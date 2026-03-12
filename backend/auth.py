"""认证 — 密码哈希与 JWT。"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlmodel import Session, select

from backend.models import User

SECRET_KEY = os.getenv("WEB_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def verify_phone(phone: str) -> bool:
    """简单校验大陆手机号。"""
    return bool(phone and PHONE_RE.match(str(phone).strip()))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_user_by_phone(session: Session, phone: str) -> Optional[User]:
    stmt = select(User).where(User.phone == phone.strip())
    return session.exec(stmt).first()
