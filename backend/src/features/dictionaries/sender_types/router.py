"""HTTP API справочника типов отправителя."""

from fastapi import APIRouter, Depends, Query

from src.features.dictionaries.sender_types.schemas import (
    SenderTypeGetResponse,
    SenderTypeListResponse,
)
from src.features.dictionaries.sender_types.service import (
    SenderTypeService,
    get_sender_type_service,
)

router = APIRouter(prefix='/sender-types', tags=['Справочник: типы отправителя'])


@router.get('/', response_model=SenderTypeListResponse)
async def list_sender_types(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: SenderTypeService = Depends(get_sender_type_service),
) -> SenderTypeListResponse:
    """Возвращает постраничный список типов отправителя."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{sender_type_id}', response_model=SenderTypeGetResponse)
async def get_sender_type(
    sender_type_id: int,
    service: SenderTypeService = Depends(get_sender_type_service),
) -> SenderTypeGetResponse:
    """Возвращает тип отправителя по id."""
    return await service.get_one(sender_type_id)
