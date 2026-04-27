from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user, notify_service
from ..schemas import TestPostRequest

router = APIRouter(prefix="/api/guilds/{guild_id}", tags=["test-post"])


@router.post("/test-post", dependencies=[Depends(get_current_user)])
# 投稿候補をテスト取得します。Dashboard のテスト投稿機能で使用します。
def test_post(guild_id: int, payload: TestPostRequest):
    schedule = {
        "tag_mode": payload.tag_mode or "all",
        "tag_list": payload.tag_list or [],
    }
    candidate = notify_service.select_candidate(guild_id, payload.channel_id, schedule)
    if not candidate:
        raise HTTPException(status_code=404, detail="投稿候補のお題が見つかりません")

    return {"data": candidate}
