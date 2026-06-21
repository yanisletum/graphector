import json
import hashlib
import os
import redis.asyncio as aioredis

CACHE_TTL = 60 * 60 * 24  # 24 часа


def get_redis() -> aioredis.Redis:
    return aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        encoding="utf-8",
        decode_responses=True,
    )


def make_cache_key(code: str) -> str:
    """SHA256 от кода — ключ в Redis"""
    digest = hashlib.sha256(code.strip().encode()).hexdigest()
    return f"graphector:review:{digest}"


async def get_cached(code: str) -> dict | None:
    redis = get_redis()
    try:
        key = make_cache_key(code)
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception:
        return None  # Redis недоступен — идём дальше без кэша
    finally:
        await redis.aclose()


async def set_cached(code: str, result: dict) -> None:
    redis = get_redis()
    try:
        key = make_cache_key(code)
        await redis.setex(key, CACHE_TTL, json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
    finally:
        await redis.aclose()
