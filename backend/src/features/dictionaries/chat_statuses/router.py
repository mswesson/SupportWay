"""HTTP API справочника статусов чата."""

from fastapi import APIRouter, Depends, Query

from src.features.dictionaries.chat_statuses.schemas import (
    ChatStatusGetResponse,
    ChatStatusListResponse,
)
from src.features.dictionaries.chat_statuses.service import (
    ChatStatusService,
    get_chat_status_service,
)

router = APIRouter(prefix='/chat-statuses', tags=['Справочник: статусы чата'])


@router.get('/', response_model=ChatStatusListResponse)
async def list_chat_statuses(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: ChatStatusService = Depends(get_chat_status_service),
) -> ChatStatusListResponse:
    """Возвращает постраничный список статусов чата."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{status_id}', response_model=ChatStatusGetResponse)
async def get_chat_status(
    status_id: int,
    service: ChatStatusService = Depends(get_chat_status_service),
) -> ChatStatusGetResponse:
    """Возвращает статус чата по id."""
    return await service.get_one(status_id)
