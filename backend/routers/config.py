"""配置路由 — 修改 AI Key、修改密码。"""

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_current_user
from backend.auth import hash_password, verify_password
from backend.models import User

# 从项目根加载 .env 路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

router = APIRouter()


class ConfigResponse(BaseModel):
    deepseek_api_key_masked: str  # 脱敏显示


class UpdateApiKeyBody(BaseModel):
    api_key: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


def _read_env_key(key: str) -> str:
    if not ENV_PATH.exists():
        return ""
    text = ENV_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if "=" in line and line.split("=", 1)[0].strip() == key:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _write_env_key(key: str, value: str):
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ENV_PATH.exists():
        text = ENV_PATH.read_text(encoding="utf-8")
        pattern = re.compile(rf"^{re.escape(key)}\s*=\s*.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f"{key}={value}", text)
        else:
            text = text.rstrip() + f"\n{key}={value}\n"
    else:
        text = f"{key}={value}\n"
    ENV_PATH.write_text(text, encoding="utf-8")


@router.get("", response_model=ConfigResponse)
def get_config(_: User = Depends(get_current_user)):
    """获取配置（AI Key 脱敏）。"""
    raw = _read_env_key("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    if len(raw) <= 4:
        masked = "***" if raw else ""
    else:
        masked = "***" + raw[-4:]
    return ConfigResponse(deepseek_api_key_masked=masked)


@router.put("/api-key")
def update_api_key(body: UpdateApiKeyBody, _: User = Depends(get_current_user)):
    """更新 DeepSeek API Key（写入 .env）。"""
    _write_env_key("DEEPSEEK_API_KEY", body.api_key.strip())
    return {"message": "已更新 API Key，CLI 下次运行或重启后端后生效"}


@router.post("/change-password")
def change_password(body: ChangePasswordBody, user: User = Depends(get_current_user)):
    """修改当前用户密码。"""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    from backend.database import engine
    from sqlmodel import Session
    with Session(engine) as session:
        u = session.get(User, user.id)
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在或已被删除")
        u.password_hash = hash_password(body.new_password)
        session.add(u)
        session.commit()
    return {"message": "密码已修改"}
