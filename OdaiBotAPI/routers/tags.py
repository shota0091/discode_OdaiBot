from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import db, get_current_user, require_admin, require_pro_plan
from ..schemas import TagCreateRequest, TagUpdateRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/tags", tags=["tags"], dependencies=[Depends(require_pro_plan)])


@router.get("", dependencies=[Depends(get_current_user)])
def list_tags(guild_id: int, q: str | None = None):
    sql = (
        "SELECT t.id, t.name, t.description, t.is_favorite, t.created_at, t.updated_at, "
        "t.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM tags t LEFT JOIN users u ON u.id = t.created_by "
        "WHERE t.guild_id = %s"
    )
    params: list = [guild_id]
    if q:
        sql += " AND t.name LIKE %s"
        params.append(f"%{q}%")
    return {"data": db.query(sql, tuple(params))}


@router.post("", status_code=201)
def create_tag(guild_id: int, payload: TagCreateRequest, current_user: dict = Depends(get_current_user)):
    if db.query_one("SELECT id FROM tags WHERE guild_id = %s AND name = %s", (guild_id, payload.name)):
        raise HTTPException(status_code=409, detail="同名タグが既に存在します")

    cursor = db.execute(
        "INSERT INTO tags (guild_id, name, description, created_by) VALUES (%s, %s, %s, %s)",
        (guild_id, payload.name, payload.description, current_user["id"]),
        commit=True,
    )
    tag = db.query_one(
        "SELECT t.id, t.name, t.description, t.is_favorite, t.created_at, t.updated_at, "
        "t.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM tags t LEFT JOIN users u ON u.id = t.created_by WHERE t.id = %s",
        (cursor.lastrowid,),
    )
    return {"data": tag}


@router.put("/{tag_id}", dependencies=[Depends(get_current_user)])
def update_tag(guild_id: int, tag_id: int, payload: TagUpdateRequest):
    if not db.query_one("SELECT id FROM tags WHERE guild_id = %s AND id = %s", (guild_id, tag_id)):
        raise HTTPException(status_code=404, detail="タグが見つかりません")

    if payload.name is not None:
        dup = db.query_one(
            "SELECT id FROM tags WHERE guild_id = %s AND name = %s AND id != %s",
            (guild_id, payload.name, tag_id),
        )
        if dup:
            raise HTTPException(status_code=409, detail="同名タグが既に存在します")

    updates, params = [], []
    if payload.name is not None:
        updates.append("name = %s")
        params.append(payload.name)
    if payload.description is not None:
        updates.append("description = %s")
        params.append(payload.description)
    if payload.is_favorite is not None:
        updates.append("is_favorite = %s")
        params.append(1 if payload.is_favorite else 0)
    if not updates:
        raise HTTPException(status_code=400, detail="更新する項目がありません")

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(tag_id)
    db.execute(
        f"UPDATE tags SET {', '.join(updates)} WHERE id = %s",
        tuple(params),
        commit=True,
    )
    return {"data": db.query_one(
        "SELECT t.id, t.name, t.description, t.is_favorite, t.created_at, t.updated_at, "
        "t.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM tags t LEFT JOIN users u ON u.id = t.created_by WHERE t.id = %s",
        (tag_id,),
    )}


@router.get("/{tag_id}/detail", dependencies=[Depends(get_current_user)])
def get_tag_detail(guild_id: int, tag_id: int):
    tag = db.query_one(
        "SELECT t.id, t.name, t.description, t.is_favorite, t.created_at, t.updated_at, "
        "t.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM tags t LEFT JOIN users u ON u.id = t.created_by "
        "WHERE t.guild_id = %s AND t.id = %s",
        (guild_id, tag_id),
    )
    if not tag:
        raise HTTPException(status_code=404, detail="タグが見つかりません")

    odai_rows = db.query(
        "SELECT o.id, o.filename, ot.created_at AS tagged_at, "
        "COALESCE(u.display_name, u.username) AS tagged_by_name "
        "FROM odai_tags ot "
        "JOIN odai o ON o.id = ot.odai_id AND o.deleted_at IS NULL "
        "LEFT JOIN users u ON u.id = ot.created_by "
        "WHERE ot.tag_id = %s "
        "ORDER BY ot.created_at DESC",
        (tag_id,),
    )

    schedule_rows = db.query(
        "SELECT s.id, s.time, s.enabled, s.tag_mode, c.name AS channel_name "
        "FROM schedules s "
        "LEFT JOIN channels c ON s.guild_id = c.guild_id AND s.channel_id = c.channel_id "
        "WHERE s.guild_id = %s AND s.tag_mode IN ('allow', 'deny') "
        "AND JSON_CONTAINS(s.tag_list, JSON_QUOTE(%s))",
        (guild_id, tag["name"]),
    )
    for r in schedule_rows:
        r["enabled"] = bool(r["enabled"])

    return {"data": {**tag, "odai": odai_rows, "schedules": schedule_rows}}


@router.delete("/{tag_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_tag(guild_id: int, tag_id: int):
    if not db.query_one("SELECT id FROM tags WHERE guild_id = %s AND id = %s", (guild_id, tag_id)):
        raise HTTPException(status_code=404, detail="タグが見つかりません")

    db.execute("DELETE FROM tags WHERE id = %s", (tag_id,), commit=True)
    return Response(status_code=204)
