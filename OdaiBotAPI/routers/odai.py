from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..deps import db, get_current_user, normalize_tags, odai_repo, require_admin
from ..schemas import OdaiUpdateRequest

router = APIRouter(prefix="/api/guilds/{guild_id}/odai", tags=["odai"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB


def _get_odai_with_tags(guild_id: int, odai_id: int) -> dict | None:
    row = db.query_one(
        "SELECT id, guild_id, filename, storage_path, used, added_at, deleted_at FROM odai WHERE guild_id = %s AND id = %s",
        (guild_id, odai_id),
    )
    if not row:
        return None
    row["tags"] = odai_repo.get_tags(row["id"])
    return row


def _get_odai_by_filename(guild_id: int, filename: str) -> dict | None:
    row = db.query_one(
        "SELECT id, guild_id, filename, storage_path, used, added_at, deleted_at FROM odai WHERE guild_id = %s AND filename = %s",
        (guild_id, filename),
    )
    if not row:
        return None
    row["tags"] = odai_repo.get_tags(row["id"])
    return row


@router.get("", dependencies=[Depends(get_current_user)])
def list_odai(guild_id: int, filename: Optional[str] = None, tag: Optional[str] = None, used: Optional[bool] = None):
    sql = (
        "SELECT DISTINCT o.id, o.guild_id, o.filename, o.storage_path, o.used, o.added_at, o.deleted_at "
        "FROM odai o"
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

    if used is not None:
        sql += " AND o.used = %s"
        params.append(1 if used else 0)

    rows = db.query(sql, tuple(params))
    for row in rows:
        row["tags"] = odai_repo.get_tags(row["id"])
    return {"data": rows}


@router.post("", dependencies=[Depends(get_current_user)], status_code=201)
async def upload_odai(
    guild_id: int,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
):
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="jpg / png / webp のみアップロード可能です")

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="ファイルサイズは 8 MB 以下にしてください")

    parsed_tags = normalize_tags(tags)
    success, message = odai_repo.add_odai(guild_id, file.filename, content, parsed_tags)
    if not success:
        raise HTTPException(status_code=409, detail=message)

    return {"data": _get_odai_by_filename(guild_id, file.filename)}


@router.post("/import", dependencies=[Depends(get_current_user)], status_code=201)
async def import_odai(
    guild_id: int,
    files: List[UploadFile] = File(...),
    tags: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
):
    parsed_tags = normalize_tags(tags)
    results = []
    for upload in files:
        content = await upload.read()
        success, message = odai_repo.add_odai(guild_id, upload.filename, content, parsed_tags, storage_path=source_path)
        item: dict = {"filename": upload.filename, "success": success, "message": message}
        if success:
            item["odai"] = _get_odai_by_filename(guild_id, upload.filename)
        results.append(item)
    return {"data": results}


@router.put("/{odai_id}", dependencies=[Depends(get_current_user)])
def update_odai(guild_id: int, odai_id: int, payload: OdaiUpdateRequest):
    if not db.query_one("SELECT id FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL", (odai_id, guild_id)):
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    if payload.tags is not None:
        db.execute("DELETE FROM odai_tags WHERE odai_id = %s", (odai_id,), commit=True)
        for tag_name in payload.tags:
            tag_id = odai_repo._ensure_tag(guild_id, tag_name)
            db.execute(
                "INSERT IGNORE INTO odai_tags (odai_id, tag_id) VALUES (%s, %s)",
                (odai_id, tag_id),
                commit=False,
            )
        db.conn.commit()

    if payload.used is not None:
        db.execute("UPDATE odai SET used = %s WHERE id = %s", (1 if payload.used else 0, odai_id), commit=True)

    if payload.deleted is not None:
        if payload.deleted:
            db.execute("UPDATE odai SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s", (odai_id,), commit=True)
        else:
            db.execute("UPDATE odai SET deleted_at = NULL WHERE id = %s", (odai_id,), commit=True)

    return {"data": _get_odai_with_tags(guild_id, odai_id)}


@router.get("/{odai_id}/image", dependencies=[Depends(get_current_user)])
def get_odai_image(guild_id: int, odai_id: int):
    row = db.query_one(
        "SELECT data, filename FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL",
        (odai_id, guild_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    filename = (row["filename"] or "").lower()
    if filename.endswith(".png"):
        media_type = "image/png"
    elif filename.endswith(".webp"):
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"

    return Response(content=bytes(row["data"]), media_type=media_type)


@router.delete("/{odai_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_odai(guild_id: int, odai_id: int):
    odai = db.query_one("SELECT id FROM odai WHERE id = %s AND guild_id = %s AND deleted_at IS NULL", (odai_id, guild_id))
    if not odai:
        raise HTTPException(status_code=404, detail="お題が見つかりません")

    db.execute("UPDATE odai SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s", (odai_id,), commit=True)
    return Response(status_code=204)
