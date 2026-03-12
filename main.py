"""主入口 — CLI 命令行工具。

用法:
    python main.py predict           # 执行每日预测推荐
    python main.py review            # 执行当日复盘
    python main.py review 2026-03-11 # 指定日期复盘
    python main.py schedule          # 启动定时调度
    python main.py history           # 查看近30天命中率
    python main.py position add/list/plan  # 个人持仓与卖出计划
    python main.py backtest [--start] [--end]  # 基于历史推荐做 AKQuant 回测
"""

import argparse
import sys
from datetime import datetime

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}")
logger.add("logs/{time:YYYY-MM-DD}.log", level="DEBUG", rotation="1 day", retention="30 days")


def cmd_predict():
    """执行每日预测推荐。"""
    from core.stock_screener import screen_stocks
    from core.fund_screener import screen_funds
    from core.ai_analyzer import analyze_stocks, analyze_funds
    from core.data_fetcher import get_all_a_stocks_spot, get_market_sentiment
    from core.news_fetcher import fetch_market_news, fetch_policy_news
    from core.report_generator import generate_prediction_report
    from storage.db import save_recommendations, save_daily_summary_after_predict, save_daily_context

    trade_date = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"===== 开始每日预测: {trade_date} =====")

    # 1. 只拉取一次 A 股行情，复用于市场概况 + 股票筛选，避免二次请求导致限流/失败
    spot_df = get_all_a_stocks_spot()
    market_info = get_market_sentiment(spot_df)
    stocks = screen_stocks(spot_df)

    # 2. 基金筛选
    funds = screen_funds()

    # 2.5 拉取市场要闻与政策要闻，入库供后续分析，并供 AI 结合推荐
    market_news_list = fetch_market_news(max_items=20)
    policy_news_list = fetch_policy_news(max_items=15)
    # 结合十四五/十五五与实时要闻，生成政策与新闻驱动板块
    from core.sector_advisor import get_affected_sectors
    affected_sectors = get_affected_sectors(market_news_list, policy_news_list, max_sectors=5)
    save_daily_context(trade_date, market_news_list, policy_news_list, affected_sectors=affected_sectors)
    if market_news_list or policy_news_list:
        logger.info(f"已入库要闻: 市场 {len(market_news_list)} 条, 政策/宏观 {len(policy_news_list)} 条")
    if affected_sectors:
        logger.info(f"政策与新闻驱动板块: {[s['name'] for s in affected_sectors]}")

    # 3. AI 分析（注入要闻、政策与关注板块）
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

    # 4. 存储到数据库
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

    # 5. 生成报告
    logger.info("正在生成报告（含今日卦象、市场概况、要闻与驱动板块）...")
    report_path = generate_prediction_report(
        trade_date, stocks, funds, market_info,
        market_news_list=market_news_list,
        policy_news_list=policy_news_list,
        affected_sectors=affected_sectors,
    )
    logger.info(f"✅ 预测完成！报告路径: {report_path}")

    # 6. 控制台预览
    _print_preview(stocks, funds)


def cmd_review(trade_date: str = None):
    """执行复盘。"""
    from core.reviewer import run_review
    from core.report_generator import generate_review_report

    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"===== 开始复盘: {trade_date} =====")

    review_data = run_review(trade_date)
    if "error" in review_data:
        logger.error(review_data["error"])
        return

    report_path = generate_review_report(review_data)
    logger.info(f"✅ 复盘完成！报告路径: {report_path}")

    # 控制台预览
    summary = review_data.get("summary", {})
    print(f"\n{'='*50}")
    print(f"  复盘结果 — {trade_date}")
    print(f"{'='*50}")
    print(f"  股票命中: {summary.get('stock_hit', 0)}/{summary.get('stock_total', 0)}")
    print(f"  基金命中: {summary.get('fund_hit', 0)}/{summary.get('fund_total', 0)}")
    print(f"  平均收益: {summary.get('avg_return', 0):+.2f}%")
    print(f"{'='*50}\n")


def cmd_history():
    """查看历史命中率。"""
    from storage.db import get_recent_accuracy

    records = get_recent_accuracy(30)
    if not records:
        print("暂无历史数据")
        return

    print(f"\n{'='*70}")
    print(f"  近 {len(records)} 天推荐命中率")
    print(f"{'='*70}")
    print(f"  {'日期':<12} {'股票命中':<10} {'基金命中':<10} {'平均收益':<10}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    total_stock_hit, total_stock_n = 0, 0
    total_fund_hit, total_fund_n = 0, 0
    total_returns = []

    for r in records:
        sh, st = r["stock_hit"] or 0, r["stock_total"] or 0
        fh, ft = r["fund_hit"] or 0, r["fund_total"] or 0
        avg_ret = r["avg_return"] or 0

        sr = f"{sh}/{st}" if st else "-"
        fr = f"{fh}/{ft}" if ft else "-"
        print(f"  {r['trade_date']:<12} {sr:<10} {fr:<10} {avg_ret:+.2f}%")

        total_stock_hit += sh
        total_stock_n += st
        total_fund_hit += fh
        total_fund_n += ft
        total_returns.append(avg_ret)

    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
    stock_rate = f"{total_stock_hit/total_stock_n*100:.0f}%" if total_stock_n else "-"
    fund_rate = f"{total_fund_hit/total_fund_n*100:.0f}%" if total_fund_n else "-"
    avg_all = sum(total_returns) / len(total_returns) if total_returns else 0
    print(f"  {'合计':<12} {stock_rate:<10} {fund_rate:<10} {avg_all:+.2f}%")
    print(f"{'='*70}\n")


def cmd_schedule():
    """启动定时调度。"""
    from scheduler import start_scheduler
    start_scheduler()


def cmd_context(trade_date: str = None):
    """查看某日的要闻与政策（从 daily_context 表读取，供后续分析）。"""
    from storage.db import get_daily_context

    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    ctx = get_daily_context(trade_date)
    market = ctx.get("market_news", []) or []
    policy = ctx.get("policy_news", []) or []
    sectors = ctx.get("affected_sectors", []) or []
    summary_entry = next((s for s in sectors if (s.get("name") or "") == "_summary"), None)
    sector_list = [s for s in sectors if (s.get("name") or "").strip() and (s.get("name") or "") != "_summary"]

    print(f"\n{'='*60}")
    print(f"  要闻与政策 — {trade_date}")
    print(f"{'='*60}")
    if summary_entry and (summary_entry.get("reason") or "").strip():
        print(f"\n【今日政策与新闻要点】")
        print(f"  {(summary_entry.get('reason') or '').strip()}")
    print(f"\n【市场要闻】共 {len(market)} 条")
    for x in market[:15]:
        print(f"  - {(x.get('title') or '').strip()}")
    print(f"\n【政策/宏观要闻】共 {len(policy)} 条")
    for x in policy[:12]:
        print(f"  - {(x.get('title') or '').strip()}")
    if sector_list:
        print(f"\n【政策与新闻驱动板块】共 {len(sector_list)} 个")
        for s in sector_list:
            name = (s.get("name") or "").strip()
            reason = (s.get("reason") or "").strip()
            basis = (s.get("policy_basis") or "").strip()
            trigger = (s.get("news_trigger") or "").strip()
            if basis or trigger:
                print(f"  - {name}")
                if basis:
                    print(f"    政策依据：{basis[:120]}")
                if trigger:
                    print(f"    新闻触发：{trigger[:100]}")
                if reason:
                    print(f"    逻辑：{reason[:120]}")
            else:
                print(f"  - {name}：{reason[:120]}")
    print(f"{'='*60}\n")


def cmd_position(args):
    """个人持仓：添加、列表、设置卖出计划。"""
    from core.position_manager import (
        get_positions_with_plan,
        add_holding,
        set_sell_plan,
        remove_holding,
        format_positions_table,
    )
    from core.data_fetcher import get_all_a_stocks_spot, get_etf_spot

    sub = getattr(args, "sub", None)
    if sub == "add":
        code = getattr(args, "code", "").strip()
        buy_date = getattr(args, "buy_date", "")
        buy_price = float(getattr(args, "buy_price", 0))
        quantity = float(getattr(args, "quantity", 0))
        name = getattr(args, "name", "") or ""
        category = (getattr(args, "category", "stock") or "stock").lower()
        if category not in ("stock", "fund"):
            category = "stock"
        target = getattr(args, "target_price", None)
        stop = getattr(args, "stop_loss", None)
        plan_date = getattr(args, "plan_sell_date", None)
        note = getattr(args, "note", None)
        if not code or not buy_date or buy_price <= 0 or quantity <= 0:
            print("用法: position add <code> <buy_date> <buy_price> <quantity> [--name] [--category stock|fund] [--target-price] [--stop-loss] [--plan-sell-date] [--note]")
            return
        add_holding(code=code, buy_date=buy_date, buy_price=buy_price, quantity=quantity, name=name, category=category, target_price=target, stop_loss=stop, plan_sell_date=plan_date, note=note)
        print("✅ 已添加持仓")
        return

    if sub == "plan":
        pid = getattr(args, "id", None)
        target = getattr(args, "target_price", None)
        stop = getattr(args, "stop_loss", None)
        plan_date = getattr(args, "plan_sell_date", None)
        note = getattr(args, "note", None)
        if not pid:
            print("用法: position plan --id <position_id> [--target-price] [--stop-loss] [--plan-sell-date] [--note]")
            return
        ok = set_sell_plan(int(pid), target_price=target, stop_loss=stop, plan_sell_date=plan_date, note=note)
        print("✅ 已更新卖出计划" if ok else "未找到该持仓")
        return

    if sub == "rm" or sub == "delete":
        pid = getattr(args, "id", None)
        if not pid:
            print("用法: position rm --id <position_id>")
            return
        ok = remove_holding(int(pid))
        print("✅ 已删除" if ok else "未找到该持仓")
        return

    # list
    positions = get_positions_with_plan()
    price_map = {}
    try:
        spot = get_all_a_stocks_spot()
        if not spot.empty and "代码" in spot.columns and "最新价" in spot.columns:
            for _, row in spot.iterrows():
                price_map[str(row["代码"])] = float(row["最新价"])
        etf = get_etf_spot()
        if not etf.empty and "代码" in etf.columns and "最新价" in etf.columns:
            for _, row in etf.iterrows():
                price_map[str(row["代码"])] = float(row["最新价"])
    except Exception:
        pass
    lines = format_positions_table(positions, today_price_map=price_map)
    print(f"\n{'='*70}")
    print("  📋 我的持仓与卖出计划")
    print(f"{'='*70}")
    for line in lines:
        print(line)
    print(f"{'='*70}\n")


def cmd_backtest(start_date: str = None, end_date: str = None, cash: float = 100000.0, max_symbols: int = 20):
    """基于历史推荐记录，用 AKQuant 做「推荐日收盘买、次日收盘卖」回测。"""
    from core.backtest_runner import run_recommendation_backtest
    from datetime import timedelta

    if not start_date or not end_date:
        end = datetime.now()
        start = end - timedelta(days=30)
        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")
    logger.info(f"回测区间: {start_date} ~ {end_date}，初始资金 {cash}，最多 {max_symbols} 只标的")
    result = run_recommendation_backtest(
        start_date=start_date,
        end_date=end_date,
        initial_cash=cash,
        category="stock",
        max_symbols=max_symbols,
    )
    if result.get("error"):
        print(f"\n⚠️ {result['error']}\n")
        return
    print(f"\n{'='*60}")
    print("  📊 AKQuant 回测结果（推荐日收盘买 / 次日收盘卖）")
    print(f"{'='*60}")
    print(f"  区间: {result['start_date']} ~ {result['end_date']}")
    print(f"  初始资金: {result['initial_cash']:.0f}")
    print(f"  总交易次数: {result['trade_count']}")
    print(f"  总盈亏: {result['total_pnl']:+.2f}")
    print(f"  总收益率: {result['total_return_pct']:+.2f}%")
    if result.get("symbol_results"):
        print(f"\n  各标的:")
        for r in result["symbol_results"][:15]:
            print(f"    {r['code']}  交易{r.get('trade_count', 0)}次  盈亏{r.get('total_pnl', 0):+.2f}  收益{r.get('total_return_pct', 0):+.2f}%")
    print(f"{'='*60}\n")


def _print_preview(stocks: dict, funds: list):
    """在终端打印推荐预览。"""
    style_map = {"aggressive": "🔥激进", "stable": "🛡️稳健", "moderate": "⚖️适中"}
    print(f"\n{'='*60}")
    print(f"  📈 股票推荐预览")
    print(f"{'='*60}")
    for style in ["aggressive", "stable", "moderate"]:
        items = stocks.get(style, [])
        label = style_map.get(style, style)
        print(f"\n  [{label}]")
        for s in items:
            print(f"    {s['code']} {s['name']:<8} ¥{s['price']:.2f}  "
                  f"{s.get('change_pct', 0):+.2f}%  评分:{s['tech_score']:.0f}")

    print(f"\n{'='*60}")
    print(f"  💰 基金推荐预览")
    print(f"{'='*60}")
    for f in funds:
        print(f"    {f['code']} {f['name']:<16} "
              f"{f.get('change_pct', 0):+.2f}%  评分:{f.get('tech_score', 0):.0f}  [{f.get('fund_type', '')}]")
    print()


def main():
    parser = argparse.ArgumentParser(description="股票基金每日推荐系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("predict", help="执行每日预测推荐")

    review_parser = subparsers.add_parser("review", help="执行当日复盘")
    review_parser.add_argument("date", nargs="?", default=None, help="指定日期 (YYYY-MM-DD)")

    subparsers.add_parser("history", help="查看近30天命中率")
    subparsers.add_parser("schedule", help="启动定时调度")

    context_parser = subparsers.add_parser("context", help="查看某日要闻与政策（供后续分析）")
    context_parser.add_argument("date", nargs="?", default=None, help="日期 YYYY-MM-DD，默认今日")

    position_parser = subparsers.add_parser("position", help="个人持仓与卖出计划")
    position_parser.add_argument("sub", nargs="?", default="list", choices=["add", "list", "plan", "rm", "delete"], help="add=list=plan=rm")
    position_parser.add_argument("code", nargs="?", default="", help="标的代码（add 时必填）")
    position_parser.add_argument("buy_date", nargs="?", default="", help="买入日期 YYYY-MM-DD（add 时必填）")
    position_parser.add_argument("buy_price", nargs="?", default="0", help="买入价格（add 时必填）")
    position_parser.add_argument("quantity", nargs="?", default="0", help="数量（add 时必填）")
    position_parser.add_argument("--name", default="", help="名称（可选）")
    position_parser.add_argument("--category", default="stock", choices=["stock", "fund"], help="stock|fund")
    position_parser.add_argument("--target-price", type=float, default=None, help="目标卖出价")
    position_parser.add_argument("--stop-loss", type=float, default=None, help="止损价")
    position_parser.add_argument("--plan-sell-date", default=None, help="计划卖出日 YYYY-MM-DD")
    position_parser.add_argument("--note", default=None, help="备注")
    position_parser.add_argument("--id", type=int, default=None, help="持仓 id（plan/rm 时必填）")

    backtest_parser = subparsers.add_parser("backtest", help="基于历史推荐做 AKQuant 回测")
    backtest_parser.add_argument("--start", default=None, help="开始日期 YYYY-MM-DD")
    backtest_parser.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD")
    backtest_parser.add_argument("--cash", type=float, default=100000.0, help="初始资金")
    backtest_parser.add_argument("--max-symbols", type=int, default=20, help="最多回测标的数")

    args = parser.parse_args()

    if args.command == "predict":
        cmd_predict()
    elif args.command == "review":
        cmd_review(args.date)
    elif args.command == "history":
        cmd_history()
    elif args.command == "schedule":
        cmd_schedule()
    elif args.command == "context":
        cmd_context(args.date)
    elif args.command == "position":
        cmd_position(args)
    elif args.command == "backtest":
        cmd_backtest(start_date=args.start, end_date=args.end, cash=args.cash, max_symbols=args.max_symbols)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
