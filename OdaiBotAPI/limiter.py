import time
from collections import defaultdict

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)


def _check(request: Request, limit: int, window: int) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _buckets[ip] = [t for t in _buckets[ip] if now - t < window]
    if len(_buckets[ip]) >= limit:
        wait_sec = int(window - (now - _buckets[ip][0])) + 1
        wait_msg = f"{(wait_sec + 59) // 60}分" if wait_sec >= 60 else f"{wait_sec}秒"
        raise HTTPException(
            status_code=429,
            detail=f"リクエスト数が上限を超えました。{wait_msg}後に再試行してください。",
        )
    _buckets[ip].append(now)


def login_rate_limit(request: Request) -> None:
    _check(request, limit=10, window=60)


def reset_rate_limit(request: Request) -> None:
    _check(request, limit=5, window=60)
