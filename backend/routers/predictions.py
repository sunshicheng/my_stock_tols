"""预测与复盘路由 — 今日预测、历史列表、某日详情、预测/复盘报告正文、触发预测/复盘任务（异步+轮询）。"""

import threading
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from storage import db as storage_db

router = APIRouter()

# 预测任务状态：idle | running | success | error
_predict_state = {"status": "idle", "trade_date": None, "error": None}
_predict_lock = threading.Lock()

# 复盘任务状态
_review_state = {"status": "idle", "trade_date": None, "error": None}
_review_lock = threading.Lock()


def _run_predict_background():
    from core.predict_runner import run_predict
    global _predict_state
    try:
        result = run_predict(return_data=False)
        with _predict_lock:
            if result.get("ok"):
                _predict_state["status"] = "success"
                _predict_state["trade_date"] = result.get("trade_date")
                _predict_state["error"] = None
            else:
                _predict_state["status"] = "error"
                _predict_state["error"] = result.get("error", "预测任务执行失败")
                _predict_state["trade_date"] = None
    except Exception as e:
        with _predict_lock:
            _predict_state["status"] = "error"
            _predict_state["error"] = str(e)
            _predict_state["trade_date"] = None


def _run_review_background(trade_date: str):
    from core.reviewer import run_review
    from core.report_generator import generate_review_report
    global _review_state
    try:
        review_data = run_review(trade_date)
        if review_data.get("error"):
            with _review_lock:
                _review_state["status"] = "error"
                _review_state["error"] = review_data["error"]
                _review_state["trade_date"] = trade_date
            return
        generate_review_report(review_data)
        with _review_lock:
            _review_state["status"] = "success"
            _review_state["error"] = None
    except Exception as e:
        with _review_lock:
            _review_state["status"] = "error"
            _review_state["error"] = str(e)
            _review_state["trade_date"] = trade_date


@router.post("/run")
def run_predict_task():
    """提交当日预测任务，后台异步执行。请前端轮询 GET /run/status 获取结果。"""
    with _predict_lock:
        if _predict_state["status"] == "running":
            return {"status": "running", "message": "预测任务进行中"}
        _predict_state["status"] = "running"
        _predict_state["error"] = None
        thread = threading.Thread(target=_run_predict_background, daemon=True)
        thread.start()
    return {"status": "running", "message": "预测任务已启动"}


@router.get("/run/status")
def get_predict_status():
    """轮询预测任务状态。status: idle | running | success | error。"""
    with _predict_lock:
        s = dict(_predict_state)
    return {"status": s["status"], "trade_date": s.get("trade_date"), "error": s.get("error")}


@router.post("/review/run")
def run_review_task(trade_date: str = Query(None, description="交易日 YYYY-MM-DD，默认当日")):
    """提交复盘任务，后台异步执行。请前端轮询 GET /review/status 获取结果。"""
    if not trade_date:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    with _review_lock:
        if _review_state["status"] == "running":
            return {"status": "running", "message": "复盘任务进行中", "trade_date": trade_date}
        _review_state["status"] = "running"
        _review_state["trade_date"] = trade_date
        _review_state["error"] = None
        thread = threading.Thread(target=_run_review_background, args=(trade_date,), daemon=True)
        thread.start()
    return {"status": "running", "message": "复盘任务已启动", "trade_date": trade_date}


@router.get("/review/status")
def get_review_status():
    """轮询复盘任务状态。"""
    with _review_lock:
        s = dict(_review_state)
    return {"status": s["status"], "trade_date": s.get("trade_date"), "error": s.get("error")}


@router.get("/today")
def get_today():
    """今日推荐（与首页每日预测对应）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    recs = storage_db.get_recommendations(today)
    summary = None
    rows = storage_db.get_daily_summaries_range(today, today)
    if rows:
        summary = rows[0]
    report = storage_db.get_daily_report(today)
    return {
        "trade_date": today,
        "recommendations": recs,
        "summary": summary,
        "report_content": report.get("prediction_report"),
    }


@router.get("/report")
def get_report(trade_date: str = Query(..., description="交易日 YYYY-MM-DD")):
    """获取某日的预测报告 Markdown 正文（从数据库）。"""
    report = storage_db.get_daily_report(trade_date)
    return {"content": report.get("prediction_report")}


@router.get("/report/review")
def get_review_report(trade_date: str = Query(..., description="交易日 YYYY-MM-DD")):
    """获取某日的复盘报告 Markdown 正文（从数据库）。"""
    report = storage_db.get_daily_report(trade_date)
    return {"content": report.get("review_report")}


@router.get("/history")
def get_history(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """历史预测列表：按日期展示，支持时间筛选。"""
    items = storage_db.get_daily_summaries_range(start_date, end_date)
    return {"items": items}


@router.get("/detail")
def get_detail(trade_date: str = Query(..., description="交易日 YYYY-MM-DD")):
    """某日的预测与复盘详情（含报告正文）。"""
    recs = storage_db.get_recommendations(trade_date)
    reviews = storage_db.get_reviews(trade_date)
    summary = None
    rows = storage_db.get_daily_summaries_range(trade_date, trade_date)
    if rows:
        summary = rows[0]
    report = storage_db.get_daily_report(trade_date)
    return {
        "trade_date": trade_date,
        "recommendations": recs,
        "reviews": reviews,
        "summary": summary,
        "prediction_report": report.get("prediction_report"),
        "review_report": report.get("review_report"),
    }
