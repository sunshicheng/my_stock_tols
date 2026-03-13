"""DeepSeek AI 分析模块 — 调用大模型对筛选结果做综合研判。"""

from openai import OpenAI
from loguru import logger

from config.settings import AI_API_KEY, AI_BASE_URL, AI_MODEL
from core.news_fetcher import market_news_summary, policy_news_summary
from core.zhouyi import zhouyi_summary_for_ai


def _get_client() -> OpenAI:
    if not AI_API_KEY:
        raise ValueError("未配置 AI API Key，请在设置页或 .env 中配置 AI_API_KEY")
    return OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


def _call_deepseek(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            pt = getattr(usage, "prompt_tokens", 0) or 0
            ct = getattr(usage, "completion_tokens", 0) or 0
            tt = getattr(usage, "total_tokens", None) or (pt + ct)
            logger.info(f"DeepSeek 本次调用 token: 输入={pt}, 输出={ct}, 合计={tt}")
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"DeepSeek 调用失败: {e}")
        return f"[AI分析暂不可用: {e}]"


# ======================== 股票分析 ========================

def _news_lists_to_summary(market_list: list, policy_list: list, market_items: int = 8, policy_items: int = 8) -> str:
    """将市场要闻与政策要闻列表转为给 AI 的摘要文本。"""
    parts = []
    if market_list:
        lines = [f"- {x.get('title', '')}" for x in market_list[:market_items] if x.get("title")]
        if lines:
            parts.append("近期市场要闻：\n" + "\n".join(lines))
    if policy_list:
        lines = [f"- {x.get('title', '')}" for x in policy_list[:policy_items] if x.get("title")]
        if lines:
            parts.append("近期政策/宏观要闻：\n" + "\n".join(lines))
    return "\n\n".join(parts) if parts else ""


def analyze_stocks(
    stocks: dict[str, list[dict]],
    market_info: dict = None,
    market_news_list: list = None,
    policy_news_list: list = None,
    affected_sectors: list = None,
) -> dict[str, list[dict]]:
    """对分类后的股票推荐列表进行 AI 分析。可传入要闻、政策与今日驱动板块。"""
    market_ctx = ""

    try:
        from datetime import datetime
        trade_date = datetime.now().strftime("%Y-%m-%d")
        zhouyi_line = zhouyi_summary_for_ai(trade_date)
        market_ctx += zhouyi_line + "\n\n"
        logger.info("已加入今日卦象供股票分析参考")
    except Exception as e:
        logger.warning(f"周易卦象获取失败，AI 分析将不包含卦象: {e}")

    if market_info:
        market_ctx += (
            f"今日市场概况：上涨 {market_info.get('up', '?')} 家，"
            f"下跌 {market_info.get('down', '?')} 家，"
            f"涨停 {market_info.get('limit_up', '?')} 家，"
            f"跌停 {market_info.get('limit_down', '?')} 家，"
            f"平均涨跌幅 {market_info.get('avg_change', '?')}%\n\n"
        )

    if market_news_list is not None or policy_news_list is not None:
        news_block = _news_lists_to_summary(market_news_list or [], policy_news_list or [])
        if news_block:
            market_ctx += news_block + "\n\n"
    else:
        try:
            market_news = market_news_summary(max_items=8)
            if market_news and "暂无" not in market_news:
                market_ctx += "近期市场要闻：\n" + market_news + "\n\n"
        except Exception as e:
            logger.debug(f"市场要闻获取失败: {e}")
        try:
            policy_news = policy_news_summary(max_items=8)
            if policy_news and "暂无" not in policy_news:
                market_ctx += "近期政策/宏观要闻：\n" + policy_news + "\n\n"
        except Exception as e:
            logger.debug(f"政策要闻获取失败: {e}")

    if affected_sectors:
        sector_parts = []
        for s in affected_sectors:
            name = (s.get("name") or "").strip()
            if not name or name == "_summary":
                continue
            parts = [name]
            if s.get("policy_basis"):
                parts.append(f"政策依据：{s['policy_basis'][:100]}")
            if s.get("news_trigger"):
                parts.append(f"新闻触发：{s['news_trigger'][:80]}")
            if s.get("logic"):
                parts.append(s["logic"][:120])
            elif s.get("reason"):
                parts.append(s["reason"][:120])
            sector_parts.append(" | ".join(parts))
        if sector_parts:
            market_ctx += "今日政策与新闻驱动板块（可结合板块热点分析个股）：\n" + "\n".join(f"- {x}" for x in sector_parts) + "\n\n"

    system = (
        "你是一位专业的 A 股短线投资分析师，同时了解中国传统文化中的周易智慧。"
        "请结合提供的今日卦象、技术指标、近期市场要闻、国家政策/宏观要闻与**今日政策与新闻驱动板块**，对每只股票做简要投资分析。"
        "**必须**包含以下 5 项（缺一不可）："
        "① 核心看点（可适度结合卦象、政策与所属板块）"
        "② 潜在风险"
        "③ 短期操作建议（1-3个交易日）"
        "④ **建议买入**：明确写出买入时机，如「现价附近介入」或「回调至 X 元附近可考虑」"
        "⑤ **建议卖出**：明确写出卖出计划，如「目标价 X 元，止损 X 元」或「持有 1～2 周，跌破 X 元止损」"
        "若某只股票所属板块在今日驱动板块中或近期有明确利好/利空，请在分析中体现。卦象仅作参考。每只股票分析控制在 120 字以内。"
    )

    for style, items in stocks.items():
        if not items:
            continue

        style_label = {"aggressive": "激进型", "stable": "稳健型", "moderate": "适中型"}.get(style, style)
        stock_info = "\n".join(
            f"- {s['name']}({s['code']}): 现价{s['price']}元, "
            f"涨跌幅{s.get('change_pct', 0):.2f}%, "
            f"量比{s.get('volume_ratio', 0):.1f}, "
            f"换手率{s.get('turnover_rate', 0):.1f}%, "
            f"PE{s.get('pe', 0):.1f}, "
            f"技术评分{s['tech_score']}, 新闻评分{s.get('news_score', 50):.0f}; "
            f"技术信号: {'; '.join(s['signals'][:4])}; "
            f"近期新闻: {s.get('news_summary', '暂无')}"
            for s in items
        )

        prompt = (
            f"{market_ctx}"
            f"以下是今日【{style_label}】推荐股票（共{len(items)}只），请逐一分析：\n\n"
            f"{stock_info}\n\n"
            f"请按序号逐一给出分析，**每条必须包含「建议买入」和「建议卖出」**，格式示例：\n"
            f"【股票名称】核心看点 | 风险提示 | 操作建议 | 建议买入：xxx | 建议卖出：目标xxx 止损xxx"
        )

        logger.info(f"正在调用 DeepSeek 分析 {style_label} 股票 ({len(items)}只)...")
        analysis = _call_deepseek(prompt, system)

        parts = _split_analysis(analysis, [s["name"] for s in items])
        for i, item in enumerate(items):
            item["ai_analysis"] = parts[i] if i < len(parts) else "分析解析失败"

    return stocks


# ======================== 基金分析 ========================

def analyze_funds(
    funds: list[dict],
    market_news_list: list = None,
    policy_news_list: list = None,
    affected_sectors: list = None,
) -> list[dict]:
    """对推荐基金列表进行 AI 分析。可传入要闻、政策与今日驱动板块以结合宏观与板块环境。"""
    if not funds:
        return funds

    try:
        zhouyi_line = zhouyi_summary_for_ai()
        fund_ctx = zhouyi_line + "\n\n"
        logger.info("已加入今日卦象供基金分析参考")
    except Exception as e:
        logger.warning(f"周易卦象获取失败，基金分析将不包含卦象: {e}")
        fund_ctx = ""

    if market_news_list is not None or policy_news_list is not None:
        news_block = _news_lists_to_summary(market_news_list or [], policy_news_list or [], 6, 6)
        if news_block:
            fund_ctx += news_block + "\n\n"

    if affected_sectors:
        sector_parts = []
        for s in affected_sectors:
            name = (s.get("name") or "").strip()
            if not name or name == "_summary":
                continue
            parts = [name]
            if s.get("policy_basis"):
                parts.append(f"政策依据：{s['policy_basis'][:100]}")
            if s.get("news_trigger"):
                parts.append(f"新闻触发：{s['news_trigger'][:80]}")
            if s.get("logic"):
                parts.append(s["logic"][:120])
            elif s.get("reason"):
                parts.append(s["reason"][:120])
            sector_parts.append(" | ".join(parts))
        if sector_parts:
            fund_ctx += "今日政策与新闻驱动板块（可结合板块配置建议）：\n" + "\n".join(f"- {x}" for x in sector_parts) + "\n\n"

    system = (
        "你是一位专业的基金投资分析师，可适度结合传统文化中的周易智慧与当前政策、宏观环境及**今日政策与新闻驱动板块**。"
        "请基于提供的基金数据（及今日卦象、市场与政策要闻、驱动板块），对每只基金做简要分析。"
        "**必须**包含以下 5 项（缺一不可）："
        "① 基金特点"
        "② 近期表现与政策/宏观/板块关联"
        "③ 短期配置建议"
        "④ **建议买入**：如「现净值/现价附近可考虑定投」或「分批介入」"
        "⑤ **建议卖出**：如「目标收益 X% 止盈」或「持有 X 周/月，跌破 X 止损」"
        "卦象仅作参考。每只基金控制在 100 字以内。"
    )

    fund_info = "\n".join(
        f"- {f['name']}({f['code']}): 类型={f.get('fund_type', '?')}, "
        f"{'净值' if f.get('fund_type') != 'ETF' else '现价'}{f.get('price', 0)}, "
        f"涨跌幅{f.get('change_pct', 0):.2f}%, "
        f"技术/评分{f.get('tech_score', 0):.0f}, "
        f"信号: {'; '.join(f.get('signals', [])[:3])}"
        for f in funds
    )

    prompt = (
        f"{fund_ctx}"
        f"以下是今日推荐基金（共{len(funds)}只），请逐一分析：\n\n"
        f"{fund_info}\n\n"
        f"请按序号逐一给出分析，**每条必须包含「建议买入」和「建议卖出」**，格式示例：\n"
        f"【基金名称】基金特点 | 近期解读 | 配置建议 | 建议买入：xxx | 建议卖出：xxx"
    )

    logger.info(f"正在调用 DeepSeek 分析基金 ({len(funds)}只)...")
    analysis = _call_deepseek(prompt, system)

    parts = _split_analysis(analysis, [f["name"] for f in funds])
    for i, fund in enumerate(funds):
        fund["ai_analysis"] = parts[i] if i < len(parts) else "分析解析失败"

    return funds


# ======================== 复盘分析 ========================

def analyze_review(recommendations: list[dict], actual_results: list[dict]) -> str:
    """对当日推荐进行 AI 复盘总结。"""
    system = (
        "你是一位专业的投资复盘分析师。请基于今日推荐和实际表现数据，"
        "做出深入的复盘总结，包括：\n"
        "1. 整体命中率分析\n"
        "2. 表现最好和最差的标的分析\n"
        "3. 筛选模型的优缺点反思\n"
        "4. 明日操作方向建议\n"
        "要求言之有物，不要泛泛而谈，字数控制在500字以内。"
    )

    rec_text = "\n".join(
        f"- {r['name']}({r['code']}): 推荐理由={r.get('reason', '?')}"
        for r in recommendations
    )

    result_text = "\n".join(
        f"- {r['name']}({r['code']}): "
        f"评分{r.get('recommend_price', '?')} → 收盘价{r.get('close_price', '?')}, "
        f"涨跌幅{r.get('change_pct', 0):.2f}%, "
        f"{'✅ 命中' if r.get('hit') else '❌ 未命中'}"
        for r in actual_results
    )

    prompt = (
        f"=== 今日推荐 ===\n{rec_text}\n\n"
        f"=== 实际表现 ===\n{result_text}\n\n"
        f"请做出复盘总结。"
    )

    return _call_deepseek(prompt, system, temperature=0.5)


# ======================== 辅助函数 ========================

def _split_analysis(text: str, names: list[str]) -> list[str]:
    """将 AI 的批量分析按标的名称拆分。"""
    if not text or not names:
        return [text] * len(names)

    parts = []
    lines = text.strip().split("\n")
    current = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        is_header = any(name in line for name in names) and (line.startswith("【") or line.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")))
        if is_header and current:
            parts.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        parts.append("\n".join(current))

    while len(parts) < len(names):
        parts.append("暂无分析")

    return parts
