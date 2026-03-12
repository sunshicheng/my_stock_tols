"""SQLModel 引擎与会话 — 与现有 data/recommendations.db 共用。"""

import sys
from pathlib import Path

# 保证从项目根目录运行时能导入 config
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, SQLModel, create_engine

from config.settings import DB_PATH
from backend.models import User  # noqa: F401 - 注册表

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_web_tables():
    """仅创建 Web 新增的表（如 users）。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
