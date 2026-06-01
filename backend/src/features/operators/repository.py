"""Репозиторий присутствия и нагрузки операторов в Redis.

Здесь живёт вся балансировка: статус онлайн/офлайн, счётчик активных чатов
(Sorted Set) и чёрный список операторов по конкретному чату.
"""

from redis.asyncio import Redis

from src.core.config import settings

# Ключи Redis
_ACTIVE_CHATS_ZSET = 'operators:active_chats_count'


def _status_key(operator_id: int) -> str:
    return f'operator:{operator_id}:status'


def _rejected_key(chat_id: int) -> str:
    return f'chat:{chat_id}:rejected_by'


class OperatorPresenceRepository:
    """Доступ к состоянию операторов в Redis. Stateless, redis передаётся в методы."""

    async def set_online(self, redis: Redis, operator_id: int) -> None:
        """Помечает оператора онлайн и добавляет в Sorted Set нагрузки (score не сбрасывая)."""
        await redis.set(_status_key(operator_id), 'online')
        # nx=True — не перезаписываем счётчик, если оператор уже в наборе.
        await redis.zadd(_ACTIVE_CHATS_ZSET, {str(operator_id): 0}, nx=True)

    async def set_offline(self, redis: Redis, operator_id: int) -> None:
        """Помечает оператора офлайн и убирает из Sorted Set нагрузки."""
        await redis.set(_status_key(operator_id), 'offline')
        await redis.zrem(_ACTIVE_CHATS_ZSET, str(operator_id))

    async def get_status(self, redis: Redis, operator_id: int) -> str | None:
        """Возвращает строковый статус оператора или None."""
        return await redis.get(_status_key(operator_id))

    async def get_active_count(self, redis: Redis, operator_id: int) -> int:
        """Возвращает число активных чатов оператора (0, если нет в наборе)."""
        score = await redis.zscore(_ACTIVE_CHATS_ZSET, str(operator_id))
        return int(score) if score is not None else 0

    async def change_load(self, redis: Redis, operator_id: int, delta: int) -> None:
        """Изменяет счётчик активных чатов оператора на delta (+1 / -1)."""
        await redis.zincrby(_ACTIVE_CHATS_ZSET, delta, str(operator_id))

    async def find_available_operator(self, redis: Redis, rejected_ids: set[int]) -> int | None:
        """Возвращает онлайн-оператора с наименьшей нагрузкой, не из чёрного списка."""
        # Операторы по возрастанию счётчика активных чатов.
        members = await redis.zrange(_ACTIVE_CHATS_ZSET, 0, -1)
        for member in members:
            operator_id = int(member)
            if operator_id not in rejected_ids:
                return operator_id
        return None

    async def add_rejected(self, redis: Redis, chat_id: int, operator_id: int) -> None:
        """Добавляет оператора в чёрный список чата (с TTL)."""
        key = _rejected_key(chat_id)
        await redis.sadd(key, str(operator_id))
        await redis.expire(key, settings.CHAT_REJECTED_TTL_SECONDS)

    async def get_rejected(self, redis: Redis, chat_id: int) -> set[int]:
        """Возвращает множество id операторов, отклонивших чат."""
        members = await redis.smembers(_rejected_key(chat_id))
        return {int(m) for m in members}

    async def clear_rejected(self, redis: Redis, chat_id: int) -> None:
        """Очищает чёрный список чата (например, после закрытия)."""
        await redis.delete(_rejected_key(chat_id))


operator_presence_repository = OperatorPresenceRepository()
