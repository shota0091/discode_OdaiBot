import time
from collections import defaultdict

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)


def _check(request: Request, limit: int, window: int) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _buckets[ip] = [t for t in _buckets[ip] if now - t < window]
    if len(_buckets[ip]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="リクエスト数が上限を超えました。しばらく経ってから再試行してください。",
        )
    _buckets[ip].append(now)


def login_rate_limit(request: Request) -> None:
    _check(request, limit=10, window=60)


def reset_rate_limit(request: Request) -> None:
    _check(request, limit=5, window=60)
