"""FastAPI 应用入口 — 注册路由、CORS、初始化表。开源版无登录，AI Key 在设置中配置。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_web_tables
from backend.routers import positions, predictions, backtest, config

# 初始化 Web 表（positions 等仍用 SQLite）
init_web_tables()

app = FastAPI(title="股票推荐 Web", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


@app.get("/health")
def health():
    return {"status": "ok"}
