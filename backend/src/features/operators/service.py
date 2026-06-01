"""Бизнес-логика присутствия операторов."""

from fastapi import Depends
from redis.asyncio import Redis

from src.core.redis import get_redis
from src.features.operators.repository import operator_presence_repository
from src.features.operators.schemas import OperatorMeResponse, OperatorStatusResponse


class OperatorService:
    """Сервис управления статусом и нагрузкой операторов."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_status(self, operator_id: int, online: bool) -> OperatorStatusResponse:
        """Переключает статус оператора онлайн/офлайн."""
        if online:
            await operator_presence_repository.set_online(self._redis, operator_id)
            status = 'online'
        else:
            await operator_presence_repository.set_offline(self._redis, operator_id)
            status = 'offline'
        return OperatorStatusResponse(operator_id=operator_id, status=status)

    async def get_me(self, operator_id: int) -> OperatorMeResponse:
        """Возвращает текущий статус и нагрузку оператора."""
        status = await operator_presence_repository.get_status(self._redis, operator_id)
        active = await operator_presence_repository.get_active_count(self._redis, operator_id)
        return OperatorMeResponse(
            operator_id=operator_id,
            status=status or 'offline',
            active_chats_count=active,
        )


def get_operator_service(redis: Redis = Depends(get_redis)) -> OperatorService:
    """Dependency: сервис операторов с общим Redis-клиентом."""
    return OperatorService(redis)
