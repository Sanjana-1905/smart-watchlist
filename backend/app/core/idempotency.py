"""
Idempotency-Key support for unsafe POST endpoints.

Only successful (2xx) responses are cached — a failed request (404/409/etc.)
is intentionally NOT cached, so the caller can safely retry with the same key
after fixing whatever caused the failure, without waiting out a TTL.
"""
import json
import redis

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60  # 24 hours

def _key(user_id, idempotency_key: str) -> str:
    return f"idempotency:{user_id}:{idempotency_key}"

def get_cached_response(redis_client: redis.Redis, user_id, idempotency_key: str | None):
    if not idempotency_key:
        return None
    raw = redis_client.get(_key(user_id, idempotency_key))
    if raw is None:
        return None
    cached = json.loads(raw)
    return cached["status_code"], cached["body"]

def store_response(redis_client: redis.Redis, user_id, idempotency_key: str | None, status_code: int, body):
    if not idempotency_key:
        return
    payload = json.dumps({"status_code": status_code, "body": body})
    redis_client.set(_key(user_id, idempotency_key), payload, ex=IDEMPOTENCY_TTL_SECONDS)
