"""Бизнес-логика фичи сообщений (CRUD для чтения/модерации)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import EntityNotFoundError
from src.features.messages.repository import message_repository
from src.features.messages.schemas import (
    MessageCreateRequest,
    MessageCreateResponse,
    MessageGetResponse,
    MessageListItem,
    MessageListResponse,
    MessageUpdateRequest,
    MessageUpdateResponse,
)


class MessageService:
    """Сервис управления сообщениями (чтение/модерация)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: MessageCreateRequest) -> MessageCreateResponse:
        """Создаёт сообщение."""
        record = await message_repository.create(self._session, payload.model_dump())
        return MessageCreateResponse.model_validate(record)

    async def get_one(self, message_id: int) -> MessageGetResponse:
        """Возвращает сообщение по id."""
        record = await message_repository.get(self._session, message_id)
        if record is None:
            raise EntityNotFoundError('Сообщение не найдено')
        return MessageGetResponse.model_validate(record)

    async def get_list(self, page: int, page_size: int) -> MessageListResponse:
        """Возвращает постраничный список сообщений."""
        offset = (page - 1) * page_size
        records, total = await message_repository.get_list(self._session, offset, page_size)
        return MessageListResponse(
            items=[MessageListItem.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self, message_id: int, payload: MessageUpdateRequest
    ) -> MessageUpdateResponse:
        """Обновляет сообщение."""
        values = payload.model_dump(exclude_unset=True)
        record = await message_repository.update(self._session, message_id, values)
        if record is None:
            raise EntityNotFoundError('Сообщение не найдено')
        return MessageUpdateResponse.model_validate(record)

    async def delete(self, message_id: int) -> None:
        """Удаляет сообщение."""
        deleted = await message_repository.delete(self._session, message_id)
        if not deleted:
            raise EntityNotFoundError('Сообщение не найдено')


def get_message_service(session: AsyncSession = Depends(get_session)) -> MessageService:
    """Dependency: сервис сообщений с сессией запроса."""
    return MessageService(session)
