"""报告生成模块 — 将推荐和复盘结果格式化为 Markdown 文件。"""

from datetime import datetime
from pathlib import Path

from loguru import logger

from config.settings import OUTPUT_DIR
from core.zhouyi import get_daily_hexagram


def _ensure_dir(date_str: str) -> Path:
    day_dir = OUTPUT_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir


def generate_prediction_report(
    trade_date: str,
    stocks: dict[str, list[dict]],
    funds: list[dict],
    market_info: dict = None,
    market_news_list: list = None,
    policy_news_list: list = None,
    affected_sectors: list = None,
) -> str:
    """生成每日推荐报告（Markdown），返回文件路径。可传入要闻、政策与驱动板块。"""
    day_dir = _ensure_dir(trade_date)
    filepath = day_dir / f"推荐_{trade_date}.md"

    lines = [
        f"# 📊 每日推荐 — {trade_date}",
        f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # 今日卦象（周易参考，仅供文化娱乐）
    try:
        h = get_daily_hexagram(trade_date)
        lines.append("\n## ☯ 今日卦象\n")
        lines.append(f"**{h['full_name']}**（{h['name']}卦）  \n象意：{h['image']}  \n")
        if h.get("lunar"):
            lines.append(f"起卦：农历 {h['lunar']}，固定巳时。  \n")
        if h.get("dong_yao"):
            lines.append(f"动爻：第 {h['dong_yao']} 爻  \n")
        if h.get("ti_yong"):
            lines.append(f"体用：{h['ti_yong']}  \n")
        if h.get("hu_gua_name"):
            lines.append(f"互卦：{h['hu_gua_name']}  \n")
        if h.get("bian_gua_name"):
            lines.append(f"变卦：{h['bian_gua_name']}  \n")
        lines.append("*仅供传统文化参考，不构成投资依据*\n")
        logger.info(f"今日卦象已写入报告: {h['full_name']}（{h['name']}卦），农历 {h.get('lunar', '')}")
    except Exception as e:
        logger.warning(f"卦象获取或写入失败，已跳过: {e}")

    # 市场概况
    if market_info:
        lines.append("\n## 🌍 市场概况\n")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 上涨家数 | {market_info.get('up', '-')} |")
        lines.append(f"| 下跌家数 | {market_info.get('down', '-')} |")
        lines.append(f"| 涨停 | {market_info.get('limit_up', '-')} |")
        lines.append(f"| 跌停 | {market_info.get('limit_down', '-')} |")
        lines.append(f"| 上涨占比 | {market_info.get('up_ratio', '-')}% |")
        lines.append(f"| 平均涨跌幅 | {market_info.get('avg_change', '-')}% |")

    # 今日要闻与政策（来自当日入库数据，便于后续分析）
    if market_news_list or policy_news_list:
        lines.append("\n## 📰 今日要闻与政策\n")
        if market_news_list:
            lines.append("**市场要闻**\n")
            for x in market_news_list[:12]:
                title = (x.get("title") or "").strip()
                if title:
                    lines.append(f"- {title}")
            lines.append("")
        if policy_news_list:
            lines.append("**政策/宏观要闻**\n")
            for x in policy_news_list[:10]:
                title = (x.get("title") or "").strip()
                if title:
                    lines.append(f"- {title}")
            lines.append("")

    # 政策与新闻驱动板块（结合十四五/十五五与当日要闻，含要点摘要与板块明细）
    if affected_sectors:
        summary_item = next((s for s in affected_sectors if (s.get("name") or "").strip() == "_summary"), None)
        sector_list = [s for s in affected_sectors if (s.get("name") or "").strip() and (s.get("name") or "").strip() != "_summary"]
        if summary_item and (summary_item.get("reason") or "").strip():
            lines.append("\n## 📌 今日政策与新闻要点\n")
            lines.append("*结合国家十四五/十五五规划与当日要闻的摘要*\n")
            lines.append((summary_item.get("reason") or "").strip())
            lines.append("\n")
        if sector_list:
            lines.append("\n## 📌 政策与新闻驱动板块\n")
            lines.append("*以下板块在政策依据与今日新闻催化下可重点关注*\n")
            has_detail = any(s.get("policy_basis") or s.get("news_trigger") for s in sector_list)
            if has_detail:
                lines.append("| 板块 | 政策/规划依据 | 今日新闻触发 | 投资逻辑 |")
                lines.append("|------|---------------|--------------|----------|")
                for s in sector_list:
                    name = (s.get("name") or "").strip()
                    basis = (s.get("policy_basis") or s.get("reason") or "-")[:80]
                    trigger = (s.get("news_trigger") or "-")[:60]
                    logic = (s.get("logic") or s.get("reason") or "-")[:100]
                    lines.append(f"| {name} | {basis} | {trigger} | {logic} |")
            else:
                for s in sector_list:
                    name = (s.get("name") or "").strip()
                    reason = (s.get("reason") or "").strip()
                    if name:
                        lines.append(f"- **{name}**：{reason}" if reason else f"- **{name}**")
            lines.append("")

    # 股票推荐
    lines.append("\n---\n")
    stock_total = sum(len(items) for items in stocks.values())
    lines.append(f"## 📈 股票推荐 ({stock_total}只)\n")

    style_labels = {
        "aggressive": ("🔥 激进型 (30%)", "短线强势，适合追求高收益的操作"),
        "stable": ("🛡️ 稳健型 (50%)", "趋势稳健，适合中线持有"),
        "moderate": ("⚖️ 适中型 (20%)", "攻守兼备，综合评分较高"),
    }

    for style in ["aggressive", "stable", "moderate"]:
        items = stocks.get(style, [])
        label, desc = style_labels.get(style, (style, ""))
        lines.append(f"\n### {label}\n")
        lines.append(f"*{desc}*\n")

        if not items:
            lines.append("暂无推荐\n")
            continue

        lines.append(f"| 序号 | 代码 | 名称 | 现价 | 涨跌幅 | 量比 | 换手率 | PE | 技术 | 新闻 |")
        lines.append(f"|------|------|------|------|--------|------|--------|-----|------|------|")

        for i, s in enumerate(items, 1):
            lines.append(
                f"| {i} | {s['code']} | {s['name']} | {s['price']:.2f} | "
                f"{s.get('change_pct', 0):+.2f}% | {s.get('volume_ratio', 0):.1f} | "
                f"{s.get('turnover_rate', 0):.1f}% | {s.get('pe', 0):.1f} | "
                f"{s['tech_score']:.0f} | {s.get('news_score', 50):.0f} |"
            )

        lines.append("\n**技术信号、新闻与AI分析：**\n")
        for s in items:
            lines.append(f"**{s['name']}({s['code']})**")
            lines.append(f"- 筛选理由: {s.get('reason', '-')}")
            lines.append(f"- 技术信号: {', '.join(s.get('signals', []))}")
            if s.get("news_summary") and s["news_summary"] != "暂无近期新闻":
                lines.append(f"- 近期新闻: {s['news_summary']}")
            if s.get("ai_analysis"):
                lines.append(f"- AI分析: {s['ai_analysis']}")
            lines.append("")

    # 基金推荐
    lines.append("\n---\n")
    lines.append(f"## 💰 基金推荐 ({len(funds)}只)\n")

    if not funds:
        lines.append("暂无推荐\n")
    else:
        # 按类型分组
        etfs = [f for f in funds if f.get("fund_type") == "ETF"]
        stock_funds = [f for f in funds if f.get("fund_type") == "股票型"]
        hybrid_funds = [f for f in funds if f.get("fund_type") == "混合型"]

        for group_name, group in [("ETF基金", etfs), ("股票型基金", stock_funds), ("混合型基金", hybrid_funds)]:
            if not group:
                continue
            lines.append(f"\n#### {group_name} ({len(group)}只)\n")
            lines.append(f"| 序号 | 代码 | 名称 | 现价/净值 | 涨跌幅 | 评分 |")
            lines.append(f"|------|------|------|----------|--------|------|")
            for i, f in enumerate(group, 1):
                lines.append(
                    f"| {i} | {f['code']} | {f['name']} | {f.get('price', 0)} | "
                    f"{f.get('change_pct', 0):+.2f}% | {f.get('tech_score', 0):.0f} |"
                )
            lines.append("")

        lines.append("\n**AI分析：**\n")
        for f in funds:
            lines.append(f"**{f['name']}({f['code']})**")
            lines.append(f"- 推荐理由: {f.get('reason', '-')}")
            if f.get("ai_analysis"):
                lines.append(f"- AI分析: {f['ai_analysis']}")
            lines.append("")

    # 风险提示
    lines.append("\n---\n")
    lines.append("## ⚠️ 风险提示\n")
    lines.append("- 以上推荐基于量化筛选模型和AI分析，仅供参考，不构成投资建议")
    lines.append("- 股市有风险，投资需谨慎，请根据自身风险承受能力做决策")
    lines.append("- 短线操作需设置止损位，建议单只个股仓位不超过总资金的10%")

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"推荐报告已生成: {filepath}")
    return str(filepath)


def generate_review_report(review_data: dict) -> str:
    """生成复盘报告（Markdown），返回文件路径。"""
    trade_date = review_data.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
    day_dir = _ensure_dir(trade_date)
    filepath = day_dir / f"复盘_{trade_date}.md"

    summary = review_data.get("summary", {})
    results = review_data.get("results", [])
    ai_review = review_data.get("ai_review", "")

    lines = [
        f"# 📋 每日复盘 — {trade_date}",
        f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # 总体表现
    lines.append("\n## 📊 总体表现\n")
    stock_hit = summary.get("stock_hit", 0)
    stock_total = summary.get("stock_total", 0)
    fund_hit = summary.get("fund_hit", 0)
    fund_total = summary.get("fund_total", 0)
    avg_return = summary.get("avg_return", 0)

    stock_rate = f"{stock_hit/stock_total*100:.0f}%" if stock_total else "-"
    fund_rate = f"{fund_hit/fund_total*100:.0f}%" if fund_total else "-"

    lines.append(f"| 类别 | 命中/总数 | 命中率 |")
    lines.append(f"|------|----------|--------|")
    lines.append(f"| 股票 | {stock_hit}/{stock_total} | {stock_rate} |")
    lines.append(f"| 基金 | {fund_hit}/{fund_total} | {fund_rate} |")
    lines.append(f"| **平均收益** | | **{avg_return:+.2f}%** |")

    # 明细
    stock_results = [r for r in results if r.get("category") == "stock"]
    fund_results = [r for r in results if r.get("category") == "fund"]

    if stock_results:
        lines.append("\n## 📈 股票推荐复盘\n")
        lines.append(f"| 代码 | 名称 | 收盘价 | 涨跌幅 | 结果 |")
        lines.append(f"|------|------|--------|--------|------|")
        for r in sorted(stock_results, key=lambda x: x.get("change_pct", 0), reverse=True):
            icon = "✅" if r.get("hit") else "❌"
            lines.append(
                f"| {r['code']} | {r['name']} | {r.get('close_price', '-')} | "
                f"{r.get('change_pct', 0):+.2f}% | {icon} |"
            )

    if fund_results:
        lines.append("\n## 💰 基金推荐复盘\n")
        lines.append(f"| 代码 | 名称 | 收盘价 | 涨跌幅 | 结果 |")
        lines.append(f"|------|------|--------|--------|------|")
        for r in sorted(fund_results, key=lambda x: x.get("change_pct", 0), reverse=True):
            icon = "✅" if r.get("hit") else "❌"
            lines.append(
                f"| {r['code']} | {r['name']} | {r.get('close_price', '-')} | "
                f"{r.get('change_pct', 0):+.2f}% | {icon} |"
            )

    # AI 复盘
    if ai_review:
        lines.append("\n## 🤖 AI 复盘分析\n")
        lines.append(ai_review)

    lines.append("\n---\n")
    lines.append("*本报告由量化筛选模型 + DeepSeek AI 自动生成*")

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"复盘报告已生成: {filepath}")
    return str(filepath)
