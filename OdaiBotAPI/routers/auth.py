from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials

from ..deps import (
    db,
    get_current_user,
    get_optional_current_user,
    has_guild_users,
    hash_password,
    make_token,
    require_admin,
    verify_password,
    security,
)
from ..schemas import (
    InviteCreateRequest,
    InviteRegisterRequest,
    InviteResponse,
    LoginRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/guilds/{guild_id}/auth", tags=["auth"])

_MIN_PASSWORD_LEN = 8


def _validate_password(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LEN:
        raise HTTPException(status_code=400, detail=f"パスワードは {_MIN_PASSWORD_LEN} 文字以上で設定してください")


@router.post("/login", response_model=TokenResponse)
def login(guild_id: int, payload: LoginRequest):
    user = db.query_one(
        "SELECT id, username, password_hash, role FROM users WHERE guild_id = %s AND username = %s",
        (guild_id, payload.username),
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="ユーザ名またはパスワードが正しくありません")

    token = make_token()
    db.execute(
        "UPDATE users SET api_token = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (token, user["id"]),
        commit=True,
    )
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.post("/register", response_model=TokenResponse)
def register_with_invite(guild_id: int, payload: InviteRegisterRequest):
    _validate_password(payload.password)

    invite = db.query_one(
        "SELECT * FROM user_invites WHERE guild_id = %s AND invite_token = %s AND used = 0 AND expires_at > NOW()",
        (guild_id, payload.invite_token),
    )
    if not invite:
        raise HTTPException(status_code=404, detail="招待トークンが無効または期限切れです")

    if db.query_one("SELECT id FROM users WHERE guild_id = %s AND username = %s", (guild_id, invite["username"])):
        raise HTTPException(status_code=409, detail="このユーザー名は既に登録されています")

    password_hash = hash_password(payload.password)
    token = make_token()
    db.execute(
        "INSERT INTO users (guild_id, username, password_hash, role, api_token) VALUES (%s, %s, %s, %s, %s)",
        (guild_id, invite["username"], password_hash, invite["role"], token),
        commit=True,
    )
    db.execute(
        "UPDATE user_invites SET used = 1, used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (invite["id"],),
        commit=True,
    )
    return {"access_token": token, "token_type": "bearer", "role": invite["role"]}


@router.post("/invite", response_model=InviteResponse)
def create_invite(guild_id: int, payload: InviteCreateRequest, _user: dict = Depends(require_admin)):
    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role は admin または user を指定してください")

    if db.query_one("SELECT id FROM users WHERE guild_id = %s AND username = %s", (guild_id, payload.username)):
        raise HTTPException(status_code=409, detail="同名ユーザが既に存在します")

    expire_hours = int(os.getenv("INVITE_EXPIRE_HOURS", "24"))
    invite_token = make_token()
    expires_at = (datetime.now() + timedelta(hours=expire_hours)).strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "INSERT INTO user_invites (guild_id, username, role, invite_token, expires_at) VALUES (%s, %s, %s, %s, %s)",
        (guild_id, payload.username, payload.role, invite_token, expires_at),
        commit=True,
    )
    return {"invite_token": invite_token, "expires_at": expires_at}


@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(require_admin)])
def list_users(guild_id: int):
    return db.query("SELECT id, username, role, created_at, updated_at FROM users WHERE guild_id = %s", (guild_id,))


@router.post("/users", response_model=UserResponse)
def create_user(
    guild_id: int,
    payload: UserCreateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if has_guild_users(guild_id):
        current_user = get_optional_current_user(guild_id, credentials)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="管理者権限が必要です")

    _validate_password(payload.password)

    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role は admin または user を指定してください")

    if db.query_one("SELECT id FROM users WHERE guild_id = %s AND username = %s", (guild_id, payload.username)):
        raise HTTPException(status_code=409, detail="同名ユーザが既に存在します")

    password_hash = hash_password(payload.password)
    token = make_token()
    cursor = db.execute(
        "INSERT INTO users (guild_id, username, password_hash, role, api_token) VALUES (%s, %s, %s, %s, %s)",
        (guild_id, payload.username, password_hash, payload.role, token),
        commit=True,
    )
    return db.query_one("SELECT id, username, role, created_at, updated_at FROM users WHERE id = %s", (cursor.lastrowid,))


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(guild_id: int, user_id: int, payload: UserUpdateRequest, _user: dict = Depends(require_admin)):
    if not db.query_one("SELECT id FROM users WHERE guild_id = %s AND id = %s", (guild_id, user_id)):
        raise HTTPException(status_code=404, detail="ユーザが見つかりません")

    updates: list[tuple[str, Any]] = []
    params: list[Any] = []
    if payload.password:
        _validate_password(payload.password)
        updates.append(("password_hash", hash_password(payload.password)))
        params.append(updates[-1][1])
    if payload.role:
        if payload.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="role は admin または user を指定してください")
        updates.append(("role", payload.role))
        params.append(updates[-1][1])
    if not updates:
        raise HTTPException(status_code=400, detail="更新する項目がありません")

    sql = "UPDATE users SET " + ", ".join(f"{col} = %s" for col, _ in updates) + ", updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    params.append(user_id)
    db.execute(sql, tuple(params), commit=True)
    return db.query_one("SELECT id, username, role, created_at, updated_at FROM users WHERE id = %s", (user_id,))


@router.delete("/users/{user_id}", status_code=204)
def delete_user(guild_id: int, user_id: int, current_user: dict = Depends(require_admin)):
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="自分自身は削除できません")

    if not db.query_one("SELECT id FROM users WHERE guild_id = %s AND id = %s", (guild_id, user_id)):
        raise HTTPException(status_code=404, detail="ユーザが見つかりません")

    db.execute("DELETE FROM users WHERE guild_id = %s AND id = %s", (guild_id, user_id), commit=True)
    return Response(status_code=204)
