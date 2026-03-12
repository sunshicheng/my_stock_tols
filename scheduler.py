"""定时调度模块 — 每日自动执行预测与复盘。"""

import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.settings import PREDICT_TIME, REVIEW_TIME

# A 股交易日简易判断（不含节假日，节假日可后续对接接口）
_TRADE_WEEKDAYS = {0, 1, 2, 3, 4}  # 周一到周五


def _is_trade_day() -> bool:
    return datetime.now().weekday() in _TRADE_WEEKDAYS


def _job_predict():
    if not _is_trade_day():
        logger.info("非交易日，跳过预测")
        return
    logger.info("定时任务触发: 每日预测")
    try:
        from main import cmd_predict
        cmd_predict()
    except Exception as e:
        logger.exception(f"预测任务异常: {e}")


def _job_review():
    if not _is_trade_day():
        logger.info("非交易日，跳过复盘")
        return
    logger.info("定时任务触发: 每日复盘")
    try:
        from main import cmd_review
        cmd_review()
    except Exception as e:
        logger.exception(f"复盘任务异常: {e}")


def start_scheduler():
    """启动阻塞式调度器。"""
    predict_h, predict_m = PREDICT_TIME.split(":")
    review_h, review_m = REVIEW_TIME.split(":")

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(
        _job_predict,
        CronTrigger(hour=int(predict_h), minute=int(predict_m), day_of_week="mon-fri"),
        id="daily_predict",
        name="每日预测推荐",
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _job_review,
        CronTrigger(hour=int(review_h), minute=int(review_m), day_of_week="mon-fri"),
        id="daily_review",
        name="每日复盘",
        misfire_grace_time=3600,
    )

    def _shutdown(signum, frame):
        logger.info("收到退出信号，正在关闭调度器...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(f"调度器已启动:")
    logger.info(f"  📈 每日预测: {PREDICT_TIME} (周一至周五)")
    logger.info(f"  📋 每日复盘: {REVIEW_TIME} (周一至周五)")
    logger.info(f"按 Ctrl+C 停止")

    scheduler.start()
