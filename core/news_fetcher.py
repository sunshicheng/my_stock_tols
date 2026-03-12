"""新闻因子模块 — 获取个股/市场新闻并做简单情感与热度打分，供筛选与 AI 分析使用。

数据源：AKShare（东方财富个股新闻 stock_news_em；市场要闻优先 news_cctv，备选 stock_info_global_em）。
"""

import re
import time
from datetime import datetime

import akshare as ak
import pandas as pd
from loguru import logger

# 简单利好/利空关键词（可扩展）
KEYWORDS_POSITIVE = [
    "利好", "大涨", "涨停", "突破", "签约", "中标", "获批", "增产", "扭亏",
    "预增", "增持", "回购", "分红", "收购", "重组", "注入", "订单", "创新高",
]
KEYWORDS_NEGATIVE = [
    "利空", "大跌", "跌停", "减持", "亏损", "暴雷", "违规", "调查", "处罚",
    "诉讼", "停产", "破产", "爆仓", "违约", "预亏", "下滑", "裁员",
]


def _retry(fn, *args, retries: int = 2, delay: float = 1.0, **kwargs):
    from config.settings import SLOW_FETCH
    if SLOW_FETCH:
        delay = max(delay, 2.0)
    for i in range(retries):
        try:
            return fn(*args, **kwargs)
        except re.error as e:
            # AKShare 内部正则可能抛 invalid escape sequence \u，不重试
            logger.debug(f"新闻接口正则错误，跳过重试: {e}")
            return pd.DataFrame()
        except Exception as e:
            err_msg = str(e).lower()
            if "escape sequence" in err_msg or "regex" in err_msg or "regular expression" in err_msg:
                logger.debug(f"新闻接口解析错误，跳过重试: {e}")
                return pd.DataFrame()
            logger.debug(f"news fetch retry {i+1}: {e}")
            if i < retries - 1:
                time.sleep(delay)
    return pd.DataFrame()


def fetch_stock_news(symbol: str, max_items: int = 15) -> list[dict]:
    """获取单只股票近期新闻（AKShare 东方财富）。返回带标题、时间、摘要、情感。"""
    symbol = str(symbol).strip()
    if len(symbol) != 6 or not symbol.isdigit():
        return []

    try:
        df = _retry(ak.stock_news_em, symbol=symbol, retries=2, delay=1.5)
    except Exception as e:
        logger.debug(f"个股新闻获取失败 {symbol}: {e}")
        return []

    if df.empty:
        return []

    out = []
    for _, row in df.head(max_items).iterrows():
        title = str(row.get("新闻标题", ""))
        content = str(row.get("新闻内容", ""))[:500]
        pub_time = row.get("发布时间", "")
        source = str(row.get("文章来源", ""))
        link = str(row.get("新闻链接", ""))

        sentiment, score = _sentiment_score(title + " " + content)
        recency = _recency_score(pub_time)

        out.append({
            "title": title,
            "content": content,
            "pub_time": pub_time,
            "source": source,
            "link": link,
            "sentiment": sentiment,
            "sentiment_score": score,
            "recency_score": recency,
        })
    return out


def _sentiment_score(text: str) -> tuple[str, float]:
    """简单关键词情感：利好/利空/中性，及 -1~1 分数。"""
    if not text:
        return "中性", 0.0
    text = text.lower()
    pos = sum(1 for k in KEYWORDS_POSITIVE if k in text)
    neg = sum(1 for k in KEYWORDS_NEGATIVE if k in text)
    if pos > neg:
        return "利好", min(1.0, 0.3 + pos * 0.2)
    if neg > pos:
        return "利空", max(-1.0, -0.3 - neg * 0.2)
    return "中性", 0.0


def _recency_score(pub_time) -> float:
    """新闻时效性打分：越近越高，0~1。"""
    if not pub_time:
        return 0.3
    try:
        if isinstance(pub_time, datetime):
            dt = pub_time
        elif isinstance(pub_time, str):
            # 兼容 "2026-03-12 10:00" 或 "03-12 10:00"
            pub_time = str(pub_time).strip()
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(pub_time[:19], fmt)
                    if dt.year == 1900:
                        dt = dt.replace(year=datetime.now().year)
                    break
                except ValueError:
                    continue
            else:
                return 0.3
        else:
            return 0.3
        delta = datetime.now() - dt
        if delta.days > 7:
            return 0.1
        if delta.days > 3:
            return 0.3
        if delta.days >= 1:
            return 0.6
        return 1.0
    except Exception:
        return 0.3


def news_to_summary(news_list: list[dict], max_headlines: int = 5) -> str:
    """将新闻列表压成一段摘要，供 AI 与报告使用。"""
    if not news_list:
        return "暂无近期新闻"
    lines = []
    for n in news_list[:max_headlines]:
        title = (n.get("title") or "").strip()
        sentiment = n.get("sentiment", "中性")
        pub = n.get("pub_time", "")
        if title:
            lines.append(f"[{sentiment}] {title} ({pub})")
    return "；".join(lines) if lines else "暂无近期新闻"


def news_score_for_stock(news_list: list[dict]) -> float:
    """综合新闻热度与情感，得到 0~100 的新闻因子得分。"""
    if not news_list:
        return 50.0  # 无新闻给中性分
    base = 50.0
    for n in news_list:
        base += n.get("sentiment_score", 0) * 15
        base += (n.get("recency_score", 0) - 0.5) * 10
    return max(0, min(100, round(base, 1)))


def fetch_market_news(max_items: int = 20) -> list[dict]:
    """获取市场/财经要闻。优先央视 news_cctv，失败时用东财 stock_info_global_em（AKShare 资讯数据）。"""
    out = []
    try:
        df = _retry(ak.news_cctv, retries=2, delay=1.0)
    except Exception as e:
        logger.debug(f"市场新闻(央视)获取失败: {e}")
        df = None
    if df is not None and not df.empty:
        for _, row in df.head(max_items).iterrows():
            out.append({
                "date": str(row.get("date", "")),
                "title": str(row.get("title", "")),
                "content": str(row.get("content", ""))[:300],
            })
        return out
    # 备选：东财全球资讯（文档-资讯数据）
    try:
        df = _retry(ak.stock_info_global_em, retries=2, delay=1.0)
    except Exception as e:
        logger.debug(f"市场新闻(东财)获取失败: {e}")
        return []
    if df.empty:
        return []
    for _, row in df.head(max_items).iterrows():
        out.append({
            "date": str(row.get("发布时间", "")),
            "title": str(row.get("标题", "")),
            "content": str(row.get("摘要", ""))[:300],
        })
    return out


def market_news_summary(max_items: int = 10) -> str:
    """市场要闻摘要，一段话给 AI。"""
    items = fetch_market_news(max_items)
    if not items:
        return "暂无市场要闻"
    lines = [f"- {x['title']}" for x in items if x.get("title")]
    return "\n".join(lines[:max_items])


def fetch_policy_news(max_items: int = 15) -> list[dict]:
    """获取政策/宏观要闻（如财经早餐），供推荐与 AI 参考，并可与市场要闻一起入库便于后续分析。"""
    out = []
    try:
        df = _retry(ak.stock_info_cjzc_em, retries=2, delay=1.0)
    except Exception as e:
        logger.debug(f"政策/财经早餐获取失败: {e}")
        return []
    if df.empty:
        return []
    for _, row in df.head(max_items).iterrows():
        out.append({
            "date": str(row.get("发布时间", "")),
            "title": str(row.get("标题", "")),
            "content": str(row.get("摘要", ""))[:400],
        })
    return out


def policy_news_summary(max_items: int = 8) -> str:
    """政策/宏观要闻摘要，一段话给 AI。"""
    items = fetch_policy_news(max_items)
    if not items:
        return "暂无政策要闻"
    lines = [f"- {x['title']}" for x in items if x.get("title")]
    return "\n".join(lines[:max_items])
