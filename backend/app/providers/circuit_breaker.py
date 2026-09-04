import time
import redis

FAILURE_THRESHOLD = 3
COOLDOWN_SECONDS = 60

class CircuitBreaker:
    """
    Tracks consecutive provider failures in Redis. After FAILURE_THRESHOLD
    consecutive failures, the circuit opens for COOLDOWN_SECONDS, during
    which calls are skipped without hitting the provider at all.
    """

    def __init__(self, redis_client: redis.Redis, provider_name: str):
        self.r = redis_client
        self.failures_key = f"provider:{provider_name}:failures"
        self.open_until_key = f"provider:{provider_name}:circuit_until"

    def is_open(self) -> bool:
        until = self.r.get(self.open_until_key)
        if until is None:
            return False
        return time.time() < float(until)

    def record_success(self):
        self.r.delete(self.failures_key)

    def record_failure(self):
        failures = self.r.incr(self.failures_key)
        self.r.expire(self.failures_key, COOLDOWN_SECONDS * 5)
        if failures >= FAILURE_THRESHOLD:
            self.r.set(self.open_until_key, time.time() + COOLDOWN_SECONDS)
