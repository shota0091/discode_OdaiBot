from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

_IMAGE_DIR = Path(os.getenv("ODAI_IMAGE_DIR", "/data/odai"))

from ..deps import db, get_current_user, normalize_tags, odai_repo, require_admin
from ..schemas import OdaiUpdateRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/odai", tags=["odai"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB


def _get_odai_with_tags(guild_id: int, odai_id: int) -> dict | None:
    row = db.query_one(
        "SELECT o.id, o.guild_id, o.filename, o.storage_path, o.is_favorite, o.memo, o.added_at, o.updated_at, o.deleted_at, "
        "o.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM odai o LEFT JOIN users u ON u.id = o.created_by "
        "WHERE o.guild_id = %s AND o.id = %s",
        (guild_id, odai_id),
    )
    if not row:
        return None
    row["tags"] = odai_repo.get_tags(row["id"])
    return row


def _get_odai_by_filename(guild_id: int, filename: str) -> dict | None:
    row = db.query_one(
        "SELECT o.id, o.guild_id, o.filename, o.storage_path, o.is_favorite, o.memo, o.added_at, o.updated_at, o.deleted_at, "
        "o.created_by, COALESCE(u.display_name, u.username) AS created_by_name "
        "FROM odai o LEFT JOIN users u ON u.id = o.created_by "
        "WHERE o.guild_id = %s AND o.filename = %s",
        (guild_id, filename),
    )
    if not row:
        return None
    row["tags"] = odai_repo.get_tags(row["id"])
    return row


@router.get("", dependencies=[Depends(get_current_user)])
def list_odai(guild_id: int, filename: Optional[str] = None, tag: Optional[str] = None, favorite: Optional[bool] = None):
    sql = (
        "SELECT DISTINCT o.id, o.guild_id, o.filename, o.storage_path, o.is_favorite, o.memo, o.added_at, o.updated_at, o.deleted_at, "
        "o.created_by, COALESCE(cu.display_name, cu.username) AS created_by_name, "
        "COALESCE(uc.usage_count, 0) AS usage_count "
        "FROM odai o "
        "LEFT JOIN users cu ON cu.id = o.created_by "
        "LEFT JOIN ("
        "  SELECT odai_id, COUNT(DISTINCT channel_id) AS usage_count FROM odai_usage GROUP BY odai_id"
        ") uc ON uc.odai_id = o.id"
    )
    params: list = []

    if tag:
        sql += (
            " JOIN odai_tags ot ON ot.odai_id = o.id"
            " JOIN tags t ON t.id = ot.tag_id AND t.name = %s"
        )
        params.append(tag)

    sql += " WHERE o.guild_id = %s AND o.deleted_at IS NULL"
    params.append(guild_id)

    if filename:
        sql += " AND o.filename LIKE %s"
        params.append(f"%{filename}%")

    if favorite is not None:
        sql += " AND o.is_favorite = %s"
        params.append(1 if favorite else 0)

    rows = db.query(sql, tuple(params))

    total_row = db.query_one(
        "SELECT COUNT(DISTINCT channel_id) AS cnt FROM schedules WHERE guild_id = %s AND enabled = 1",
        (guild_id,),
    )
    total_channels = total_row["cnt"] if total_row else 0

    for row in rows:
        row["tags"] = odai_repo.get_tags(row["id"])
        row["total_channels"] = total_channels
    return {"data": rows}


@router.get("/{odai_id}/history", dependencies=[Depends(get_current_user)])
def get_odai_history(guild_id: int, odai_id: int, page: int = 1, per_page: int = 5):
    if not db.query_one("SELECT id FROM odai WHERE id = %s AND guild_id = %s", (odai_id, guild_id)):
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    per_page = max(1, min(per_page, 50))
    offset = (page - 1) * per_page

    total_row = db.query_one(
        "SELECT COUNT(*) AS cnt FROM odai_history WHERE odai_id = %s",
        (odai_id,),
    )
    total = total_row["cnt"] if total_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    rows = db.query(
        "SELECT h.id, h.action, h.detail, h.created_at, h.user_id, "
        "COALESCE(u.display_name, u.username) AS user_name "
        "FROM odai_history h LEFT JOIN users u ON u.id = h.user_id "
        "WHERE h.odai_id = %s "
        "ORDER BY h.created_at DESC "
        "LIMIT %s OFFSET %s",
        (odai_id, per_page, offset),
    )
    return {"data": rows, "total": total, "page": page, "per_page": per_page, "total_pages": total_pages}


@router.get("/{odai_id}/usage", dependencies=[Depends(get_current_user)])
def get_odai_usage(guild_id: int, odai_id: int):
    if not db.query_one(
        "SELECT id FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL",
        (odai_id, guild_id),
    ):
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    rows = db.query(
        "SELECT ou.channel_id, c.name AS channel_name, ou.used_at "
        "FROM odai_usage ou "
        "LEFT JOIN channels c ON ou.guild_id = c.guild_id AND ou.channel_id = c.channel_id "
        "WHERE ou.odai_id = %s "
        "ORDER BY ou.used_at DESC",
        (odai_id,),
    )
    for row in rows:
        row["channel_id"] = str(row["channel_id"])
    return {"data": rows}


@router.post("", status_code=201)
async def upload_odai(
    guild_id: int,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="jpg / png / webp のみアップロード可能です")

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="ファイルサイズは 8 MB 以下にしてください")

    parsed_tags = normalize_tags(tags)
    success, message = odai_repo.add_odai(guild_id, file.filename, content, parsed_tags, created_by=current_user["id"])
    if not success:
        raise HTTPException(status_code=409, detail=message)

    return {"data": _get_odai_by_filename(guild_id, file.filename)}


@router.post("/import", status_code=201)
async def import_odai(
    guild_id: int,
    files: List[UploadFile] = File(...),
    tags: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    parsed_tags = normalize_tags(tags)
    results = []
    for upload in files:
        content = await upload.read()
        success, message = odai_repo.add_odai(guild_id, upload.filename, content, parsed_tags, storage_path=source_path, created_by=current_user["id"])
        item: dict = {"filename": upload.filename, "success": success, "message": message}
        if success:
            item["odai"] = _get_odai_by_filename(guild_id, upload.filename)
        results.append(item)
    return {"data": results}


@router.put("/{odai_id}")
def update_odai(guild_id: int, odai_id: int, payload: OdaiUpdateRequest, current_user: dict = Depends(get_current_user)):
    if not db.query_one("SELECT id FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL", (odai_id, guild_id)):
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    if payload.filename is not None:
        new_name = payload.filename.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="ファイル名は空にできません")
        existing = db.query_one(
            "SELECT id FROM odai WHERE guild_id = %s AND filename = %s AND deleted_at IS NULL AND id != %s",
            (guild_id, new_name, odai_id),
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"同名のファイルが既に存在します: {new_name}")
        db.execute("UPDATE odai SET filename = %s WHERE id = %s", (new_name, odai_id), commit=True)

    if payload.tags is not None:
        old_tags = set(odai_repo.get_tags(odai_id))
        new_tags = set(payload.tags)
        db.execute("DELETE FROM odai_tags WHERE odai_id = %s", (odai_id,), commit=True)
        for tag_name in payload.tags:
            tag_id = odai_repo._ensure_tag(guild_id, tag_name, created_by=current_user["id"])
            db.execute(
                "INSERT IGNORE INTO odai_tags (odai_id, tag_id, created_by) VALUES (%s, %s, %s)",
                (odai_id, tag_id, current_user["id"]),
                commit=False,
            )
        db.conn.commit()
        for tag_name in (new_tags - old_tags):
            db.execute(
                "INSERT INTO odai_history (odai_id, guild_id, action, detail, user_id) VALUES (%s, %s, %s, %s, %s)",
                (odai_id, guild_id, "tagged", tag_name, current_user["id"]),
                commit=False,
            )
        for tag_name in (old_tags - new_tags):
            db.execute(
                "INSERT INTO odai_history (odai_id, guild_id, action, detail, user_id) VALUES (%s, %s, %s, %s, %s)",
                (odai_id, guild_id, "untagged", tag_name, current_user["id"]),
                commit=False,
            )
        if (new_tags - old_tags) or (old_tags - new_tags):
            db.conn.commit()

    if payload.memo is not None:
        memo_val = payload.memo.strip() or None
        db.execute("UPDATE odai SET memo = %s WHERE id = %s", (memo_val, odai_id), commit=True)

    if payload.deleted is not None:
        if payload.deleted:
            db.execute("UPDATE odai SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s", (odai_id,), commit=True)
        else:
            db.execute("UPDATE odai SET deleted_at = NULL WHERE id = %s", (odai_id,), commit=True)

    if payload.is_favorite is not None:
        db.execute("UPDATE odai SET is_favorite = %s WHERE id = %s", (1 if payload.is_favorite else 0, odai_id), commit=True)
        db.execute(
            "INSERT INTO odai_history (odai_id, guild_id, action, user_id) VALUES (%s, %s, %s, %s)",
            (odai_id, guild_id, "favorited" if payload.is_favorite else "unfavorited", current_user["id"]),
            commit=True,
        )

    return {"data": _get_odai_with_tags(guild_id, odai_id)}


@router.get("/{odai_id}/image", dependencies=[Depends(get_current_user)])
def get_odai_image(guild_id: int, odai_id: int):
    row = db.query_one(
        "SELECT filename, storage_path, data FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL",
        (odai_id, guild_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    content: bytes | None = None
    if row.get("storage_path"):
        p = Path(row["storage_path"])
        if p.exists():
            content = p.read_bytes()
    if content is None and row.get("data"):
        content = bytes(row["data"])
    if content is None:
        raise HTTPException(status_code=404, detail="画像データが見つかりません")

    filename = (row["filename"] or "").lower()
    if filename.endswith(".png"):
        media_type = "image/png"
    elif filename.endswith(".webp"):
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"

    return Response(content=content, media_type=media_type)


@router.delete("/{odai_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_odai(guild_id: int, odai_id: int):
    odai = db.query_one("SELECT id FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL", (odai_id, guild_id))
    if not odai:
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    db.execute("UPDATE odai SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s", (odai_id,), commit=True)
    return Response(status_code=204)
