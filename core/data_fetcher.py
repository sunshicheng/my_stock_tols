"""AKShare 数据获取层 — 封装常用接口，统一异常处理和重试。

东方财富部分接口有反爬限制，本模块通过多种策略应对：
1. 渐进式重试（指数退避）
2. 全量行情接口失败时自动降级到分页/成分股方式
3. 对单接口的调用间隔限流；支持慢速拉取（SLOW_FETCH）拉长间隔

参考：AKShare 文档 https://akshare.akfamily.xyz/tutorial.html；
行情/东财问题见 GitHub issues #7107（新浪不全）、#7119（东财手动 cookie）。
"""

import time
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd
from loguru import logger

from config.settings import SLOW_FETCH, FETCH_INTERVAL_API

_last_call_time = 0.0


def _throttle():
    global _last_call_time
    interval = FETCH_INTERVAL_API if SLOW_FETCH else 0.3
    elapsed = time.time() - _last_call_time
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_call_time = time.time()


def _retry(func, *args, retries: int = 3, delay: float = 2.0, **kwargs):
    for i in range(retries):
        _throttle()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            wait = delay * (i + 1)
            logger.warning(f"[retry {i+1}/{retries}] {func.__name__} failed: {type(e).__name__}, wait {wait:.0f}s")
            if i < retries - 1:
                time.sleep(wait)
    logger.error(f"{func.__name__} 最终失败，返回空 DataFrame")
    return pd.DataFrame()


# ========== 股票数据 ==========

def get_all_a_stocks_spot() -> pd.DataFrame:
    """获取全部沪深京 A 股实时行情快照。

    优先东方财富；失败时尝试新浪 stock_zh_a_spot（AKShare 文档）。
    说明：新浪接口有时返回不全、少部分标的（见 akfamily/akshare#7107）；
    东财可选手动 cookie（见 #7119）但易被封，建议仍以多源降级为主。
    """
    df = _retry(ak.stock_zh_a_spot_em, retries=3, delay=3.0)

    if df.empty:
        logger.info("全量行情不可用，尝试分板块获取...")
        parts = []
        for fn_name in ["stock_sh_a_spot_em", "stock_sz_a_spot_em", "stock_bj_a_spot_em"]:
            fn = getattr(ak, fn_name, None)
            if fn:
                part = _retry(fn, retries=2, delay=3.0)
                if not part.empty:
                    parts.append(part)
                if SLOW_FETCH:
                    time.sleep(FETCH_INTERVAL_API * 2)
                else:
                    time.sleep(2)
        if parts:
            df = pd.concat(parts, ignore_index=True)
            logger.info(f"分板块获取成功: {len(df)} 只")

    if df.empty:
        logger.info("东方财富不可用，尝试新浪 stock_zh_a_spot...")
        if SLOW_FETCH:
            time.sleep(FETCH_INTERVAL_API * 2)
        df = _retry(ak.stock_zh_a_spot, retries=2, delay=5.0)
        if not df.empty:
            # 新浪代码带前缀 bj/sz/sh，统一为 6 位代码供后续使用
            if "代码" in df.columns:
                df["代码"] = df["代码"].astype(str).str.replace(r"^(bj|sz|sh)", "", regex=True)
            # 补齐东方财富字段名/缺失列，便于下游统一处理
            if "流通市值" not in df.columns:
                df["流通市值"] = float("nan")
            if "量比" not in df.columns:
                df["量比"] = float("nan")
            if "换手率" not in df.columns:
                df["换手率"] = float("nan")
            if "60日涨跌幅" not in df.columns:
                df["60日涨跌幅"] = float("nan")
            if "市盈率-动态" not in df.columns:
                df["市盈率-动态"] = float("nan")
            logger.info(f"新浪行情获取成功: {len(df)} 只")

    if df.empty:
        return df

    for col in ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅",
                 "最高", "最低", "今开", "昨收", "量比", "换手率",
                 "市盈率-动态", "市净率", "总市值", "流通市值",
                 "60日涨跌幅", "年初至今涨跌幅"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_stock_list_by_rank() -> pd.DataFrame:
    """备选方案：通过涨幅排行获取活跃个股列表。"""
    try:
        df = _retry(ak.stock_zh_a_spot_em, retries=2, delay=3.0)
        if not df.empty:
            return df
    except Exception:
        pass

    logger.info("尝试通过成分股方式获取候选列表...")
    candidates = []
    try:
        # 沪深300成分
        hs300 = _retry(ak.index_stock_cons, symbol="000300", retries=2)
        if not hs300.empty:
            if "品种代码" in hs300.columns:
                candidates.extend(hs300["品种代码"].tolist())
            elif "代码" in hs300.columns:
                candidates.extend(hs300["代码"].tolist())
    except Exception:
        pass

    return pd.DataFrame({"代码": candidates}) if candidates else pd.DataFrame()


def _symbol_to_tx_prefix(symbol: str) -> str:
    """6 位代码转腾讯接口前缀：6->sh，0/3->sz，北交所暂不请求腾讯。"""
    s = str(symbol).strip()
    if len(s) != 6 or not s.isdigit():
        return ""
    if s[0] == "6":
        return "sh" + s
    if s[0] in ("0", "3"):
        return "sz" + s
    return ""


def get_stock_history(symbol: str, days: int = 60, adjust: str = "qfq") -> pd.DataFrame:
    """获取个股日 K 历史（前复权）。优先东财 stock_zh_a_hist，失败时用腾讯 stock_zh_a_hist_tx（见 AKShare 文档）。"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")
    df = _retry(
        ak.stock_zh_a_hist,
        symbol=symbol, period="daily",
        start_date=start, end_date=end, adjust=adjust,
    )
    if df.empty:
        tx_symbol = _symbol_to_tx_prefix(symbol)
        if tx_symbol:
            _throttle()
            try:
                df = ak.stock_zh_a_hist_tx(symbol=tx_symbol, start_date=start, end_date=end, adjust=adjust)
            except Exception as e:
                logger.debug(f"腾讯日K备选失败 {symbol}: {e}")
            if not df.empty:
                # 腾讯列名: date, open, close, high, low, amount -> 统一为东财列名
                df = df.rename(columns={
                    "date": "日期", "open": "开盘", "close": "收盘",
                    "high": "最高", "low": "最低", "amount": "成交量",
                })
                df["日期"] = pd.to_datetime(df["日期"])
                df["成交额"] = float("nan")
                df["振幅"] = float("nan")
                df["涨跌额"] = float("nan")
                df["换手率"] = float("nan")
                df["涨跌幅"] = df["收盘"].pct_change() * 100
                logger.debug(f"日K使用腾讯备选: {symbol}")
    if df.empty:
        return df
    df["日期"] = pd.to_datetime(df["日期"])
    for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("日期").tail(days).reset_index(drop=True)


def get_stock_fund_flow(symbol: str, market: str = "") -> pd.DataFrame:
    """获取个股资金流向（近日）。"""
    try:
        df = _retry(ak.stock_individual_fund_flow, stock=symbol, market=market)
        return df
    except Exception as e:
        logger.debug(f"资金流向获取失败 {symbol}: {e}")
        return pd.DataFrame()


def get_stock_info(symbol: str) -> dict:
    """获取个股基本信息。"""
    try:
        df = _retry(ak.stock_individual_info_em, symbol=symbol)
        if df.empty:
            return {}
        return dict(zip(df["item"], df["value"]))
    except Exception:
        return {}


# ========== 基金数据 ==========

def get_etf_spot() -> pd.DataFrame:
    """获取全部 ETF 实时行情。东方财富失败时返回空，由调用方依赖开放式基金排行。"""
    df = _retry(ak.fund_etf_spot_em, retries=3, delay=3.0)
    if df.empty:
        return df
    for col in ["最新价", "涨跌额", "涨跌幅", "成交量", "成交额", "开盘价",
                 "最高价", "最低价", "昨收", "换手率", "量比", "流通市值", "总市值"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_etf_history(symbol: str, days: int = 60) -> pd.DataFrame:
    """获取 ETF 日 K 历史。"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")
    df = _retry(
        ak.fund_etf_hist_em,
        symbol=symbol, period="daily",
        start_date=start, end_date=end, adjust="qfq",
    )
    if df.empty:
        return df
    df["日期"] = pd.to_datetime(df["日期"])
    for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("日期").tail(days).reset_index(drop=True)


def get_fund_rank(fund_type: str = "全部", sort_key: str = "近1周") -> pd.DataFrame:
    """获取开放式基金排行。fund_type: 股票型 / 混合型 / 全部 等。"""
    try:
        df = _retry(ak.fund_open_fund_rank_em, symbol=fund_type)
        return df
    except Exception as e:
        logger.warning(f"基金排行获取失败 ({fund_type}): {e}")
        return pd.DataFrame()


def get_fund_net_value(symbol: str) -> pd.DataFrame:
    """获取基金历史净值。"""
    try:
        df = _retry(ak.fund_open_fund_info_em, symbol=symbol, indicator="单位净值走势")
        return df
    except Exception as e:
        logger.debug(f"基金净值获取失败 {symbol}: {e}")
        return pd.DataFrame()


# ========== 市场概况 ==========

def get_market_sentiment(spot_df: pd.DataFrame | None = None) -> dict:
    """获取市场整体情绪指标。若传入已拉取的行情 spot_df 则直接使用，避免重复请求。"""
    try:
        if spot_df is not None and not spot_df.empty:
            df = spot_df
        else:
            df = get_all_a_stocks_spot()
        if df.empty:
            return {}
        total = len(df)
        up = len(df[df["涨跌幅"] > 0])
        down = len(df[df["涨跌幅"] < 0])
        flat = total - up - down
        limit_up = len(df[df["涨跌幅"] >= 9.9])
        limit_down = len(df[df["涨跌幅"] <= -9.9])
        avg_change = df["涨跌幅"].mean()
        return {
            "total": total, "up": up, "down": down, "flat": flat,
            "limit_up": limit_up, "limit_down": limit_down,
            "avg_change": round(avg_change, 2),
            "up_ratio": round(up / total * 100, 1),
        }
    except Exception as e:
        logger.warning(f"市场情绪获取失败: {e}")
        return {}
