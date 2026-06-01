"""Сервис справочника ролей."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.features.dictionaries.base import BaseDictionaryService
from src.features.dictionaries.roles.repository import role_repository
from src.features.dictionaries.roles.schemas import (
    RoleGetResponse,
    RoleListItem,
    RoleListResponse,
)


class RoleService(BaseDictionaryService):
    """Чтение справочника ролей."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, role_repository, RoleListItem, RoleListResponse, RoleGetResponse)


def get_role_service(session: AsyncSession = Depends(get_session)) -> RoleService:
    """Dependency: сервис справочника ролей с сессией запроса."""
    return RoleService(session)
