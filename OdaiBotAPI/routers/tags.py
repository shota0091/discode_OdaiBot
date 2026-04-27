from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import db, get_current_user, require_admin
from ..schemas import TagCreateRequest, TagUpdateRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/tags", tags=["tags"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_tags(guild_id: int, q: str | None = None):
    sql = "SELECT id, name, description, created_at, updated_at FROM tags WHERE guild_id = %s"
    params: list = [guild_id]
    if q:
        sql += " AND name LIKE %s"
        params.append(f"%{q}%")
    return {"data": db.query(sql, tuple(params))}


@router.post("", dependencies=[Depends(get_current_user)], status_code=201)
def create_tag(guild_id: int, payload: TagCreateRequest):
    if db.query_one("SELECT id FROM tags WHERE guild_id = %s AND name = %s", (guild_id, payload.name)):
        raise HTTPException(status_code=409, detail="同名タグが既に存在します")

    cursor = db.execute(
        "INSERT INTO tags (guild_id, name, description) VALUES (%s, %s, %s)",
        (guild_id, payload.name, payload.description),
        commit=True,
    )
    tag = db.query_one(
        "SELECT id, name, description, created_at, updated_at FROM tags WHERE id = %s",
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
    if not updates:
        raise HTTPException(status_code=400, detail="更新する項目がありません")

    params.append(tag_id)
    db.execute(
        f"UPDATE tags SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        tuple(params),
        commit=True,
    )
    return {"data": db.query_one("SELECT id, name, description, created_at, updated_at FROM tags WHERE id = %s", (tag_id,))}


@router.delete("/{tag_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_tag(guild_id: int, tag_id: int):
    if not db.query_one("SELECT id FROM tags WHERE guild_id = %s AND id = %s", (guild_id, tag_id)):
        raise HTTPException(status_code=404, detail="タグが見つかりません")

    db.execute("DELETE FROM tags WHERE id = %s", (tag_id,), commit=True)
    return Response(status_code=204)
