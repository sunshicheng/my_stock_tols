"""基金筛选器 — ETF 为主 + 股票型/混合型基金补充。"""

import pandas as pd
from loguru import logger

from config.settings import FUND_CONFIG
from core.data_fetcher import get_etf_spot, get_etf_history, get_fund_rank
from strategies.indicators import compute_all_indicators, score_technical


def _screen_etfs() -> list[dict]:
    """筛选 ETF：基于实时行情 + 近期技术走势。"""
    spot = get_etf_spot()
    if spot.empty:
        logger.warning("ETF 行情为空")
        return []

    # 基础过滤
    mask = (
        (spot["成交额"] > FUND_CONFIG["min_volume"]) &
        (spot["最新价"] > 0.1) &
        (spot["涨跌幅"].notna())
    )
    # 排除货币 ETF（价格通常在 100 左右且波动极小）
    mask &= spot["最新价"] < 90

    filtered = spot[mask].copy()
    if filtered.empty:
        return []

    # 初步打分（从实时数据）
    s = pd.Series(0.0, index=filtered.index)
    s += filtered["涨跌幅"].clip(-5, 8) * 3
    if "量比" in filtered.columns:
        s += filtered["量比"].clip(0, 5).fillna(1) * 2
    if "换手率" in filtered.columns:
        s += filtered["换手率"].clip(0, 10).fillna(0) * 1.5
    filtered["spot_score"] = s

    # 取 top 30 做详细分析
    top = filtered.nlargest(30, "spot_score")
    results = []

    for _, row in top.iterrows():
        code = row["代码"]
        name = row["名称"]
        try:
            hist = get_etf_history(code, days=40)
            if len(hist) < 15:
                continue
            hist = compute_all_indicators(hist)
            tech = score_technical(hist)

            results.append({
                "code": code,
                "name": name,
                "price": row["最新价"],
                "change_pct": row.get("涨跌幅", 0),
                "volume": row.get("成交额", 0),
                "spot_score": row.get("spot_score", 0),
                "tech_score": tech["score"],
                "signals": tech["signals"],
                "fund_type": "ETF",
                "total_score": row.get("spot_score", 0) * 0.4 + tech["score"] * 0.6,
            })
        except Exception as e:
            logger.debug(f"ETF分析失败 {code}: {e}")

    results.sort(key=lambda x: x["total_score"], reverse=True)
    selected = results[:FUND_CONFIG["etf_count"]]
    for item in selected:
        item["reason"] = f"ETF强势: {', '.join(item['signals'][:3])}"
        item["style"] = "etf"

    logger.info(f"ETF 筛选完成: {len(selected)} 只")
    return selected


def _screen_open_funds(fund_type: str, count: int) -> list[dict]:
    """筛选开放式基金（股票型/混合型），基于近期业绩排行。"""
    df = get_fund_rank(fund_type)
    if df.empty:
        logger.warning(f"{fund_type}基金排行为空")
        return []

    # 仅对数值列做转换（pandas 3.x 已移除 errors='ignore'，只支持 raise/coerce）
    numeric_cols = ["序号", "单位净值", "累计净值", "日增长率", "近1周", "近1月", "近3月", "近6月", "近1年", "今年来", "成立来"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    results = []
    sort_col = None
    for candidate in ["近1周", "近1月", "日增长率"]:
        if candidate in df.columns:
            sort_col = candidate
            break
    if sort_col is None:
        logger.warning(f"{fund_type}基金排行没有可用排序列")
        return []

    df[sort_col] = pd.to_numeric(df[sort_col], errors="coerce")
    df = df.dropna(subset=[sort_col])
    df = df.sort_values(sort_col, ascending=False).head(count * 3)

    for _, row in df.iterrows():
        code = str(row.get("基金代码", ""))
        name = str(row.get("基金简称", ""))
        if not code:
            continue

        weekly_return = row.get("近1周", 0)
        monthly_return = row.get("近1月", 0)
        daily_return = row.get("日增长率", 0)

        score = 50.0
        signals = []

        if pd.notna(weekly_return) and weekly_return > 0:
            score += min(weekly_return * 3, 20)
            signals.append(f"周涨 {weekly_return:.2f}%")

        if pd.notna(monthly_return) and monthly_return > 0:
            score += min(monthly_return, 15)
            signals.append(f"月涨 {monthly_return:.2f}%")

        if pd.notna(daily_return) and daily_return > 0:
            score += min(daily_return * 5, 15)
            signals.append(f"日涨 {daily_return:.2f}%")

        results.append({
            "code": code,
            "name": name,
            "price": row.get("单位净值", 0),
            "change_pct": daily_return if pd.notna(daily_return) else 0,
            "volume": 0,
            "spot_score": 0,
            "tech_score": score,
            "signals": signals,
            "fund_type": fund_type,
            "total_score": score,
            "style": fund_type,
            "reason": f"{fund_type}近期强势: {', '.join(signals[:3])}",
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    selected = results[:count]
    logger.info(f"{fund_type}基金筛选完成: {len(selected)} 只")
    return selected


def screen_funds() -> list[dict]:
    """基金筛选主流程。ETF 为主，股票型/混合型补充；当 ETF 行情不可用时自动多取开放式基金以达到目标只数。"""
    logger.info("=" * 40 + " 开始基金筛选 " + "=" * 40)

    etfs = _screen_etfs()
    target = FUND_CONFIG.get("target_total", 14)
    need_open = target - len(etfs)
    # ETF 不足时，用更多股票型+混合型补足
    base_stock = FUND_CONFIG["stock_fund_count"]
    base_hybrid = FUND_CONFIG["hybrid_fund_count"]
    stock_count = max(base_stock, (need_open + 1) // 2)
    hybrid_count = max(base_hybrid, need_open - stock_count)

    stock_funds = _screen_open_funds("股票型", stock_count)
    hybrid_funds = _screen_open_funds("混合型", hybrid_count)

    all_funds = etfs + stock_funds + hybrid_funds
    logger.info(f"基金推荐总计: {len(all_funds)} 只 "
                f"(ETF {len(etfs)}, 股票型 {len(stock_funds)}, 混合型 {len(hybrid_funds)})")
    return all_funds
