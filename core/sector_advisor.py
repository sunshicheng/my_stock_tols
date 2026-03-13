"""政策与新闻驱动板块 — 结合十四五/十五五规划与当日要闻，由 AI 输出结构化政策分析与板块推荐。"""

import re
from loguru import logger

from config.policy_themes import get_policy_themes_summary


def _call_deepseek(prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> str:
    from openai import OpenAI
    from config.settings import AI_API_KEY, AI_BASE_URL, AI_MODEL
    if not AI_API_KEY:
        return ""
    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            pt = getattr(usage, "prompt_tokens", 0) or 0
            ct = getattr(usage, "completion_tokens", 0) or 0
            tt = getattr(usage, "total_tokens", None) or (pt + ct)
            logger.info(f"DeepSeek 政策/板块分析 token: 输入={pt}, 输出={ct}, 合计={tt}")
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning(f"政策与板块分析 AI 调用失败: {e}")
        return ""


def _parse_structured_policy_output(text: str) -> dict:
    """解析 AI 返回的结构化内容：要点摘要 + 各板块的政策依据、新闻触发、投资逻辑。"""
    result = {"summary": "", "sectors": []}
    if not text or "[暂不可用" in text:
        return result

    # 第一部分：今日政策与新闻要点摘要（到「驱动板块」或「板块」列表之前）
    summary_end = re.search(r"\n#+\s*[一二三四五]?[、.]?\s*今日?.?驱动板块|板块列表|以下板块", text, re.I)
    if summary_end:
        result["summary"] = text[: summary_end.start()].strip()
    else:
        # 取前两段或前 300 字作为摘要
        blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 10]
        result["summary"] = "\n\n".join(blocks[:2]) if blocks else text[:400]

    # 第二部分：按 ## 板块名 或 1. 板块名 分块解析
    sector_blocks = re.split(r"\n\s*#+\s*|\n\s*[一二三四五六七八九十\d]+[.、]\s*", text)
    for block in sector_blocks:
        block = block.strip()
        if len(block) < 15:
            continue
        name = ""
        policy_basis = ""
        news_trigger = ""
        logic = ""

        # 首行作为板块名（取第一行或「板块名：」前）
        first_line = block.split("\n")[0].strip()
        for sep in ("：", ":", "|", "—"):
            if sep in first_line:
                name = first_line.split(sep, 1)[0].strip()
                break
        if not name:
            name = first_line[:16].strip()
        # 清理板块名中的 markdown
        name = re.sub(r"^\*+\s*|\s*\*+$", "", name).strip()
        if not name or len(name) > 20:
            continue

        rest = block[len(first_line) :].strip()
        # 解析「政策/规划依据」「今日新闻触发」「投资逻辑」
        for label, key in [
            ("政策[/规划]?依据", "policy_basis"),
            ("今日新闻触发|新闻触发", "news_trigger"),
            ("投资逻辑|逻辑", "logic"),
        ]:
            m = re.search(rf"{label}\s*[：:]\s*(.+?)(?=\n\s*[-*]?\s*[政策今日投资]|$)", rest, re.S | re.I)
            if m and m.group(1) is not None:
                val = (m.group(1) or "").strip()
                val = re.sub(r"\n+", " ", val)[:200]
                if key == "policy_basis":
                    policy_basis = val
                elif key == "news_trigger":
                    news_trigger = val
                else:
                    logic = val

        # 若未解析出单独字段，整段作为 reason
        reason = logic or policy_basis or news_trigger or rest[:150]
        result["sectors"].append({
            "name": name,
            "reason": reason,
            "policy_basis": policy_basis or None,
            "news_trigger": news_trigger or None,
            "logic": logic or None,
        })

    result["sectors"] = result["sectors"][:8]
    return result


def _parse_sectors_text(text: str) -> list[dict]:
    """简单格式回退：从「板块名：理由」行解析出 [{name, reason, ...}, ...]。"""
    if not text or "[暂不可用" in text:
        return []
    result = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        for prefix in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "- ", "• "):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        name, reason = "", ""
        for sep in ("：", ":", "|", "—"):
            if sep in line:
                parts = line.split(sep, 1)
                name = (parts[0] or "").strip()
                reason = (parts[1] or "").strip() if len(parts) > 1 else ""
                break
        if not name:
            name = line[:20]
            reason = line[20:] if len(line) > 20 else ""
        name = re.sub(r"^\*+\s*|\s*\*+$", "", name).strip()
        if name and len(name) <= 20 and name != "_summary":
            result.append({"name": name, "reason": reason[:200], "policy_basis": None, "news_trigger": None, "logic": None})
    return result[:8]


def get_affected_sectors(
    market_news_list: list,
    policy_news_list: list,
    max_sectors: int = 5,
) -> list[dict]:
    """根据当日市场要闻、政策要闻与十四五/十五五规划，用 AI 生成结构化的「今日政策要点摘要」与「政策与新闻驱动板块」。"""
    policy_summary = get_policy_themes_summary()
    market_lines = [x.get("title", "") for x in (market_news_list or [])[:14] if x.get("title")]
    policy_lines = [x.get("title", "") for x in (policy_news_list or [])[:12] if x.get("title")]

    if not market_lines and not policy_lines:
        logger.debug("无要闻，跳过政策与板块分析")
        return []

    system = (
        "你是 A 股政策与板块解读专家，熟悉国家十四五、十五五规划及产业政策。\n"
        "请根据下方「规划概要」与「今日要闻」，完成两项输出：\n\n"
        "**一、今日政策与新闻要点摘要**\n"
        "用 2～4 句话概括：今日要闻中与 A 股最相关的政策/宏观/行业要点，以及对市场或板块的直接影响。\n\n"
        "**二、今日政策与新闻驱动板块**\n"
        "列出 3～5 个当前最值得关注的 A 股板块/概念（如新能源、半导体、医药、数字经济等）。"
        "每个板块严格按以下结构书写：\n"
        "## 板块名\n"
        "- 政策/规划依据：（结合十四五/十五五或近期政策，一句话说明该板块的政策支撑）\n"
        "- 今日新闻触发：（今日要闻中哪条或哪类消息直接利好/催化该板块）\n"
        "- 投资逻辑：（1～2 句话，为何当前时点该板块值得关注）\n\n"
        "只输出上述一、二两部分，不要其他开场白或总结。"
    )
    prompt = (
        f"{policy_summary}\n\n"
        "【今日市场要闻】\n" + "\n".join(market_lines or ["暂无"]) + "\n\n"
        "【今日政策/宏观要闻】\n" + "\n".join(policy_lines or ["暂无"]) + "\n\n"
        "请按「一、今日政策与新闻要点摘要」和「二、今日政策与新闻驱动板块」两部分输出。"
    )
    logger.info("正在生成政策要点与驱动板块（结构化）...")
    raw = _call_deepseek(prompt, system, temperature=0.2, max_tokens=2048)
    parsed = _parse_structured_policy_output(raw)
    sectors = parsed.get("sectors", [])[:max_sectors]
    summary = parsed.get("summary", "").strip()

    # 若结构化解析未得到板块，用简单格式再解析一次
    if not sectors and raw:
        simple = _parse_sectors_text(raw)
        if simple:
            sectors = simple[:max_sectors]
    if sectors:
        logger.info(f"驱动板块: {[s['name'] for s in sectors]}")
    if summary:
        sectors.insert(0, {"name": "_summary", "reason": summary, "policy_basis": None, "news_trigger": None, "logic": None})
    return sectors