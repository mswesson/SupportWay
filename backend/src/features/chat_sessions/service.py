"""Бизнес-логика фичи сессий чата (CRUD)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import EntityNotFoundError
from src.features.chat_sessions.repository import chat_session_repository
from src.features.chat_sessions.schemas import (
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    ChatSessionGetResponse,
    ChatSessionListItem,
    ChatSessionListResponse,
    ChatSessionUpdateRequest,
    ChatSessionUpdateResponse,
)


class ChatSessionService:
    """Сервис управления сессиями чата (чтение/администрирование)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: ChatSessionCreateRequest) -> ChatSessionCreateResponse:
        """Создаёт сессию чата."""
        record = await chat_session_repository.create(self._session, payload.model_dump())
        return ChatSessionCreateResponse.model_validate(record)

    async def get_one(self, session_id: int) -> ChatSessionGetResponse:
        """Возвращает сессию по id."""
        record = await chat_session_repository.get(self._session, session_id)
        if record is None:
            raise EntityNotFoundError('Сессия чата не найдена')
        return ChatSessionGetResponse.model_validate(record)

    async def get_list(self, page: int, page_size: int) -> ChatSessionListResponse:
        """Возвращает постраничный список сессий."""
        offset = (page - 1) * page_size
        records, total = await chat_session_repository.get_list(self._session, offset, page_size)
        return ChatSessionListResponse(
            items=[ChatSessionListItem.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self, session_id: int, payload: ChatSessionUpdateRequest
    ) -> ChatSessionUpdateResponse:
        """Обновляет сессию."""
        values = payload.model_dump(exclude_unset=True)
        record = await chat_session_repository.update(self._session, session_id, values)
        if record is None:
            raise EntityNotFoundError('Сессия чата не найдена')
        return ChatSessionUpdateResponse.model_validate(record)

    async def delete(self, session_id: int) -> None:
        """Удаляет сессию."""
        deleted = await chat_session_repository.delete(self._session, session_id)
        if not deleted:
            raise EntityNotFoundError('Сессия чата не найдена')


def get_chat_session_service(session: AsyncSession = Depends(get_session)) -> ChatSessionService:
    """Dependency: сервис сессий чата с сессией запроса."""
    return ChatSessionService(session)
