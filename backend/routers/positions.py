"""持仓路由 — 与现有 storage.db 一致，需登录。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from backend.database import get_session
from storage import db as storage_db

router = APIRouter()


class PositionAdd(BaseModel):
    code: str
    buy_date: str
    buy_price: float
    quantity: float
    name: str = ""
    category: str = "stock"
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    plan_sell_date: Optional[str] = None
    note: Optional[str] = None


class PositionPlan(BaseModel):
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    plan_sell_date: Optional[str] = None
    note: Optional[str] = None


@router.get("")
def list_positions():
    items = storage_db.list_positions()
    return {"items": items}


@router.post("")
def add_position(body: PositionAdd):
    if not body.code or not body.buy_date or body.buy_price <= 0 or body.quantity <= 0:
        raise HTTPException(status_code=400, detail="code/buy_date/buy_price/quantity 必填且有效")
    cat = (body.category or "stock").lower()
    if cat not in ("stock", "fund"):
        cat = "stock"
    pid = storage_db.add_position(
        code=body.code.strip(),
        name=body.name or body.code,
        category=cat,
        buy_date=body.buy_date,
        buy_price=body.buy_price,
        quantity=body.quantity,
        target_price=body.target_price,
        stop_loss=body.stop_loss,
        plan_sell_date=body.plan_sell_date,
        note=body.note,
    )
    return {"id": pid, "message": "已添加持仓"}


@router.put("/{position_id}")
def update_plan(position_id: int, body: PositionPlan):
    ok = storage_db.update_position(
        position_id,
        target_price=body.target_price,
        stop_loss=body.stop_loss,
        plan_sell_date=body.plan_sell_date,
        note=body.note,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="未找到该持仓")
    return {"message": "已更新卖出计划"}


@router.delete("/{position_id}")
def delete_position(position_id: int):
    ok = storage_db.delete_position(position_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到该持仓")
    return {"message": "已删除"}
