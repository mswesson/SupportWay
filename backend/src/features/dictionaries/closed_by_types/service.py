"""Сервис справочника инициаторов закрытия чата."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.features.dictionaries.base import BaseDictionaryService
from src.features.dictionaries.closed_by_types.repository import closed_by_type_repository
from src.features.dictionaries.closed_by_types.schemas import (
    ClosedByTypeGetResponse,
    ClosedByTypeListItem,
    ClosedByTypeListResponse,
)


class ClosedByTypeService(BaseDictionaryService):
    """Чтение справочника инициаторов закрытия чата."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            closed_by_type_repository,
            ClosedByTypeListItem,
            ClosedByTypeListResponse,
            ClosedByTypeGetResponse,
        )


def get_closed_by_type_service(
    session: AsyncSession = Depends(get_session),
) -> ClosedByTypeService:
    """Dependency: сервис справочника инициаторов закрытия чата."""
    return ClosedByTypeService(session)
