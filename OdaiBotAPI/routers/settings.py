from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import db, get_current_user, require_admin, require_pro_plan
from ..schemas import SettingsRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/settings", tags=["settings"])

_DEFAULTS = {"bot_enabled": True, "timezone": "Asia/Tokyo"}


@router.get("/name")
def get_guild_name(guild_id: int):
    """認証不要。招待登録ページ向けにサーバー名だけ返す。"""
    row = db.query_one("SELECT guild_name FROM guild_settings WHERE guild_id = %s", (guild_id,))
    return {"guild_name": row["guild_name"] if row else None}


@router.get("/channels", dependencies=[Depends(get_current_user)])
def get_channels(guild_id: int):
    """チャンネル一覧をスケジュールフォームのプルダウン用に返す。"""
    rows = db.query(
        "SELECT channel_id, name FROM channels WHERE guild_id = %s ORDER BY name",
        (guild_id,),
    )
    return {"data": [{"channel_id": str(r["channel_id"]), "name": r["name"]} for r in rows]}


@router.get("", dependencies=[Depends(get_current_user)])
def get_settings(guild_id: int):
    row = db.query_one(
        "SELECT guild_id, guild_name, bot_enabled, timezone, use_default_odai, updated_at FROM guild_settings WHERE guild_id = %s",
        (guild_id,),
    )
    if not row:
        return {"data": {"guild_id": guild_id, "guild_name": None, **_DEFAULTS, "use_default_odai": True, "updated_at": None}}
    row["bot_enabled"] = bool(row["bot_enabled"])
    row["use_default_odai"] = bool(row["use_default_odai"])
    return {"data": row}


@router.put("", dependencies=[Depends(require_admin), Depends(require_pro_plan)])
def update_settings(guild_id: int, payload: SettingsRequest):
    existing = db.query_one("SELECT id FROM guild_settings WHERE guild_id = %s", (guild_id,))

    if existing:
        fields, params = [], []
        if payload.bot_enabled is not None:
            fields.append("bot_enabled = %s")
            params.append(1 if payload.bot_enabled else 0)
        if payload.timezone is not None:
            fields.append("timezone = %s")
            params.append(payload.timezone)
        if payload.use_default_odai is not None:
            fields.append("use_default_odai = %s")
            params.append(1 if payload.use_default_odai else 0)
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(guild_id)
            db.execute(
                f"UPDATE guild_settings SET {', '.join(fields)} WHERE guild_id = %s",
                tuple(params),
                commit=True,
            )
    else:
        bot_enabled = payload.bot_enabled if payload.bot_enabled is not None else _DEFAULTS["bot_enabled"]
        timezone = payload.timezone or _DEFAULTS["timezone"]
        db.execute(
            "INSERT INTO guild_settings (guild_id, bot_enabled, timezone) VALUES (%s, %s, %s)",
            (guild_id, 1 if bot_enabled else 0, timezone),
            commit=True,
        )

    row = db.query_one(
        "SELECT guild_id, bot_enabled, timezone, use_default_odai, updated_at FROM guild_settings WHERE guild_id = %s",
        (guild_id,),
    )
    row["bot_enabled"] = bool(row["bot_enabled"])
    row["use_default_odai"] = bool(row["use_default_odai"])
    return {"data": row}
