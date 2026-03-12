"""基于历史推荐的 AKQuant 回测 — 用复盘期的推荐记录驱动「推荐日收盘买、次日收盘卖」的回测。

依赖：pip install akquant
参考：https://github.com/akfamily/akquant
"""

import time
from collections import defaultdict

import pandas as pd
from loguru import logger

from storage.db import get_recommendations_by_date_range
from core.data_fetcher import _symbol_to_tx_prefix


def _code_to_ak_symbol(code: str) -> str:
    """6 位代码转 akquant 所需 symbol：sh600xxx / sz000xxx / sz300xxx。"""
    s = str(code).strip()
    if len(s) != 6 or not s.isdigit():
        return ""
    if s[0] == "6":
        return "sh" + s
    if s[0] in ("0", "3"):
        return "sz" + s
    return ""


def _get_stock_bars_for_range(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取指定日期区间的日 K（用于回测）。"""
    try:
        import akshare as ak
        start = start_date.replace("-", "")[:8]
        end = end_date.replace("-", "")[:8]
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if df.empty or len(df) < 2:
            return pd.DataFrame()
        df["日期"] = pd.to_datetime(df["日期"])
        return df.sort_values("日期").reset_index(drop=True)
    except Exception as e:
        logger.debug(f"回测取 K 线 {code} {start_date}~{end_date}: {e}")
        return pd.DataFrame()


def _recommendation_dates_by_symbol(recs: list[dict], category: str = "stock") -> dict[str, set[str]]:
    """从推荐列表按标的汇总「被推荐日」集合。"""
    by_symbol = defaultdict(set)
    for r in recs:
        if r.get("category") != category:
            continue
        code = (r.get("code") or "").strip()
        if not code:
            continue
        td = r.get("trade_date", "")
        if td:
            by_symbol[code].add(td)
    return dict(by_symbol)


def run_recommendation_backtest(
    start_date: str,
    end_date: str,
    initial_cash: float = 100000.0,
    category: str = "stock",
    max_symbols: int = 20,
) -> dict:
    """基于 DB 中的推荐记录，用 AKQuant 做「推荐日收盘买、次日收盘卖」的回测。

    仅支持 A 股（category=stock）。每个标的单独回测再汇总。
    返回汇总统计与 per-symbol 结果列表。
    """
    try:
        import akquant as aq
        from akquant import Strategy
    except ImportError:
        return {
            "error": "请先安装 akquant: pip install akquant",
            "total_pnl": 0,
            "total_return_pct": 0,
            "trade_count": 0,
            "symbol_results": [],
        }

    recs = get_recommendations_by_date_range(start_date, end_date, category=category)
    by_symbol = _recommendation_dates_by_symbol(recs, category=category)
    if not by_symbol:
        return {
            "error": f"日期范围 {start_date}~{end_date} 内无{category}推荐记录",
            "total_pnl": 0,
            "total_return_pct": 0,
            "trade_count": 0,
            "symbol_results": [],
        }

    symbols = list(by_symbol.keys())[:max_symbols]
    cash_per_symbol = initial_cash / len(symbols) if symbols else 0
    results = []
    total_pnl = 0.0
    total_trades = 0

    for code in symbols:
        recommendation_dates = by_symbol[code]
        if not recommendation_dates:
            continue
        aq_symbol = _code_to_ak_symbol(code)
        if not aq_symbol:
            continue
        df = _get_stock_bars_for_range(code, start_date, end_date)
        if df.empty or len(df) < 2:
            continue
        for col in ["日期", "开盘", "收盘", "最高", "最低", "成交量"]:
            if col not in df.columns:
                return {"error": f"K 线缺少列 {col}", "symbol_results": results}
        df = df.sort_values("日期").reset_index(drop=True)
        date_strs = set(pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d").tolist())
        rec_dates = recommendation_dates & date_strs
        if not rec_dates:
            continue

        bar_dates_list = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d").tolist()

        class RecStrategy(Strategy):
            def __init__(self, rec_dates_set, dates_list):
                self.rec_dates = rec_dates_set
                self.dates_list = dates_list
                self.buy_index = -1
                self._bar_index = -1

            def on_bar(self, bar):
                self._bar_index += 1
                idx = self._bar_index
                if idx >= len(self.dates_list):
                    return
                d = self.dates_list[idx]
                pos = self.get_position(bar.symbol)
                if pos == 0 and d in self.rec_dates:
                    self.buy(symbol=bar.symbol, quantity=100)
                    self.buy_index = idx
                elif pos > 0 and self.buy_index >= 0 and idx == self.buy_index + 1:
                    self.close_position(symbol=bar.symbol)
                    self.buy_index = -1

        strategy = RecStrategy(rec_dates, bar_dates_list)
        try:
            res = aq.run_backtest(
                data=df,
                strategy=strategy,
                initial_cash=cash_per_symbol,
                symbol=aq_symbol,
            )
            total_pnl += getattr(res, "total_pnl", 0) or 0
            total_trades += getattr(res, "trade_count", 0) or 0
            results.append({
                "code": code,
                "symbol": aq_symbol,
                "trade_count": getattr(res, "trade_count", 0),
                "total_pnl": getattr(res, "total_pnl", 0),
                "total_return_pct": getattr(res, "total_return_pct", 0),
            })
        except Exception as e:
            logger.warning(f"回测 {code} 失败: {e}")
        time.sleep(0.3)

    total_return_pct = (total_pnl / initial_cash * 100) if initial_cash else 0
    return {
        "start_date": start_date,
        "end_date": end_date,
        "initial_cash": initial_cash,
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "trade_count": total_trades,
        "symbol_results": results,
        "error": None,
    }
