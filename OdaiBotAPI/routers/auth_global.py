from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..deps import db, security, verify_password, make_token
from ..schemas import LoginRequest, GlobalLoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth-global"])


@router.post("/login", response_model=GlobalLoginResponse)
def global_login(payload: LoginRequest):
    """guild_id なしでログイン。同名ユーザが複数 guild に存在する場合は全て返す。"""
    users = db.query(
        "SELECT id, guild_id, username, password_hash, role FROM users WHERE username = %s",
        (payload.username,),
    )
    matched = [u for u in users if verify_password(payload.password, u["password_hash"])]

    if not matched:
        raise HTTPException(status_code=401, detail="ユーザ名またはパスワードが正しくありません")

    token = make_token()
    for user in matched:
        db.execute(
            "UPDATE users SET api_token = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (token, user["id"]),
            commit=True,
        )

    guilds = []
    for user in matched:
        gs = db.query_one(
            "SELECT guild_name FROM guild_settings WHERE guild_id = %s",
            (user["guild_id"],),
        )
        guilds.append(
            {
                "guild_id": str(user["guild_id"]),
                "guild_name": gs["guild_name"] if gs and gs.get("guild_name") else None,
                "role": user["role"],
            }
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": matched[0]["role"],
        "guilds": guilds,
    }


@router.get("/guilds")
def list_guilds(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """現在のトークンで認証済みのユーザが所属する guild 一覧を返す。"""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="認証トークンが必要です")

    token = credentials.credentials
    rows = db.query(
        "SELECT u.guild_id, u.role, gs.guild_name "
        "FROM users u LEFT JOIN guild_settings gs ON u.guild_id = gs.guild_id "
        "WHERE u.api_token = %s",
        (token,),
    )

    if not rows:
        raise HTTPException(status_code=401, detail="無効なトークンです")

    return {
        "data": [
            {
                "guild_id": str(r["guild_id"]),
                "guild_name": r.get("guild_name"),
                "role": r["role"],
            }
            for r in rows
        ]
    }
