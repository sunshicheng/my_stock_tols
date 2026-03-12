"""股票筛选器 — 多因子打分模型，按风格（激进/稳健/适中）分类推荐。"""

import pandas as pd
from loguru import logger

from config.settings import STOCK_CONFIG, RISK_ALLOCATION
from core.data_fetcher import get_all_a_stocks_spot, get_stock_history, get_stock_fund_flow, get_stock_info
from core.news_fetcher import (
    fetch_stock_news,
    news_to_summary,
    news_score_for_stock,
)
from strategies.indicators import compute_all_indicators, score_technical


def _prefilter(df: pd.DataFrame) -> pd.DataFrame:
    """基础过滤：排除 ST、停牌、涨跌停、异常标的。每步记录剔除数量便于排查。"""
    cfg = STOCK_CONFIG
    n_start = len(df)
    mask = pd.Series(True, index=df.index)

    # ST/退市/N/C
    m = ~df["名称"].str.contains("ST|退市|N |C ", na=False, regex=True)
    drop = (~m & mask).sum()
    mask &= m
    if drop > 0:
        logger.info(f"  基础过滤 · 排除 ST/退市/N/C: -{drop} 只 (剩余 {mask.sum()})")

    # 最新价 > 0
    m = df["最新价"] > 0
    drop = (~m & mask).sum()
    mask &= m
    if drop > 0:
        logger.info(f"  基础过滤 · 排除 最新价<=0: -{drop} 只 (剩余 {mask.sum()})")

    # 成交额
    m = df["成交额"] > cfg["min_turnover"]
    drop = (~m & mask).sum()
    mask &= m
    if drop > 0:
        logger.info(f"  基础过滤 · 排除 成交额<{cfg['min_turnover']/1e4:.0f}万: -{drop} 只 (剩余 {mask.sum()})")

    # 价格区间
    m = df["最新价"].between(cfg["min_price"], cfg["max_price"])
    drop = (~m & mask).sum()
    mask &= m
    if drop > 0:
        logger.info(f"  基础过滤 · 排除 价格不在[{cfg['min_price']},{cfg['max_price']}]: -{drop} 只 (剩余 {mask.sum()})")

    # 流通市值（可能无此列）
    if "流通市值" in df.columns and df["流通市值"].notna().any():
        m = df["流通市值"].fillna(0) > cfg["min_market_cap"]
        drop = (~m & mask).sum()
        mask &= m
        if drop > 0:
            logger.info(f"  基础过滤 · 排除 流通市值<{cfg['min_market_cap']/1e8:.0f}亿: -{drop} 只 (剩余 {mask.sum()})")

    # 换手率
    if "换手率" in df.columns:
        valid_turnover = df["换手率"].notna()
        m = (~valid_turnover) | df["换手率"].between(cfg["min_turnover_rate"], cfg["max_turnover_rate"])
        drop = (~m & mask).sum()
        mask &= m
        if drop > 0:
            logger.info(f"  基础过滤 · 排除 换手率不在[{cfg['min_turnover_rate']},{cfg['max_turnover_rate']}]%: -{drop} 只 (剩余 {mask.sum()})")

    # 涨跌幅（排除涨停/跌停）
    if "涨跌幅" in df.columns:
        m = df["涨跌幅"].between(-9.8, 9.8)
        drop = (~m & mask).sum()
        mask &= m
        if drop > 0:
            logger.info(f"  基础过滤 · 排除 涨停/跌停(涨跌幅超出±9.8%): -{drop} 只 (剩余 {mask.sum()})")

    filtered = df[mask].copy()
    n_end = len(filtered)
    logger.info(f"基础过滤: {n_start} → {n_end} 只 (合计剔除 {n_start - n_end} 只)")
    return filtered


def _spot_score(df: pd.DataFrame) -> pd.DataFrame:
    """从实时行情中提取初步打分（量比、换手率、涨跌幅等）。
    当数据源缺列（如新浪备选无量比/换手率/60日/PE）时，缺项按 0 分计，避免 spot_score 全 NaN 导致乱选。
    """
    s = pd.Series(0.0, index=df.index)

    # 量比加分
    if "量比" in df.columns:
        s += df["量比"].clip(0, 5).fillna(0) * 3  # max +15

    # 适度换手率加分（缺列或全 NaN 时该项为 0）
    if "换手率" in df.columns:
        ideal_turnover = 1 - ((df["换手率"] - 5).abs() / 10).clip(0, 1)
        s += ideal_turnover.fillna(0) * 10  # max +10

    # 涨跌幅：微涨加分（1-5%），大涨不加（追高风险）
    if "涨跌幅" in df.columns:
        pct = df["涨跌幅"].fillna(0)
        s += ((pct > 0.5) & (pct < 5)).astype(float) * 8
        s += ((pct >= 5) & (pct < 8)).astype(float) * 3
        s -= (pct < -3).astype(float) * 5

    # 低估值加分
    if "市盈率-动态" in df.columns:
        pe = df["市盈率-动态"].fillna(0)
        s += ((pe > 0) & (pe < 30)).astype(float) * 5
        s += ((pe >= 30) & (pe < 60)).astype(float) * 2

    # 60日涨幅适中加分（趋势向上但不过热）
    if "60日涨跌幅" in df.columns:
        chg60 = df["60日涨跌幅"].fillna(0)
        s += ((chg60 > 0) & (chg60 < 30)).astype(float) * 5
        s -= (chg60 > 50).astype(float) * 5

    df = df.copy()
    df["spot_score"] = s.fillna(0)  # 确保无 NaN，避免 nlargest 乱序
    return df


def _analyze_candidates(candidates: pd.DataFrame) -> list[dict]:
    """对候选股逐个获取历史数据、技术评分与新闻因子。慢速拉取时每只间隔 FETCH_INTERVAL_STOCK/FETCH_INTERVAL_NEWS。"""
    import time
    from config.settings import SLOW_FETCH, FETCH_INTERVAL_STOCK, FETCH_INTERVAL_NEWS
    results = []
    for idx, (_, row) in enumerate(candidates.iterrows()):
        code = row["代码"]
        name = row["名称"]
        try:
            hist = get_stock_history(code, days=STOCK_CONFIG["history_days"])
            if SLOW_FETCH:
                time.sleep(FETCH_INTERVAL_STOCK)
            if len(hist) < 20:
                continue
            hist = compute_all_indicators(hist)
            tech = score_technical(hist)

            latest = hist.iloc[-1]
            # 量比：行情有则用，否则用历史 K 算（当日量/5日均量）
            vol_ratio = row.get("量比")
            if pd.isna(vol_ratio) or vol_ratio is None:
                vol_ratio = latest.get("VOL_RATIO")
            if pd.isna(vol_ratio) or vol_ratio is None:
                vol_ratio = 0.0
            # 换手率：行情有则用，否则用 成交量(手)*100/流通股 推算
            turnover_rate = row.get("换手率")
            if pd.isna(turnover_rate) or turnover_rate is None:
                info = get_stock_info(code)
                flow_float = info.get("流通股") or info.get("流通股本")
                if flow_float is not None:
                    try:
                        flow = float(flow_float)
                        vol = latest.get("成交量") or 0
                        if flow > 0 and vol is not None:
                            turnover_rate = (float(vol) * 100 / flow) * 100  # 手→股，再换算为%
                    except (TypeError, ValueError):
                        pass
            if pd.isna(turnover_rate) or turnover_rate is None:
                turnover_rate = 0.0

            item = {
                "code": code,
                "name": name,
                "price": row["最新价"],
                "change_pct": row.get("涨跌幅", 0),
                "volume_ratio": vol_ratio,
                "turnover_rate": turnover_rate,
                "pe": row.get("市盈率-动态", 0),
                "market_cap": row.get("流通市值", 0),
                "spot_score": row.get("spot_score", 0),
                "tech_score": tech["score"],
                "signals": tech["signals"],
                "ma5": latest.get("MA5"),
                "ma10": latest.get("MA10"),
                "ma20": latest.get("MA20"),
            }

            # 新闻因子：仅对进入候选的股票拉取新闻，避免请求过多
            try:
                news_list = fetch_stock_news(code, max_items=10)
                if SLOW_FETCH and FETCH_INTERVAL_NEWS > 0:
                    time.sleep(FETCH_INTERVAL_NEWS)
                item["news_score"] = news_score_for_stock(news_list)
                item["news_summary"] = news_to_summary(news_list, max_headlines=5)
            except Exception as e:
                logger.debug(f"新闻获取 {code}: {e}")
                item["news_score"] = 50.0
                item["news_summary"] = "暂无近期新闻"

            results.append(item)
            # 非慢速模式下每 5 只稍停，避免新闻接口限流
            if not SLOW_FETCH and (idx + 1) % 5 == 0:
                time.sleep(1.0)
        except Exception as e:
            logger.debug(f"分析 {code} {name} 失败: {e}")

    logger.info(f"技术+新闻分析完成: {len(results)} 只通过")
    return results


def _classify_and_rank(stocks: list[dict]) -> dict[str, list[dict]]:
    """按激进/稳健/适中分类并排序。技术+行情+新闻三因子。"""
    for s in stocks:
        news_s = s.get("news_score", 50.0)
        # 综合分：技术 50%、行情 35%、新闻 15%
        s["total_score"] = s["tech_score"] * 0.50 + s["spot_score"] * 0.35 + news_s * 0.15

    # 激进型：动量 + 新闻热度
    aggressive_score = lambda s: (
        s["tech_score"] * 0.25 +
        min(s.get("change_pct", 0), 8) * 5 +
        min(s.get("volume_ratio", 0), 5) * 4 +
        s["spot_score"] * 0.25 +
        s.get("news_score", 50) * 0.15
    )

    # 稳健型：趋势 + 估值 + 新闻偏利好
    stable_score = lambda s: (
        s["tech_score"] * 0.45 +
        (10 if 0 < s.get("pe", 999) < 30 else 0) +
        (5 if s.get("market_cap", 0) > 100e8 else 0) +
        s["spot_score"] * 0.2 +
        s.get("news_score", 50) * 0.15
    )

    sorted_agg = sorted(stocks, key=aggressive_score, reverse=True)
    sorted_stable = sorted(stocks, key=stable_score, reverse=True)

    n_agg = RISK_ALLOCATION["aggressive"]
    n_stable = RISK_ALLOCATION["stable"]
    n_mod = RISK_ALLOCATION["moderate"]

    selected_codes = set()
    result = {"aggressive": [], "stable": [], "moderate": []}

    for s in sorted_agg:
        if len(result["aggressive"]) >= n_agg:
            break
        if s["code"] not in selected_codes:
            s["style"] = "aggressive"
            reason = f"动量强势: {', '.join(s['signals'][:3])}"
            if s.get("news_summary") and s["news_summary"] != "暂无近期新闻":
                reason += f" | 新闻: {s['news_summary'][:80]}..."
            s["reason"] = reason
            result["aggressive"].append(s)
            selected_codes.add(s["code"])

    for s in sorted_stable:
        if len(result["stable"]) >= n_stable:
            break
        if s["code"] not in selected_codes:
            s["style"] = "stable"
            reason = f"趋势稳健: {', '.join(s['signals'][:3])}"
            if s.get("news_summary") and s["news_summary"] != "暂无近期新闻":
                reason += f" | 新闻: {s['news_summary'][:80]}..."
            s["reason"] = reason
            result["stable"].append(s)
            selected_codes.add(s["code"])

    # 适中型：从总分排序中选取未被选中的
    sorted_total = sorted(stocks, key=lambda s: s["total_score"], reverse=True)
    for s in sorted_total:
        if len(result["moderate"]) >= n_mod:
            break
        if s["code"] not in selected_codes:
            s["style"] = "moderate"
            reason = f"综合均衡: {', '.join(s['signals'][:3])}"
            if s.get("news_summary") and s["news_summary"] != "暂无近期新闻":
                reason += f" | 新闻: {s['news_summary'][:80]}..."
            s["reason"] = reason
            result["moderate"].append(s)
            selected_codes.add(s["code"])

    return result


def screen_stocks(spot_df: pd.DataFrame | None = None) -> dict[str, list[dict]]:
    """股票筛选主流程。若传入已拉取的行情 spot_df 则直接使用，避免重复请求导致限流。"""
    logger.info("=" * 40 + " 开始股票筛选 " + "=" * 40)

    if spot_df is not None and not spot_df.empty:
        spot = spot_df.copy()
    else:
        spot = get_all_a_stocks_spot()
    if spot.empty:
        logger.error("无法获取 A 股行情数据")
        return {"aggressive": [], "stable": [], "moderate": []}

    filtered = _prefilter(spot)
    if filtered.empty:
        return {"aggressive": [], "stable": [], "moderate": []}

    scored = _spot_score(filtered)
    candidates = scored.nlargest(STOCK_CONFIG["candidate_count"], "spot_score")
    n_cand = len(candidates)
    if n_cand > 0:
        score_min = candidates["spot_score"].min()
        score_max = candidates["spot_score"].max()
        logger.info(
            f"初筛候选: 取行情得分前 {n_cand} 只进入技术分析 "
            f"(得分范围 {score_min:.1f} ~ {score_max:.1f}；数据源缺量比/换手率等时主要按涨跌幅排序)"
        )
    else:
        logger.info(f"初筛候选: 0 只进入技术分析")

    analyzed = _analyze_candidates(candidates)
    if not analyzed:
        return {"aggressive": [], "stable": [], "moderate": []}

    result = _classify_and_rank(analyzed)

    for style, items in result.items():
        logger.info(f"[{style}] 推荐 {len(items)} 只: "
                     + ", ".join(f"{s['name']}({s['code']})" for s in items))

    return result
