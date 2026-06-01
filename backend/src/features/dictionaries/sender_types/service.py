"""Сервис справочника типов отправителя."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.features.dictionaries.base import BaseDictionaryService
from src.features.dictionaries.sender_types.repository import sender_type_repository
from src.features.dictionaries.sender_types.schemas import (
    SenderTypeGetResponse,
    SenderTypeListItem,
    SenderTypeListResponse,
)


class SenderTypeService(BaseDictionaryService):
    """Чтение справочника типов отправителя."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            sender_type_repository,
            SenderTypeListItem,
            SenderTypeListResponse,
            SenderTypeGetResponse,
        )


def get_sender_type_service(session: AsyncSession = Depends(get_session)) -> SenderTypeService:
    """Dependency: сервис справочника типов отправителя."""
    return SenderTypeService(session)
