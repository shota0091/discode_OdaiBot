from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, List, Optional

_LOCKOUT_STEPS = [
    (20, None),      # 20回以上 → 永久ロック
    (15, 60),        # 15回以上 → 60分
    (10, 10),        # 10回以上 → 10分
    (5,  1),         # 5回以上  → 1分
]

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from ..limiter import limiter
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
    ResetPasswordRequest,
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
@limiter.limit("10/minute")
def login(request: Request, guild_id: int, payload: LoginRequest):
    try:
        login_id = int(payload.username)
    except ValueError:
        login_id = -1
    user = db.query_one(
        "SELECT u.id, u.username, u.display_name, u.password_hash, u.login_attempts, u.locked_until, u.login_locked, ug.role "
        "FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
        "WHERE ug.guild_id = %s AND (u.username = %s OR u.id = %s OR u.display_name = %s)",
        (guild_id, payload.username, login_id, payload.username),
    )

    if not user:
        raise HTTPException(status_code=401, detail="ユーザ名またはパスワードが正しくありません")

    # BANチェック
    if db.query_one("SELECT 1 FROM guild_bans WHERE guild_id = %s AND username = %s", (guild_id, user["username"])):
        raise HTTPException(status_code=403, detail="このサーバーからBANされています")

    # 永久ロック
    if user["login_locked"]:
        raise HTTPException(status_code=403, detail="アカウントがロックされています。管理者にお問い合わせください")

    # 一時ロック
    if user["locked_until"] and user["locked_until"] > datetime.now():
        remaining = int((user["locked_until"] - datetime.now()).total_seconds() / 60) + 1
        raise HTTPException(status_code=403, detail=f"アカウントが一時的にロックされています。約{remaining}分後に再試行してください")

    if not verify_password(payload.password, user["password_hash"]):
        attempts = (user["login_attempts"] or 0) + 1
        locked_until = None
        login_locked = 0
        for threshold, minutes in _LOCKOUT_STEPS:
            if attempts >= threshold:
                if minutes is None:
                    login_locked = 1
                else:
                    locked_until = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
                break
        db.execute(
            "UPDATE users SET login_attempts = %s, locked_until = %s, login_locked = %s WHERE id = %s",
            (attempts, locked_until, login_locked, user["id"]), commit=True,
        )
        if login_locked:
            raise HTTPException(status_code=403, detail="ログイン試行回数の上限に達しました。管理者にお問い合わせください")
        if locked_until:
            for threshold, minutes in _LOCKOUT_STEPS:
                if attempts >= threshold and minutes:
                    raise HTTPException(status_code=403, detail=f"ログイン試行回数が上限を超えました。{minutes}分後に再試行してください")
        raise HTTPException(status_code=401, detail=f"ユーザ名またはパスワードが正しくありません（{attempts}回失敗）")

    # ログイン成功 → 試行回数リセット
    token = make_token()
    db.execute(
        "UPDATE users SET api_token = %s, login_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (token, user["id"]), commit=True,
    )
    display_name = user.get("display_name") or user["username"]
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "display_name": display_name, "user_id": user["id"]}


@router.post("/register", response_model=TokenResponse)
def register_with_invite(guild_id: int, payload: InviteRegisterRequest):
    invite = db.query_one(
        "SELECT * FROM user_invites WHERE guild_id = %s AND invite_token = %s AND used = 0 AND expires_at > NOW()",
        (guild_id, payload.invite_token),
    )
    if not invite:
        raise HTTPException(status_code=404, detail="招待トークンが無効または期限切れです")

    username = invite["username"]
    role = invite["role"]
    display_name = (payload.display_name or "").strip() or username

    # BANチェック
    if db.query_one("SELECT 1 FROM guild_bans WHERE guild_id = %s AND username = %s", (guild_id, username)):
        raise HTTPException(status_code=403, detail="このサーバーからBANされています")

    # すでにこの guild に登録済みかチェック
    if db.query_one(
        "SELECT 1 FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
        "WHERE ug.guild_id = %s AND u.username = %s",
        (guild_id, username),
    ):
        raise HTTPException(status_code=409, detail="このユーザー名は既に登録されています")

    # グローバルユーザーが既に存在するか確認（他サーバーに登録済み）
    existing_user = db.query_one("SELECT id, api_token FROM users WHERE username = %s", (username,))

    if existing_user:
        # パスワード入力があれば更新、なければ既存パスワードを引き継ぐ
        user_id = existing_user["id"]
        if payload.password:
            _validate_password(payload.password)
            db.execute(
                "UPDATE users SET password_hash = %s, display_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (hash_password(payload.password), display_name, user_id), commit=True,
            )
        else:
            db.execute(
                "UPDATE users SET display_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (display_name, user_id), commit=True,
            )
    else:
        # 新規ユーザー → パスワード必須
        if not payload.password:
            raise HTTPException(status_code=400, detail="password_required")
        _validate_password(payload.password)
        cursor = db.execute(
            "INSERT INTO users (username, display_name, password_hash, api_token) VALUES (%s, %s, %s, %s)",
            (username, display_name, hash_password(payload.password), make_token()), commit=True,
        )
        user_id = cursor.lastrowid

    # このサーバーに紐付け
    db.execute(
        "INSERT INTO user_guilds (user_id, guild_id, role) VALUES (%s, %s, %s)",
        (user_id, guild_id, role), commit=True,
    )

    # 招待を使用済みにする
    db.execute(
        "UPDATE user_invites SET used = 1, used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (invite["id"],), commit=True,
    )

    # トークンを返す（なければ新規発行）
    user = db.query_one("SELECT api_token FROM users WHERE id = %s", (user_id,))
    access_token = user["api_token"]
    if not access_token:
        access_token = make_token()
        db.execute("UPDATE users SET api_token = %s WHERE id = %s", (access_token, user_id), commit=True)

    return {"access_token": access_token, "token_type": "bearer", "role": role, "display_name": display_name, "user_id": user_id}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, guild_id: int, payload: ResetPasswordRequest):
    invite = db.query_one(
        "SELECT * FROM user_invites WHERE guild_id = %s AND invite_token = %s AND used = 0 AND expires_at > NOW()",
        (guild_id, payload.invite_token),
    )
    if not invite:
        raise HTTPException(status_code=404, detail="リセットトークンが無効または期限切れです")

    _validate_password(payload.password)

    user = db.query_one(
        "SELECT u.id FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
        "WHERE ug.guild_id = %s AND u.username = %s",
        (guild_id, invite["username"]),
    )
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    db.execute(
        "UPDATE users SET password_hash = %s, login_attempts = 0, locked_until = NULL, login_locked = 0, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (hash_password(payload.password), user["id"]), commit=True,
    )
    db.execute(
        "UPDATE user_invites SET used = 1, used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (invite["id"],), commit=True,
    )
    return {"message": "パスワードを更新しました"}


@router.get("/invite-info")
def get_invite_info(guild_id: int, token: str):
    invite = db.query_one(
        "SELECT username FROM user_invites WHERE guild_id = %s AND invite_token = %s AND used = 0 AND expires_at > NOW()",
        (guild_id, token),
    )
    if not invite:
        raise HTTPException(status_code=404, detail="招待トークンが無効または期限切れです")
    return {"username": invite["username"]}


@router.get("/bans")
def list_bans(guild_id: int, _admin: dict = Depends(require_admin)):
    bans = db.query(
        "SELECT id, username, banned_at FROM guild_bans WHERE guild_id = %s ORDER BY banned_at DESC",
        (guild_id,),
    )
    return {"data": list(bans)}


@router.delete("/bans/{ban_id}", status_code=204)
def remove_ban(guild_id: int, ban_id: int, _admin: dict = Depends(require_admin)):
    if not db.query_one("SELECT 1 FROM guild_bans WHERE id = %s AND guild_id = %s", (ban_id, guild_id)):
        raise HTTPException(status_code=404, detail="BANが見つかりません")
    db.execute("DELETE FROM guild_bans WHERE id = %s", (ban_id,), commit=True)
    return Response(status_code=204)


@router.get("/invites")
def list_invites(guild_id: int, _admin: dict = Depends(require_admin)):
    invites = db.query(
        "SELECT id, username, role, invite_token, expires_at, created_at FROM user_invites "
        "WHERE guild_id = %s AND used = 0 AND expires_at > NOW() ORDER BY created_at DESC",
        (guild_id,),
    )
    return {"data": list(invites)}


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_invite(guild_id: int, invite_id: int, _admin: dict = Depends(require_admin)):
    if not db.query_one(
        "SELECT 1 FROM user_invites WHERE id = %s AND guild_id = %s AND used = 0",
        (invite_id, guild_id),
    ):
        raise HTTPException(status_code=404, detail="招待が見つかりません")
    db.execute("DELETE FROM user_invites WHERE id = %s", (invite_id,), commit=True)
    return Response(status_code=204)


@router.post("/invite", response_model=InviteResponse)
def create_invite(guild_id: int, payload: InviteCreateRequest, _user: dict = Depends(require_admin)):
    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role は admin または user を指定してください")

    if db.query_one(
        "SELECT 1 FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
        "WHERE ug.guild_id = %s AND u.username = %s",
        (guild_id, payload.username),
    ):
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


_USER_SELECT = (
    "SELECT u.id, u.username, u.display_name, ug.role, "
    "u.login_attempts, u.locked_until, u.login_locked, u.created_at, u.updated_at, "
    "CASE WHEN gb.guild_id IS NOT NULL THEN 1 ELSE 0 END AS is_banned "
    "FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
    "LEFT JOIN guild_bans gb ON gb.guild_id = ug.guild_id AND gb.username = u.username"
)


@router.get("/users", response_model=List[UserResponse])
def list_users(guild_id: int, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") == "admin":
        return db.query(f"{_USER_SELECT} WHERE ug.guild_id = %s", (guild_id,))
    return db.query(f"{_USER_SELECT} WHERE ug.guild_id = %s AND u.id = %s", (guild_id, current_user["id"]))


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

    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role は admin または user を指定してください")

    existing = db.query_one("SELECT id FROM users WHERE username = %s", (payload.username,))

    if existing:
        user_id = existing["id"]
        if db.query_one("SELECT 1 FROM user_guilds WHERE user_id = %s AND guild_id = %s", (user_id, guild_id)):
            raise HTTPException(status_code=409, detail="同名ユーザが既に存在します")
    else:
        dn = (payload.display_name or "").strip() or payload.username
        _validate_password(payload.password)
        cursor = db.execute(
            "INSERT INTO users (username, display_name, password_hash, api_token) VALUES (%s, %s, %s, %s)",
            (payload.username, dn, hash_password(payload.password), make_token()), commit=True,
        )
        user_id = cursor.lastrowid

    db.execute(
        "INSERT INTO user_guilds (user_id, guild_id, role) VALUES (%s, %s, %s)",
        (user_id, guild_id, payload.role), commit=True,
    )
    return db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(guild_id: int, user_id: int, payload: UserUpdateRequest, current_user: dict = Depends(get_current_user)):
    is_admin = current_user.get("role") == "admin"
    if not is_admin and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="他のユーザーの編集権限がありません")

    if not db.query_one(
        "SELECT 1 FROM user_guilds WHERE user_id = %s AND guild_id = %s",
        (user_id, guild_id),
    ):
        raise HTTPException(status_code=404, detail="ユーザが見つかりません")

    if not payload.password and not payload.role and payload.display_name is None:
        raise HTTPException(status_code=400, detail="更新する項目がありません")

    if payload.password:
        _validate_password(payload.password)
        if not is_admin:
            if not payload.current_password:
                raise HTTPException(status_code=400, detail="現在のパスワードを入力してください")
            user_data = db.query_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            if not verify_password(payload.current_password, user_data["password_hash"]):
                raise HTTPException(status_code=401, detail="現在のパスワードが正しくありません")
        db.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (hash_password(payload.password), user_id), commit=True,
        )
    if payload.display_name is not None:
        dn = payload.display_name.strip() or None
        db.execute(
            "UPDATE users SET display_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (dn, user_id), commit=True,
        )
    if payload.role and is_admin:
        if payload.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="role は admin または user を指定してください")
        db.execute(
            "UPDATE user_guilds SET role = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = %s AND guild_id = %s",
            (payload.role, user_id, guild_id), commit=True,
        )

    return db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))


@router.post("/users/{user_id}/unlock", response_model=UserResponse)
def unlock_user(guild_id: int, user_id: int, _admin: dict = Depends(require_admin)):
    if not db.query_one("SELECT 1 FROM user_guilds WHERE user_id = %s AND guild_id = %s", (user_id, guild_id)):
        raise HTTPException(status_code=404, detail="ユーザが見つかりません")
    db.execute(
        "UPDATE users SET login_attempts = 0, locked_until = NULL, login_locked = 0 WHERE id = %s",
        (user_id,), commit=True,
    )
    return db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))


@router.post("/users/{user_id}/ban")
def ban_user(guild_id: int, user_id: int, current_admin: dict = Depends(require_admin)):
    if current_admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="自分自身をBANできません")
    user = db.query_one("SELECT username FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    db.execute(
        "INSERT IGNORE INTO guild_bans (guild_id, username) VALUES (%s, %s)",
        (guild_id, user["username"]), commit=True,
    )
    return db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))


@router.post("/users/{user_id}/unban")
def unban_user(guild_id: int, user_id: int, _admin: dict = Depends(require_admin)):
    user = db.query_one("SELECT username FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    db.execute(
        "DELETE FROM guild_bans WHERE guild_id = %s AND username = %s",
        (guild_id, user["username"]), commit=True,
    )
    return db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))


@router.get("/users/{user_id}/profile")
def get_user_profile(guild_id: int, user_id: int, current_user: dict = Depends(get_current_user)):
    is_admin = current_user.get("role") == "admin"
    if not is_admin and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="他のユーザーのプロフィールを閲覧する権限がありません")

    user = db.query_one(f"{_USER_SELECT} WHERE u.id = %s AND ug.guild_id = %s", (user_id, guild_id))
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    created_odai = db.query(
        "SELECT id, filename, is_favorite, added_at FROM odai "
        "WHERE guild_id = %s AND created_by = %s AND deleted_at IS NULL ORDER BY added_at DESC",
        (guild_id, user_id),
    )
    created_tags = db.query(
        "SELECT id, name, description, is_favorite, created_at FROM tags "
        "WHERE guild_id = %s AND created_by = %s ORDER BY created_at DESC",
        (guild_id, user_id),
    )
    return {
        "user": dict(user),
        "created_odai": list(created_odai),
        "created_tags": list(created_tags),
    }


@router.delete("/users/{user_id}", status_code=204)
def delete_user(guild_id: int, user_id: int, current_user: dict = Depends(require_admin)):
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="自分自身は削除できません")

    if not db.query_one(
        "SELECT 1 FROM user_guilds WHERE user_id = %s AND guild_id = %s",
        (user_id, guild_id),
    ):
        raise HTTPException(status_code=404, detail="ユーザが見つかりません")

    # このサーバーとの紐付けのみ削除（他サーバーのデータは保持）
    db.execute(
        "DELETE FROM user_guilds WHERE user_id = %s AND guild_id = %s",
        (user_id, guild_id), commit=True,
    )
    return Response(status_code=204)
