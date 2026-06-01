"""HTTP API справочника инициаторов закрытия чата."""

from fastapi import APIRouter, Depends, Query

from src.features.dictionaries.closed_by_types.schemas import (
    ClosedByTypeGetResponse,
    ClosedByTypeListResponse,
)
from src.features.dictionaries.closed_by_types.service import (
    ClosedByTypeService,
    get_closed_by_type_service,
)

router = APIRouter(prefix='/closed-by-types', tags=['Справочник: инициаторы закрытия'])


@router.get('/', response_model=ClosedByTypeListResponse)
async def list_closed_by_types(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: ClosedByTypeService = Depends(get_closed_by_type_service),
) -> ClosedByTypeListResponse:
    """Возвращает постраничный список инициаторов закрытия."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{closed_by_type_id}', response_model=ClosedByTypeGetResponse)
async def get_closed_by_type(
    closed_by_type_id: int,
    service: ClosedByTypeService = Depends(get_closed_by_type_service),
) -> ClosedByTypeGetResponse:
    """Возвращает инициатора закрытия по id."""
    return await service.get_one(closed_by_type_id)
