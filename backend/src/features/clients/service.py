"""Бизнес-логика фичи клиентов (CRUD)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import EntityNotFoundError
from src.features.clients.repository import client_repository
from src.features.clients.schemas import (
    ClientCreateRequest,
    ClientCreateResponse,
    ClientGetResponse,
    ClientListItem,
    ClientListResponse,
    ClientUpdateRequest,
    ClientUpdateResponse,
)


class ClientService:
    """Сервис управления клиентами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: ClientCreateRequest) -> ClientCreateResponse:
        """Создаёт клиента."""
        record = await client_repository.create(self._session, payload.model_dump())
        return ClientCreateResponse.model_validate(record)

    async def get_one(self, client_id: int) -> ClientGetResponse:
        """Возвращает клиента по id."""
        record = await client_repository.get(self._session, client_id)
        if record is None:
            raise EntityNotFoundError('Клиент не найден')
        return ClientGetResponse.model_validate(record)

    async def get_list(self, page: int, page_size: int) -> ClientListResponse:
        """Возвращает постраничный список клиентов."""
        offset = (page - 1) * page_size
        records, total = await client_repository.get_list(self._session, offset, page_size)
        return ClientListResponse(
            items=[ClientListItem.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(self, client_id: int, payload: ClientUpdateRequest) -> ClientUpdateResponse:
        """Обновляет клиента."""
        values = payload.model_dump(exclude_unset=True)
        record = await client_repository.update(self._session, client_id, values)
        if record is None:
            raise EntityNotFoundError('Клиент не найден')
        return ClientUpdateResponse.model_validate(record)

    async def delete(self, client_id: int) -> None:
        """Удаляет клиента."""
        deleted = await client_repository.delete(self._session, client_id)
        if not deleted:
            raise EntityNotFoundError('Клиент не найден')


def get_client_service(session: AsyncSession = Depends(get_session)) -> ClientService:
    """Dependency: сервис клиентов с сессией запроса."""
    return ClientService(session)
