from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import db, get_current_user

router = APIRouter(prefix="/api/guilds/{guild_id}", tags=["summary"])


@router.get("/dashboard-summary", dependencies=[Depends(get_current_user)])
def dashboard_summary(guild_id: int):
    odai_count = (
        db.query_one("SELECT COUNT(*) AS cnt FROM odai WHERE guild_id = %s AND deleted_at IS NULL", (guild_id,))["cnt"]
    )
    active_schedule_count = (
        db.query_one("SELECT COUNT(*) AS cnt FROM schedules WHERE guild_id = %s AND enabled = 1", (guild_id,))["cnt"]
    )
    channel_count = (
        db.query_one("SELECT COUNT(DISTINCT channel_id) AS cnt FROM schedules WHERE guild_id = %s", (guild_id,))["cnt"]
    )
    last_post = db.query_one(
        "SELECT ph.odai_id, o.filename, ph.channel_id, ph.result, ph.posted_at "
        "FROM post_history ph "
        "JOIN odai o ON ph.odai_id = o.id "
        "WHERE ph.guild_id = %s "
        "ORDER BY ph.posted_at DESC LIMIT 1",
        (guild_id,),
    )
    return {
        "data": {
            "odai_count": odai_count,
            "active_schedule_count": active_schedule_count,
            "channel_count": channel_count,
            "last_post": last_post,
        }
    }
