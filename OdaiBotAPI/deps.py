from __future__ import annotations
import hashlib
import secrets
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT.parent))

from OdaiBotDB.database import MySQLDatabase
from OdaiBot.Repository.OdaiRepository import OdaiRepository
from OdaiBot.Repository.ScheduleRepository import ScheduleRepository
from OdaiBot.Service.NotifyServiceImpl import NotifyServiceImpl

security = HTTPBearer(auto_error=False)

db = MySQLDatabase()
odai_repo = OdaiRepository(db)
schedule_repo = ScheduleRepository(db)
notify_service = NotifyServiceImpl(odai_repo, db)


def normalize_tags(tags: Optional[str] | List[str]) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        return [item.strip() for item in tags.split(",") if item.strip()]
    return [item.strip() for item in tags if item and item.strip()]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
    except ValueError:
        return False
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return secrets.compare_digest(key.hex(), digest)


def make_token() -> str:
    return secrets.token_urlsafe(32)


def get_user_by_token(token: str, guild_id: int) -> Optional[dict]:
    return db.query_one(
        "SELECT u.id, ug.guild_id, u.username, ug.role "
        "FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
        "WHERE u.api_token = %s AND ug.guild_id = %s "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM guild_bans gb WHERE gb.guild_id = %s AND gb.username = u.username"
        ")",
        (token, guild_id, guild_id),
    )


def get_optional_current_user(guild_id: int, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return get_user_by_token(credentials.credentials, guild_id)


def get_current_user(guild_id: int, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    user = get_optional_current_user(guild_id, credentials)
    if not user:
        raise HTTPException(status_code=401, detail="認証トークンが必要です")
    return user


def require_admin(guild_id: int, user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return user


def has_guild_users(guild_id: int) -> bool:
    return db.query_one("SELECT 1 FROM user_guilds WHERE guild_id = %s", (guild_id,)) is not None


def get_guild_plan(guild_id: int) -> dict:
    """guild_plans + plans を JOIN して返す。レコードなしは free プラン扱い。"""
    gp = db.query_one(
        "SELECT p.name AS plan_name, p.has_dashboard, p.has_discord_op, p.can_expand_capacity, "
        "p.custom_odai_max, gp.custom_odai_capacity, gp.status "
        "FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id "
        "WHERE gp.guild_id = %s",
        (guild_id,),
    )
    if gp:
        return gp
    free = db.query_one(
        "SELECT name AS plan_name, has_dashboard, has_discord_op, can_expand_capacity, custom_odai_max "
        "FROM plans WHERE name = 'free'",
        (),
    )
    return {**(free or {}), "custom_odai_capacity": 0, "status": "active"}


def require_dashboard_plan(guild_id: int) -> None:
    """has_dashboard = 0 のプランはログイン不可（Light プラン以上が必要）。"""
    plan = get_guild_plan(guild_id)
    if not plan.get("has_dashboard"):
        raise HTTPException(status_code=403, detail="このプランでは Dashboard を利用できません（Light プラン以上が必要です）")


def require_pro_plan(guild_id: int, _: dict = Depends(get_current_user)) -> None:
    """Pro / Enterprise プラン以外はアクセス不可。認証チェックを先行させることで未認証時は401を返す。"""
    plan = get_guild_plan(guild_id)
    if plan.get("plan_name") not in ("pro", "enterprise"):
        raise HTTPException(status_code=403, detail="この機能は Pro プラン以上が必要です")


def check_odai_capacity(guild_id: int, adding: int = 1) -> None:
    """独自お題の登録上限をチェック。上限超えは 403。cap=NULL は無制限。"""
    plan = get_guild_plan(guild_id)
    cap = plan.get("custom_odai_capacity")
    if cap is None:
        return  # NULL = 無制限
    if cap == 0:
        raise HTTPException(status_code=403, detail="このプランでは独自お題を登録できません（Light プラン以上が必要です）")
    current_row = db.query_one(
        "SELECT COUNT(*) AS cnt FROM odai WHERE guild_id = %s AND deleted_at IS NULL",
        (guild_id,),
    )
    current = current_row["cnt"] if current_row else 0
    if current + adding > cap:
        raise HTTPException(status_code=403, detail=f"お題の登録上限（{cap} 件）に達しています。容量を拡張してください")
