"""Подключение к Redis (async) — один клиент на всё приложение."""

from redis.asyncio import Redis

from src.core.config import settings

# Один Redis-клиент на весь процесс. decode_responses=True — работаем со строками.
redis_client: Redis = Redis.from_url(
    settings.REDIS_URL,
    encoding='utf-8',
    decode_responses=True,
)


async def get_redis() -> Redis:
    """Dependency: возвращает общий Redis-клиент приложения."""
    return redis_client
