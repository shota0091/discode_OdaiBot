"""OdaiBotAPI のエントリポイント。

このファイルは FastAPI アプリケーションを作成し、機能別に分割したルータを登録します。
- `deps.py` で DB / 認証 / リポジトリの共通依存を定義
- `routers/` 以下に API ごとのエンドポイントを分離

`api.py` 自体はルータの登録とライフサイクル管理のみを担当し、具体的なビジネスロジックは各 router モジュールに委譲します。
"""

from __future__ import annotations
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT.parent / "OdaiBot"))

from .deps import db
from .routers import auth_router, auth_global_router, odai_router, schedules_router, settings_router, summary_router, tags_router, test_post_router

app = FastAPI(title="OdaiBotAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各機能ごとのルータを登録します。
app.include_router(auth_global_router)
app.include_router(auth_router)
app.include_router(odai_router)
app.include_router(tags_router)
app.include_router(schedules_router)
app.include_router(settings_router)
app.include_router(summary_router)
app.include_router(test_post_router)


@app.on_event("shutdown")
def shutdown_event():
    """アプリシャットダウン時に共通 DB 接続を閉じます。"""
    db.close()
