"""预测与复盘路由 — 今日预测、历史列表、某日详情、预测/复盘报告正文、触发预测任务。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from storage import db as storage_db

router = APIRouter()


@router.post("/run")
def run_predict_task():
    """触发当日预测任务（与 CLI python main.py predict 相同）。耗时可长达数分钟，请前端设置较长超时。"""
    from core.predict_runner import run_predict

    result = run_predict(return_data=False)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "预测任务执行失败"))
    return {"message": "预测完成", "trade_date": result.get("trade_date"), "report_path": result.get("report_path")}


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
