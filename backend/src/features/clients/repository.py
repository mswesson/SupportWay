"""Репозиторий клиентов."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import BaseCrudRepository
from src.features.clients.models import Client


class ClientRepository(BaseCrudRepository[Client]):
    """Доступ к данным таблицы clients."""

    def __init__(self) -> None:
        super().__init__(Client)

    async def get_or_create_by_external(
        self, session: AsyncSession, values: dict[str, Any]
    ) -> Client:
        """Возвращает существующего клиента по (source, external_id) или создаёт нового.

        Если source или external_id не заданы — всегда создаёт нового клиента.
        """
        source = values.get('source')
        external_id = values.get('external_id')
        if source and external_id:
            result = await session.execute(
                select(Client).where(Client.source == source, Client.external_id == external_id)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing
        return await self.create(session, values)


client_repository = ClientRepository()
