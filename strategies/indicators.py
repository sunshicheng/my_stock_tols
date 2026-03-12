"""技术指标计算 — 纯 pandas/numpy 实现，无外部 TA 依赖。"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    histogram = 2 * (dif - dea)
    return dif, dea, histogram


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3):
    lowest = low.rolling(window=n, min_periods=n).min()
    highest = high.rolling(window=n, min_periods=n).max()
    rsv = (close - lowest) / (highest - lowest).replace(0, np.nan) * 100
    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    mid = sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def volume_ratio(volume: pd.Series, period: int = 5) -> pd.Series:
    """量比 = 当日成交量 / 过去 N 日平均成交量。"""
    avg_vol = volume.rolling(window=period, min_periods=period).mean().shift(1)
    return volume / avg_vol.replace(0, np.nan)


def price_position(close: pd.Series, period: int = 60) -> pd.Series:
    """价格在 N 日内的相对位置 (0~1)。"""
    lowest = close.rolling(window=period, min_periods=period).min()
    highest = close.rolling(window=period, min_periods=period).max()
    rng = (highest - lowest).replace(0, np.nan)
    return (close - lowest) / rng


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """对包含 OHLCV 数据的 DataFrame 计算全部技术指标。

    要求列名: 开盘/收盘/最高/最低/成交量
    """
    c, h, l, v = df["收盘"], df["最高"], df["最低"], df["成交量"]

    df["MA5"] = sma(c, 5)
    df["MA10"] = sma(c, 10)
    df["MA20"] = sma(c, 20)
    df["MA60"] = sma(c, 60)

    df["EMA12"] = ema(c, 12)
    df["EMA26"] = ema(c, 26)

    dif, dea, hist = macd(c)
    df["MACD_DIF"] = dif
    df["MACD_DEA"] = dea
    df["MACD_HIST"] = hist

    df["RSI6"] = rsi(c, 6)
    df["RSI14"] = rsi(c, 14)

    k, d, j = kdj(h, l, c)
    df["KDJ_K"] = k
    df["KDJ_D"] = d
    df["KDJ_J"] = j

    upper, mid, lower = bollinger_bands(c)
    df["BOLL_UPPER"] = upper
    df["BOLL_MID"] = mid
    df["BOLL_LOWER"] = lower

    df["VOL_RATIO"] = volume_ratio(v)
    df["PRICE_POS"] = price_position(c)

    return df


def score_technical(df: pd.DataFrame) -> dict:
    """基于最新指标值给出技术面评分 (0~100) 及信号详情。"""
    if len(df) < 20:
        return {"score": 0, "signals": ["数据不足"]}

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    signals = []
    score = 50.0

    # --- 均线多头排列 ---
    if all(pd.notna(latest[c]) for c in ["MA5", "MA10", "MA20"]):
        if latest["MA5"] > latest["MA10"] > latest["MA20"]:
            score += 12
            signals.append("均线多头排列 ↑")
        elif latest["MA5"] < latest["MA10"] < latest["MA20"]:
            score -= 10
            signals.append("均线空头排列 ↓")

    # --- MA5 向上穿越 MA10（金叉） ---
    if all(pd.notna(x) for x in [latest["MA5"], latest["MA10"], prev["MA5"], prev["MA10"]]):
        if prev["MA5"] <= prev["MA10"] and latest["MA5"] > latest["MA10"]:
            score += 8
            signals.append("MA5/MA10 金叉 ↑")

    # --- MACD ---
    if pd.notna(latest["MACD_DIF"]) and pd.notna(latest["MACD_DEA"]):
        if latest["MACD_DIF"] > latest["MACD_DEA"]:
            score += 6
            if pd.notna(prev["MACD_DIF"]) and prev["MACD_DIF"] <= prev["MACD_DEA"]:
                score += 6
                signals.append("MACD 金叉 ↑")
            else:
                signals.append("MACD 多头")
        else:
            score -= 5
            signals.append("MACD 空头")

    # --- MACD 柱状图 ---
    if pd.notna(latest["MACD_HIST"]) and pd.notna(prev.get("MACD_HIST")):
        if latest["MACD_HIST"] > 0 and latest["MACD_HIST"] > prev["MACD_HIST"]:
            score += 4
            signals.append("MACD 红柱放大")

    # --- RSI ---
    if pd.notna(latest["RSI14"]):
        if latest["RSI14"] < 30:
            score += 8
            signals.append(f"RSI14 超卖 ({latest['RSI14']:.0f})")
        elif latest["RSI14"] < 45:
            score += 3
            signals.append(f"RSI14 偏低 ({latest['RSI14']:.0f})")
        elif latest["RSI14"] > 80:
            score -= 8
            signals.append(f"RSI14 超买 ({latest['RSI14']:.0f})")

    # --- KDJ ---
    if pd.notna(latest["KDJ_J"]):
        if latest["KDJ_J"] < 20:
            score += 6
            signals.append("KDJ 超卖区")
        elif pd.notna(prev["KDJ_K"]) and prev["KDJ_K"] <= prev["KDJ_D"] and latest["KDJ_K"] > latest["KDJ_D"]:
            score += 5
            signals.append("KDJ 金叉 ↑")

    # --- 布林带 ---
    if pd.notna(latest["BOLL_LOWER"]) and pd.notna(latest["BOLL_MID"]):
        if latest["收盘"] <= latest["BOLL_LOWER"]:
            score += 5
            signals.append("触及布林下轨")
        elif latest["收盘"] >= latest["BOLL_UPPER"]:
            score -= 4
            signals.append("触及布林上轨")
        elif latest["BOLL_LOWER"] < latest["收盘"] < latest["BOLL_MID"]:
            score += 2

    # --- 放量 ---
    if pd.notna(latest["VOL_RATIO"]) and latest["VOL_RATIO"] > 1.5:
        if latest.get("涨跌幅", 0) > 0:
            score += 5
            signals.append(f"放量上涨 (量比 {latest['VOL_RATIO']:.1f})")
        else:
            score -= 3
            signals.append(f"放量下跌 (量比 {latest['VOL_RATIO']:.1f})")

    # --- 价格位置 ---
    if pd.notna(latest["PRICE_POS"]):
        if latest["PRICE_POS"] < 0.3:
            score += 4
            signals.append("处于60日低位")
        elif latest["PRICE_POS"] > 0.9:
            score -= 3
            signals.append("处于60日高位")

    score = max(0, min(100, score))

    return {"score": round(score, 1), "signals": signals}
