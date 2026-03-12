"""SQLite 存储层 — 记录每日推荐与复盘结果，用于追踪历史表现。"""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from config.settings import DB_PATH

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS recommendations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date  TEXT    NOT NULL,
    category    TEXT    NOT NULL,  -- stock / fund
    style       TEXT,              -- aggressive / stable / moderate
    code        TEXT    NOT NULL,
    name        TEXT,
    score       REAL,
    reason      TEXT,
    ai_analysis TEXT,
    created_at  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date       TEXT NOT NULL,
    category         TEXT NOT NULL,
    code             TEXT NOT NULL,
    name             TEXT,
    recommend_price  REAL,
    close_price      REAL,
    change_pct       REAL,
    hit              INTEGER,  -- 1=涨 0=跌
    ai_review        TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS daily_summary (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date  TEXT    NOT NULL UNIQUE,
    stock_hit   INTEGER,
    stock_total INTEGER,
    fund_hit    INTEGER,
    fund_total  INTEGER,
    avg_return  REAL,
    summary     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS daily_context (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date   TEXT NOT NULL,
    context_type TEXT NOT NULL,   -- 'market_news' | 'policy_news'
    content      TEXT NOT NULL,   -- JSON array of {date, title, content}
    created_at   TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(trade_date, context_type)
);

CREATE TABLE IF NOT EXISTS positions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL,
    name           TEXT,
    category       TEXT NOT NULL,  -- stock / fund
    buy_date       TEXT NOT NULL,
    buy_price      REAL NOT NULL,
    quantity       REAL NOT NULL,
    target_price   REAL,           -- 目标卖出价
    stop_loss      REAL,           -- 止损价
    plan_sell_date TEXT,          -- 计划卖出日 YYYY-MM-DD
    note           TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript(_CREATE_TABLES)


def save_recommendations(trade_date: str, items: list[dict]):
    """批量保存推荐记录。每条 dict 需包含 category/style/code/name/score/reason/ai_analysis。"""
    with _conn() as conn:
        conn.executemany(
            """INSERT INTO recommendations
               (trade_date, category, style, code, name, score, reason, ai_analysis)
               VALUES (:trade_date, :category, :style, :code, :name, :score, :reason, :ai_analysis)""",
            [{**item, "trade_date": trade_date} for item in items],
        )


def get_recommendations(trade_date: str, category: Optional[str] = None) -> list[dict]:
    sql = "SELECT * FROM recommendations WHERE trade_date = ?"
    params: list = [trade_date]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY score DESC"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def save_reviews(trade_date: str, items: list[dict]):
    with _conn() as conn:
        conn.executemany(
            """INSERT INTO reviews
               (trade_date, category, code, name, recommend_price, close_price, change_pct, hit, ai_review)
               VALUES (:trade_date, :category, :code, :name, :recommend_price, :close_price, :change_pct, :hit, :ai_review)""",
            [{**item, "trade_date": trade_date} for item in items],
        )


def save_daily_summary(trade_date: str, summary: dict):
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_summary
               (trade_date, stock_hit, stock_total, fund_hit, fund_total, avg_return, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                trade_date,
                summary.get("stock_hit", 0),
                summary.get("stock_total", 0),
                summary.get("fund_hit", 0),
                summary.get("fund_total", 0),
                summary.get("avg_return", 0.0),
                summary.get("summary", ""),
            ),
        )


def save_daily_summary_after_predict(trade_date: str, stock_total: int, fund_total: int):
    """预测完成后写入当日汇总（仅推荐只数），命中与收益待复盘后更新。"""
    save_daily_summary(trade_date, {
        "stock_hit": 0,
        "stock_total": stock_total,
        "fund_hit": 0,
        "fund_total": fund_total,
        "avg_return": 0.0,
        "summary": "待复盘",
    })


def get_recent_accuracy(days: int = 30) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_summary ORDER BY trade_date DESC LIMIT ?",
            (days,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_daily_context(trade_date: str, market_news: list, policy_news: list, affected_sectors: list = None):
    """保存当日市场要闻、政策要闻与政策驱动板块，便于后续分析。"""
    with _conn() as conn:
        if market_news is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_context (trade_date, context_type, content)
                   VALUES (?, 'market_news', ?)""",
                (trade_date, json.dumps(market_news, ensure_ascii=False)),
            )
        if policy_news is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_context (trade_date, context_type, content)
                   VALUES (?, 'policy_news', ?)""",
                (trade_date, json.dumps(policy_news, ensure_ascii=False)),
            )
        if affected_sectors is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_context (trade_date, context_type, content)
                   VALUES (?, 'affected_sectors', ?)""",
                (trade_date, json.dumps(affected_sectors, ensure_ascii=False)),
            )


def get_daily_context(trade_date: str) -> dict:
    """读取某日的要闻、政策与驱动板块，返回 {'market_news': [...], 'policy_news': [...], 'affected_sectors': [...]}。"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT context_type, content FROM daily_context WHERE trade_date = ?",
            (trade_date,),
        ).fetchall()
    out = {"market_news": [], "policy_news": [], "affected_sectors": []}
    for r in rows:
        ctx_type = r["context_type"]
        if ctx_type not in out:
            continue
        if r["content"]:
            try:
                out[ctx_type] = json.loads(r["content"])
            except (json.JSONDecodeError, TypeError):
                out[ctx_type] = []
    return out


def add_position(
    code: str,
    name: str,
    category: str,
    buy_date: str,
    buy_price: float,
    quantity: float,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    plan_sell_date: Optional[str] = None,
    note: Optional[str] = None,
) -> int:
    """添加一条持仓记录，返回 id。"""
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO positions (code, name, category, buy_date, buy_price, quantity, target_price, stop_loss, plan_sell_date, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, name or "", category, buy_date, buy_price, quantity, target_price, stop_loss, plan_sell_date or None, note or None),
        )
        return cur.lastrowid


def list_positions(only_open: bool = True) -> list[dict]:
    """列出持仓。only_open=True 时仅返回未设置 plan_sell_date 或未标记清仓的（当前表结构下即全部）。"""
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM positions ORDER BY buy_date DESC, id DESC").fetchall()
    return [dict(r) for r in rows]


def update_position(
    position_id: int,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    plan_sell_date: Optional[str] = None,
    note: Optional[str] = None,
) -> bool:
    """更新持仓的卖出计划字段。"""
    with _conn() as conn:
        cur = conn.execute(
            """UPDATE positions SET target_price=COALESCE(?, target_price), stop_loss=COALESCE(?, stop_loss),
               plan_sell_date=COALESCE(?, plan_sell_date), note=COALESCE(?, note) WHERE id = ?""",
            (target_price, stop_loss, plan_sell_date, note, position_id),
        )
        return cur.rowcount > 0


def delete_position(position_id: int) -> bool:
    """删除一条持仓（如已清仓可删或保留做历史）。"""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        return cur.rowcount > 0


def get_recommendations_by_date_range(start_date: str, end_date: str, category: Optional[str] = None) -> list[dict]:
    """按日期范围获取推荐记录，供回测使用。"""
    sql = "SELECT * FROM recommendations WHERE trade_date >= ? AND trade_date <= ?"
    params: list = [start_date, end_date]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY trade_date, score DESC"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


init_db()
