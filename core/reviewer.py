"""复盘模块 — 拉取当日实际行情，与早盘推荐对比，生成复盘数据。"""

from datetime import datetime

import pandas as pd
from loguru import logger

from core.data_fetcher import get_all_a_stocks_spot, get_etf_spot
from core.ai_analyzer import analyze_review
from storage.db import get_recommendations, save_reviews, save_daily_summary


def _get_actual_prices() -> dict[str, dict]:
    """获取当日收盘数据，返回 {代码: {price, change_pct}} 映射。"""
    result = {}

    stock_spot = get_all_a_stocks_spot()
    if not stock_spot.empty:
        for _, row in stock_spot.iterrows():
            result[row["代码"]] = {
                "close_price": row["最新价"],
                "change_pct": row.get("涨跌幅", 0),
            }

    etf_spot = get_etf_spot()
    if not etf_spot.empty:
        for _, row in etf_spot.iterrows():
            result[row["代码"]] = {
                "close_price": row["最新价"],
                "change_pct": row.get("涨跌幅", 0),
            }

    return result


def run_review(trade_date: str = None) -> dict:
    """执行当日复盘。

    Returns:
        包含 recommendations, results, summary, ai_review 的字典
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"开始复盘: {trade_date}")

    recommendations = get_recommendations(trade_date)
    if not recommendations:
        logger.warning(f"没有找到 {trade_date} 的推荐记录，无法复盘")
        return {"error": f"没有找到 {trade_date} 的推荐记录"}

    actual_prices = _get_actual_prices()

    results = []
    stock_hit = 0
    stock_total = 0
    fund_hit = 0
    fund_total = 0
    returns = []

    for rec in recommendations:
        code = rec["code"]
        actual = actual_prices.get(code, {})
        close_price = actual.get("close_price", 0)
        change_pct = actual.get("change_pct", 0)
        hit = 1 if change_pct > 0 else 0

        if rec["category"] == "stock":
            stock_total += 1
            stock_hit += hit
        else:
            fund_total += 1
            fund_hit += hit

        returns.append(change_pct if pd.notna(change_pct) else 0)

        results.append({
            "category": rec["category"],
            "code": code,
            "name": rec["name"],
            "recommend_price": rec.get("score", 0),
            "close_price": close_price,
            "change_pct": round(change_pct, 2) if pd.notna(change_pct) else 0,
            "hit": hit,
            "ai_review": "",
            "reason": rec.get("reason", ""),
        })

    avg_return = sum(returns) / len(returns) if returns else 0

    # AI 复盘
    ai_review = analyze_review(recommendations, results)

    save_reviews(trade_date, results)

    summary = {
        "stock_hit": stock_hit,
        "stock_total": stock_total,
        "fund_hit": fund_hit,
        "fund_total": fund_total,
        "avg_return": round(avg_return, 2),
        "summary": ai_review,
    }
    save_daily_summary(trade_date, summary)

    logger.info(
        f"复盘完成: 股票 {stock_hit}/{stock_total}, "
        f"基金 {fund_hit}/{fund_total}, 平均收益 {avg_return:.2f}%"
    )

    return {
        "trade_date": trade_date,
        "recommendations": recommendations,
        "results": results,
        "summary": summary,
        "ai_review": ai_review,
    }
