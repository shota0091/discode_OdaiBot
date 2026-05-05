from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..deps import db, security, verify_password, make_token
from ..schemas import LoginRequest, GlobalLoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth-global"])


@router.post("/login", response_model=GlobalLoginResponse)
def global_login(payload: LoginRequest):
    try:
        login_id = int(payload.username)
    except ValueError:
        login_id = -1
    user = db.query_one(
        "SELECT id, username, display_name, password_hash FROM users WHERE username = %s OR id = %s OR display_name = %s",
        (payload.username, login_id, payload.username),
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="ユーザ名またはパスワードが正しくありません")

    token = make_token()
    db.execute(
        "UPDATE users SET api_token = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (token, user["id"]),
        commit=True,
    )

    guilds_data = db.query(
        "SELECT ug.guild_id, ug.role, gs.guild_name "
        "FROM user_guilds ug LEFT JOIN guild_settings gs ON ug.guild_id = gs.guild_id "
        "WHERE ug.user_id = %s",
        (user["id"],),
    )

    guilds = [
        {
            "guild_id": str(g["guild_id"]),
            "guild_name": g.get("guild_name"),
            "role": g["role"],
        }
        for g in guilds_data
    ]

    if not guilds:
        raise HTTPException(status_code=403, detail="所属するサーバーが見つかりません")

    display_name = user.get("display_name") or user["username"]
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": guilds[0]["role"],
        "display_name": display_name,
        "guilds": guilds,
    }


@router.get("/guilds")
def list_guilds(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="認証トークンが必要です")

    token = credentials.credentials
    rows = db.query(
        "SELECT ug.guild_id, ug.role, gs.guild_name "
        "FROM users u "
        "JOIN user_guilds ug ON u.id = ug.user_id "
        "LEFT JOIN guild_settings gs ON ug.guild_id = gs.guild_id "
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
