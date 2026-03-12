"""认证路由 — 注册、登录。"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from backend.auth import (
    create_access_token,
    get_user_by_phone,
    hash_password,
    verify_password,
    verify_phone,
)
from backend.database import get_session
from backend.models import User

router = APIRouter()


class RegisterBody(BaseModel):
    phone: str
    password: str


class LoginBody(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    phone: str


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterBody, session: Session = Depends(get_session)):
    if not verify_phone(body.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if get_user_by_phone(session, body.phone):
        raise HTTPException(status_code=400, detail="该手机号已注册")
    user = User(
        phone=body.phone.strip(),
        password_hash=hash_password(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, phone=user.phone)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, session: Session = Depends(get_session)):
    user = get_user_by_phone(session, body.phone)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, phone=user.phone)
