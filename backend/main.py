"""FastAPI 应用入口 — 注册路由、CORS、初始化表。"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_web_tables
from backend.deps import get_current_user
from backend.routers import auth, positions, predictions, backtest, config

# 初始化 Web 表（users）
init_web_tables()

app = FastAPI(title="股票推荐 Web", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # 与 allow_origins=["*"] 不可同用；本接口用 JWT 头认证，无需 credentials
    allow_methods=["*"],
    allow_headers=["*"],
)

# 无需登录
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# 需登录
app.include_router(positions.router, prefix="/api/positions", tags=["positions"], dependencies=[Depends(get_current_user)])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"], dependencies=[Depends(get_current_user)])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"], dependencies=[Depends(get_current_user)])
app.include_router(config.router, prefix="/api/config", tags=["config"], dependencies=[Depends(get_current_user)])


@app.get("/health")
def health():
    return {"status": "ok"}
