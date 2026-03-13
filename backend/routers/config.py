"""配置路由 — 仅 AI Key/BaseURL/Model，开源版无登录。"""

import os
import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

# 从项目根加载 .env 路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

# 兼容旧 .env：优先读 AI_*，没有则读 DEEPSEEK_*
ENV_KEYS = ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL")
LEGACY_KEYS = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")

router = APIRouter()


class ConfigResponse(BaseModel):
    ai_api_key_masked: str
    ai_base_url: str
    ai_model: str


class UpdateConfigBody(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


def _read_env_key(key: str) -> str | None:
    """从 .env 读取键值。键不存在返回 None；存在则返回值（可能为空字符串）。"""
    if not ENV_PATH.exists():
        return None
    text = ENV_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if "=" in line and line.split("=", 1)[0].strip() == key:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


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


def _get_ai_key() -> str:
    raw = _read_env_key("AI_API_KEY")
    if raw is not None:
        return raw
    raw = os.getenv("AI_API_KEY")
    if raw is not None:
        return raw
    return _read_env_key("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")


def _get_ai_base_url() -> str:
    raw = _read_env_key("AI_BASE_URL")
    if raw is not None:
        return raw
    raw = os.getenv("AI_BASE_URL")
    if raw is not None:
        return raw
    return _read_env_key("DEEPSEEK_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def _get_ai_model() -> str:
    raw = _read_env_key("AI_MODEL")
    if raw is not None:
        return raw
    raw = os.getenv("AI_MODEL")
    if raw is not None:
        return raw
    return _read_env_key("DEEPSEEK_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


@router.get("", response_model=ConfigResponse)
def get_config():
    """获取 AI 配置（Key 脱敏）。"""
    raw = _get_ai_key()
    if len(raw) <= 4:
        masked = "***" if raw else ""
    else:
        masked = "***" + raw[-4:]
    return ConfigResponse(
        ai_api_key_masked=masked,
        ai_base_url=_get_ai_base_url(),
        ai_model=_get_ai_model(),
    )


@router.put("")
def update_config(body: UpdateConfigBody):
    """更新 AI 配置（API Key / Base URL / Model），写入 .env。"""
    if body.api_key is not None:
        _write_env_key("AI_API_KEY", body.api_key.strip())
    if body.base_url is not None:
        _write_env_key("AI_BASE_URL", body.base_url.strip())
    if body.model is not None:
        _write_env_key("AI_MODEL", body.model.strip())
    return {"message": "已保存，重启后端或 CLI 后生效"}
