"""HTTP API справочника ролей."""

from fastapi import APIRouter, Depends, Query

from src.features.dictionaries.roles.schemas import RoleGetResponse, RoleListResponse
from src.features.dictionaries.roles.service import RoleService, get_role_service

router = APIRouter(prefix='/roles', tags=['Справочник: роли'])


@router.get('/', response_model=RoleListResponse)
async def list_roles(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: RoleService = Depends(get_role_service),
) -> RoleListResponse:
    """Возвращает постраничный список ролей."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{role_id}', response_model=RoleGetResponse)
async def get_role(
    role_id: int,
    service: RoleService = Depends(get_role_service),
) -> RoleGetResponse:
    """Возвращает роль по id."""
    return await service.get_one(role_id)
