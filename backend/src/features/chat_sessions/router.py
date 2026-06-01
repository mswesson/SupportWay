"""HTTP API сессий чата (CRUD для чтения/администрирования)."""

from fastapi import APIRouter, Depends, Query, status

from src.features.chat_sessions.schemas import (
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    ChatSessionGetResponse,
    ChatSessionListResponse,
    ChatSessionUpdateRequest,
    ChatSessionUpdateResponse,
)
from src.features.chat_sessions.service import (
    ChatSessionService,
    get_chat_session_service,
)

router = APIRouter(prefix='/chat-sessions', tags=['Сессии чата'])


@router.post('/', response_model=ChatSessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
    service: ChatSessionService = Depends(get_chat_session_service),
) -> ChatSessionCreateResponse:
    """Создаёт сессию чата."""
    return await service.create(payload)


@router.get('/', response_model=ChatSessionListResponse)
async def list_chat_sessions(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: ChatSessionService = Depends(get_chat_session_service),
) -> ChatSessionListResponse:
    """Возвращает постраничный список сессий чата."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{session_id}', response_model=ChatSessionGetResponse)
async def get_chat_session(
    session_id: int,
    service: ChatSessionService = Depends(get_chat_session_service),
) -> ChatSessionGetResponse:
    """Возвращает сессию чата по id."""
    return await service.get_one(session_id)


@router.put('/{session_id}', response_model=ChatSessionUpdateResponse)
async def update_chat_session(
    session_id: int,
    payload: ChatSessionUpdateRequest,
    service: ChatSessionService = Depends(get_chat_session_service),
) -> ChatSessionUpdateResponse:
    """Обновляет сессию чата."""
    return await service.update(session_id, payload)


@router.delete('/{session_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: int,
    service: ChatSessionService = Depends(get_chat_session_service),
) -> None:
    """Удаляет сессию чата."""
    await service.delete(session_id)
