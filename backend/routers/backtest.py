"""回测路由 — 按区间执行回测并返回结果。"""

from fastapi import APIRouter
from pydantic import BaseModel

from core.backtest_runner import run_recommendation_backtest

router = APIRouter()


class BacktestBody(BaseModel):
    start_date: str
    end_date: str
    cash: float = 100000.0
    max_symbols: int = 20


@router.post("/run")
def run_backtest(body: BacktestBody):
    """执行回测，返回汇总与各标的结果。"""
    result = run_recommendation_backtest(
        start_date=body.start_date,
        end_date=body.end_date,
        initial_cash=body.cash,
        category="stock",
        max_symbols=body.max_symbols,
    )
    return result
