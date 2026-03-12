"""预测任务执行 — 供 CLI 与 Web API 调用。"""

from datetime import datetime

from loguru import logger


def run_predict(return_data: bool = False) -> dict:
    """执行当日预测全流程。
    返回 {"ok": True, "trade_date": str, "report_path": str [, "stocks", "funds"]} 或 {"ok": False, "error": str}。
    return_data=True 时附带 stocks、funds 供 CLI 预览。
    """
    try:
        from core.stock_screener import screen_stocks
        from core.fund_screener import screen_funds
        from core.ai_analyzer import analyze_stocks, analyze_funds
        from core.data_fetcher import get_all_a_stocks_spot, get_market_sentiment
        from core.news_fetcher import fetch_market_news, fetch_policy_news
        from core.report_generator import generate_prediction_report
        from core.sector_advisor import get_affected_sectors
        from storage.db import save_recommendations, save_daily_summary_after_predict, save_daily_context

        trade_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"===== 开始每日预测: {trade_date} =====")

        spot_df = get_all_a_stocks_spot()
        market_info = get_market_sentiment(spot_df)
        stocks = screen_stocks(spot_df)
        funds = screen_funds()

        market_news_list = fetch_market_news(max_items=20)
        policy_news_list = fetch_policy_news(max_items=15)
        affected_sectors = get_affected_sectors(market_news_list, policy_news_list, max_sectors=5)
        save_daily_context(trade_date, market_news_list, policy_news_list, affected_sectors=affected_sectors)
        if market_news_list or policy_news_list:
            logger.info(f"已入库要闻: 市场 {len(market_news_list)} 条, 政策/宏观 {len(policy_news_list)} 条")
        if affected_sectors:
            logger.info(f"政策与新闻驱动板块: {[s['name'] for s in affected_sectors]}")

        logger.info("开始 AI 分析（含今日卦象、要闻、驱动板块）...")
        stocks = analyze_stocks(
            stocks, market_info,
            market_news_list=market_news_list,
            policy_news_list=policy_news_list,
            affected_sectors=affected_sectors,
        )
        funds = analyze_funds(
            funds,
            market_news_list=market_news_list,
            policy_news_list=policy_news_list,
            affected_sectors=affected_sectors,
        )

        db_items = []
        for style, items in stocks.items():
            for s in items:
                db_items.append({
                    "category": "stock",
                    "style": style,
                    "code": s["code"],
                    "name": s["name"],
                    "score": s.get("tech_score", 0),
                    "reason": s.get("reason", ""),
                    "ai_analysis": s.get("ai_analysis", ""),
                })
        for f in funds:
            db_items.append({
                "category": "fund",
                "style": f.get("style", "etf"),
                "code": f["code"],
                "name": f["name"],
                "score": f.get("tech_score", 0),
                "reason": f.get("reason", ""),
                "ai_analysis": f.get("ai_analysis", ""),
            })

        save_recommendations(trade_date, db_items)
        stock_total = sum(len(items) for items in stocks.values())
        fund_total = len(funds)
        save_daily_summary_after_predict(trade_date, stock_total, fund_total)

        logger.info("正在生成报告（含今日卦象、市场概况、要闻与驱动板块）...")
        generate_prediction_report(
            trade_date, stocks, funds, market_info,
            market_news_list=market_news_list,
            policy_news_list=policy_news_list,
            affected_sectors=affected_sectors,
        )
        logger.info("✅ 预测完成！报告已写入数据库")
        out = {"ok": True, "trade_date": trade_date, "report_path": ""}
        if return_data:
            out["stocks"] = stocks
            out["funds"] = funds
        return out
    except Exception as e:
        logger.exception("预测任务执行失败")
        return {"ok": False, "error": str(e)}
