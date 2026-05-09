"""Free プラン向けスケジュール管理（1件制限）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import db, get_current_user, get_guild_plan
from ..schemas import ScheduleRequest

router = APIRouter(prefix="/api/guilds/{guild_id}", tags=["plan-schedule"])


def _is_pro(guild_id: int) -> bool:
    return get_guild_plan(guild_id).get("plan_name") in ("pro", "enterprise")


@router.get("/plan-schedule", dependencies=[Depends(get_current_user)])
def get_plan_schedule(guild_id: int):
    rows = db.query(
        "SELECT id, channel_id, time, enabled, tag_mode, tag_list "
        "FROM schedules WHERE guild_id = %s ORDER BY id LIMIT 1",
        (guild_id,),
    )
    if not rows:
        return {"data": None}
    row = dict(rows[0])
    row["channel_id"] = str(row["channel_id"])
    return {"data": row}


@router.post("/plan-schedule", dependencies=[Depends(get_current_user)])
def upsert_plan_schedule(guild_id: int, payload: ScheduleRequest):
    existing = db.query(
        "SELECT id FROM schedules WHERE guild_id = %s ORDER BY id LIMIT 1",
        (guild_id,),
    )

    if existing:
        db.execute(
            "UPDATE schedules SET channel_id = %s, time = %s, enabled = 1 WHERE id = %s",
            (payload.channel_id, payload.time, existing[0]["id"]),
            commit=True,
        )
        schedule_id = existing[0]["id"]
    else:
        if not _is_pro(guild_id):
            count = db.query_one(
                "SELECT COUNT(*) AS cnt FROM schedules WHERE guild_id = %s", (guild_id,)
            )["cnt"]
            if count >= 1:
                raise HTTPException(status_code=403, detail="このプランでは1件のスケジュールのみ登録できます")
        cursor = db.execute(
            "INSERT INTO schedules (guild_id, channel_id, time, enabled, tag_mode) VALUES (%s, %s, %s, 1, 'all')",
            (guild_id, payload.channel_id, payload.time),
            commit=True,
        )
        schedule_id = cursor.lastrowid

    row = db.query_one(
        "SELECT id, channel_id, time, enabled FROM schedules WHERE id = %s", (schedule_id,)
    )
    row["channel_id"] = str(row["channel_id"])
    return {"data": row}


@router.delete("/plan-schedule/{schedule_id}", status_code=204, dependencies=[Depends(get_current_user)])
def delete_plan_schedule(guild_id: int, schedule_id: int):
    if not db.query_one(
        "SELECT 1 FROM schedules WHERE id = %s AND guild_id = %s", (schedule_id, guild_id)
    ):
        raise HTTPException(status_code=404, detail="スケジュールが見つかりません")
    db.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,), commit=True)
    return Response(status_code=204)
