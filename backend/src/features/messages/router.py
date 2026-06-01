"""HTTP API сообщений (CRUD для чтения/модерации; боевая отправка — через WebSocket)."""

from fastapi import APIRouter, Depends, Query, status

from src.features.messages.schemas import (
    MessageCreateRequest,
    MessageCreateResponse,
    MessageGetResponse,
    MessageListResponse,
    MessageUpdateRequest,
    MessageUpdateResponse,
)
from src.features.messages.service import MessageService, get_message_service

router = APIRouter(prefix='/messages', tags=['Сообщения'])


@router.post('/', response_model=MessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreateRequest,
    service: MessageService = Depends(get_message_service),
) -> MessageCreateResponse:
    """Создаёт сообщение (административно; обмен в чате идёт через WebSocket)."""
    return await service.create(payload)


@router.get('/', response_model=MessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    """Возвращает постраничный список сообщений."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{message_id}', response_model=MessageGetResponse)
async def get_message(
    message_id: int,
    service: MessageService = Depends(get_message_service),
) -> MessageGetResponse:
    """Возвращает сообщение по id."""
    return await service.get_one(message_id)


@router.put('/{message_id}', response_model=MessageUpdateResponse)
async def update_message(
    message_id: int,
    payload: MessageUpdateRequest,
    service: MessageService = Depends(get_message_service),
) -> MessageUpdateResponse:
    """Обновляет сообщение."""
    return await service.update(message_id, payload)


@router.delete('/{message_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    service: MessageService = Depends(get_message_service),
) -> None:
    """Удаляет сообщение."""
    await service.delete(message_id)
