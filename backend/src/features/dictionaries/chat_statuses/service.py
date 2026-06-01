"""Сервис справочника статусов чата."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.features.dictionaries.base import BaseDictionaryService
from src.features.dictionaries.chat_statuses.repository import chat_status_repository
from src.features.dictionaries.chat_statuses.schemas import (
    ChatStatusGetResponse,
    ChatStatusListItem,
    ChatStatusListResponse,
)


class ChatStatusService(BaseDictionaryService):
    """Чтение справочника статусов чата."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            chat_status_repository,
            ChatStatusListItem,
            ChatStatusListResponse,
            ChatStatusGetResponse,
        )


def get_chat_status_service(session: AsyncSession = Depends(get_session)) -> ChatStatusService:
    """Dependency: сервис справочника статусов чата."""
    return ChatStatusService(session)
