"""个人持仓与卖出计划 — 记录持仓、目标价/止损/计划卖出日，并与当日推荐对照。"""

from datetime import datetime

from loguru import logger

from storage.db import list_positions, add_position, update_position, delete_position


def get_positions_with_plan() -> list[dict]:
    """获取当前持仓列表（含卖出计划字段）。"""
    return list_positions()


def add_holding(
    code: str,
    buy_date: str,
    buy_price: float,
    quantity: float,
    name: str = "",
    category: str = "stock",
    target_price: float = None,
    stop_loss: float = None,
    plan_sell_date: str = None,
    note: str = None,
) -> int:
    """添加一条持仓。"""
    pid = add_position(
        code=code.strip(),
        name=name or code,
        category=category,
        buy_date=buy_date,
        buy_price=buy_price,
        quantity=quantity,
        target_price=target_price,
        stop_loss=stop_loss,
        plan_sell_date=plan_sell_date,
        note=note,
    )
    logger.info(f"已添加持仓: {name or code}({code}) {buy_date} @{buy_price} x{quantity}")
    return pid


def set_sell_plan(position_id: int, target_price: float = None, stop_loss: float = None, plan_sell_date: str = None, note: str = None) -> bool:
    """设置/更新卖出计划。"""
    ok = update_position(position_id, target_price=target_price, stop_loss=stop_loss, plan_sell_date=plan_sell_date, note=note)
    if ok:
        logger.info(f"已更新持仓 id={position_id} 卖出计划")
    return ok


def remove_holding(position_id: int) -> bool:
    """删除一条持仓记录。"""
    ok = delete_position(position_id)
    if ok:
        logger.info(f"已删除持仓 id={position_id}")
    return ok


def format_positions_table(positions: list[dict], today_price_map: dict = None) -> list[str]:
    """格式化为可打印的表格行。today_price_map: {code: current_price} 可选，用于显示浮动盈亏。"""
    lines = []
    if not positions:
        return ["  暂无持仓"]
    for p in positions:
        code = p.get("code", "")
        name = p.get("name", "") or code
        buy_date = p.get("buy_date", "")
        buy_price = p.get("buy_price", 0)
        qty = p.get("quantity", 0)
        target = p.get("target_price")
        stop = p.get("stop_loss")
        plan_date = p.get("plan_sell_date")
        cur = (today_price_map or {}).get(code)
        if cur is not None and buy_price and float(buy_price) != 0:
            pct = (float(cur) - float(buy_price)) / float(buy_price) * 100
            cur_str = f"现价 {cur:.2f} ({pct:+.2f}%)"
        else:
            cur_str = ""
        line = f"  [{p.get('id')}] {name}({code})  {buy_date} 买入{buy_price:.2f} x{qty}"
        if target is not None:
            line += f"  目标{target:.2f}"
        if stop is not None:
            line += f"  止损{stop:.2f}"
        if plan_date:
            line += f"  计划卖出日{plan_date}"
        if cur_str:
            line += f"  {cur_str}"
        lines.append(line)
    return lines
