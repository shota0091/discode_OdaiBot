from __future__ import annotations
import json

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import db, get_current_user, require_admin, require_pro_plan
from ..schemas import ScheduleRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/schedules", tags=["schedules"], dependencies=[Depends(require_pro_plan)])


def _deserialize(row: dict) -> dict:
    return {
        **row,
        "channel_id": str(row["channel_id"]),   # JS の float 精度損失を防ぐため文字列で返す
        "enabled": bool(row.get("enabled")),
        "tag_list": json.loads(row["tag_list"]) if row.get("tag_list") else [],
        "channel_name": row.get("channel_name"),
    }


@router.get("", dependencies=[Depends(get_current_user)])
def list_schedules(guild_id: int):
    rows = db.query(
        "SELECT s.id, s.guild_id, s.channel_id, s.time, s.enabled, s.tag_mode, s.tag_list, "
        "s.created_at, s.updated_at, c.name AS channel_name "
        "FROM schedules s "
        "LEFT JOIN channels c ON s.guild_id = c.guild_id AND s.channel_id = c.channel_id "
        "WHERE s.guild_id = %s ORDER BY s.id",
        (guild_id,),
    )
    return {"data": [_deserialize(r) for r in rows]}


@router.post("", dependencies=[Depends(get_current_user)], status_code=201)
def create_schedule(guild_id: int, payload: ScheduleRequest):
    _validate_schedule(payload)
    tag_list_json = json.dumps(payload.tag_list or [], ensure_ascii=False)
    cursor = db.execute(
        "INSERT INTO schedules (guild_id, channel_id, time, enabled, tag_mode, tag_list) VALUES (%s, %s, %s, %s, %s, %s)",
        (guild_id, payload.channel_id, payload.time, 1 if payload.enabled else 0, payload.tag_mode, tag_list_json),
        commit=True,
    )
    row = db.query_one(
        "SELECT id, guild_id, channel_id, time, enabled, tag_mode, tag_list, created_at, updated_at FROM schedules WHERE id = %s",
        (cursor.lastrowid,),
    )
    return {"data": _deserialize(row)}


@router.put("/{schedule_id}", dependencies=[Depends(get_current_user)])
def update_schedule(guild_id: int, schedule_id: int, payload: ScheduleRequest):
    if not db.query_one("SELECT id FROM schedules WHERE guild_id = %s AND id = %s", (guild_id, schedule_id)):
        raise HTTPException(status_code=404, detail="スケジュールが見つかりません")

    _validate_schedule(payload)
    tag_list_json = json.dumps(payload.tag_list or [], ensure_ascii=False)
    db.execute(
        "UPDATE schedules SET channel_id = %s, time = %s, enabled = %s, tag_mode = %s, tag_list = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (payload.channel_id, payload.time, 1 if payload.enabled else 0, payload.tag_mode, tag_list_json, schedule_id),
        commit=True,
    )
    row = db.query_one(
        "SELECT id, guild_id, channel_id, time, enabled, tag_mode, tag_list, created_at, updated_at FROM schedules WHERE id = %s",
        (schedule_id,),
    )
    return {"data": _deserialize(row)}


@router.delete("/{schedule_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_schedule(guild_id: int, schedule_id: int):
    if not db.query_one("SELECT id FROM schedules WHERE guild_id = %s AND id = %s", (guild_id, schedule_id)):
        raise HTTPException(status_code=404, detail="スケジュールが見つかりません")

    db.execute("DELETE FROM schedules WHERE guild_id = %s AND id = %s", (guild_id, schedule_id), commit=True)
    return Response(status_code=204)


def _validate_schedule(payload: ScheduleRequest) -> None:
    import re
    if not re.fullmatch(r"\d{2}:\d{2}", payload.time):
        raise HTTPException(status_code=400, detail="time は HH:MM 形式で指定してください")
    if payload.tag_mode not in ("all", "allow", "deny"):
        raise HTTPException(status_code=400, detail="tag_mode は all / allow / deny のいずれかを指定してください")
    if payload.tag_mode in ("allow", "deny") and not payload.tag_list:
        raise HTTPException(status_code=400, detail=f"tag_mode が {payload.tag_mode} の場合は tag_list を 1 件以上指定してください")
