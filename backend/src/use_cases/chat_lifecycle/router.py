"""REST и WebSocket API жизненного цикла чата.

REST — все действия с состоянием (создание, accept/reject/close/rating, история).
WebSocket — только обмен сообщениями и доставка эвентов.
"""

import asyncio

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger

from src.core.database import async_session_factory
from src.core.exceptions import AuthorizationError, DomainError
from src.core.redis import redis_client
from src.core.security import (
    CurrentOperator,
    authenticate_ws_operator,
    get_current_operator,
    verify_client_token,
    verify_integration_key,
)
from src.core.ws_manager import ws_manager
from src.use_cases.chat_lifecycle.schemas import (
    AcceptChatResponse,
    CloseChatRequest,
    CloseChatResponse,
    ClosedChatsResponse,
    CreateChatRequest,
    CreateChatResponse,
    HistoryResponse,
    MyChatsResponse,
    RatingRequest,
    RatingResponse,
    RejectChatResponse,
)
from src.use_cases.chat_lifecycle.service import (
    SENDER_CLIENT,
    SENDER_OPERATOR,
    ChatLifecycleService,
    get_chat_lifecycle_service,
)

# Код закрытия WebSocket при ошибке авторизации
_WS_UNAUTHORIZED = 4401
# Интервал heartbeat-пинга (секунды)
_HEARTBEAT_INTERVAL = 15

_TAG_OPERATOR = 'Чат — Оператор'
_TAG_CLIENT = 'Чат — Клиент'

router = APIRouter(prefix='/chats')
ws_router = APIRouter()


# ============================ REST ============================


@router.post('/', response_model=CreateChatResponse, tags=[_TAG_CLIENT])
async def create_chat(
    payload: CreateChatRequest,
    x_integration_key: str | None = Header(default=None),
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> CreateChatResponse:
    """Создаёт обращение и автоматически резервирует свободного оператора."""
    verify_integration_key(x_integration_key)
    return await service.create_chat(payload)


@router.get('/my', response_model=MyChatsResponse, tags=[_TAG_OPERATOR])
async def list_my_chats(
    current: CurrentOperator = Depends(get_current_operator),
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> MyChatsResponse:
    """Возвращает активные чаты текущего оператора (статусы reserved и active)."""
    return await service.list_my_chats(current.id)


@router.get('/closed', response_model=ClosedChatsResponse, tags=[_TAG_OPERATOR])
async def list_closed(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(20, ge=1, le=100, description='Записей на странице'),
    search: str | None = Query(None, description='Поиск по имени клиента или id чата'),
    current: CurrentOperator = Depends(get_current_operator),
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> ClosedChatsResponse:
    """Возвращает завершённые чаты текущего оператора, постранично, с поиском."""
    return await service.list_closed_chats(
        current.id, page=page, page_size=page_size, search=search
    )


@router.post('/{chat_id}/accept', response_model=AcceptChatResponse, tags=[_TAG_OPERATOR])
async def accept_chat(
    chat_id: int,
    current: CurrentOperator = Depends(get_current_operator),
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> AcceptChatResponse:
    """Оператор принимает зарезервированный чат."""
    return await service.accept_chat(chat_id, operator_id=current.id)


@router.post('/{chat_id}/reject', response_model=RejectChatResponse, tags=[_TAG_OPERATOR])
async def reject_chat(
    chat_id: int,
    current: CurrentOperator = Depends(get_current_operator),
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> RejectChatResponse:
    """Оператор отклоняет чат — он переназначается следующему свободному."""
    return await service.reject_chat(chat_id, operator_id=current.id)


_BOTH_TAGS = [_TAG_OPERATOR, _TAG_CLIENT]


@router.post('/{chat_id}/close', response_model=CloseChatResponse, tags=_BOTH_TAGS)
async def close_chat(
    chat_id: int,
    payload: CloseChatRequest,
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> CloseChatResponse:
    """Закрывает сессию (инициатор указывается в closed_by)."""
    return await service.close_chat(chat_id, closed_by=payload.closed_by)


@router.post('/{chat_id}/rating', response_model=RatingResponse, tags=[_TAG_CLIENT])
async def set_rating(
    chat_id: int,
    payload: RatingRequest,
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> RatingResponse:
    """Клиент ставит оценку качества после закрытия чата."""
    return await service.set_rating(chat_id, rating=payload.rating)


@router.get('/{chat_id}/history', response_model=HistoryResponse, tags=_BOTH_TAGS)
async def get_history(
    chat_id: int,
    service: ChatLifecycleService = Depends(get_chat_lifecycle_service),
) -> HistoryResponse:
    """Возвращает историю сообщений чата (для восстановления при обрыве связи)."""
    return await service.get_history(chat_id)


# ============================ WebSocket ============================


async def _heartbeat(websocket: WebSocket) -> None:
    """Шлёт ping каждые N секунд, чтобы держать соединение живым."""
    try:
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            await websocket.send_json({'type': 'ping'})
    except Exception:
        pass


async def _handle_incoming(chat_id: int, sender: str, data: dict, sender_id: int | None) -> None:
    """Обрабатывает входящее сообщение из WebSocket: пишет в БД и рассылает."""
    if data.get('type') != 'new_message':
        return
    text = data.get('text')
    if not text:
        return
    # На каждое сообщение — новая сессия (соединение долгоживущее).
    async with async_session_factory() as session:
        service = ChatLifecycleService(session, redis_client)
        await service.relay_message(chat_id, sender, text, sender_id=sender_id)


@ws_router.websocket('/ws/operator')
async def ws_operator(websocket: WebSocket, token: str = Query(...)) -> None:
    """WebSocket оператора. Авторизация: JWT в query-параметре token.

    Исходящие (сервер -> оператор):
      - chat_assigned  — оператору назначен/зарезервирован новый чат.
          {"type": "chat_assigned", "chat_id": int,
           "client": {"full_name": str|null, "phone": str|null, "email": str|null}}
      - new_message    — новое сообщение в одном из чатов оператора.
          {"type": "new_message", "chat_id": int, "message_id": int,
           "sender": "client"|"operator", "sender_id": int|null,
           "text": str, "created_at": str (ISO-8601)}
      - session_closed — чат закрыт любой из сторон (UI блокируется).
          {"type": "session_closed", "chat_id": int}
      - ping           — heartbeat сервера каждые 15 секунд.
          {"type": "ping"}
      - error          — ошибка обработки входящего сообщения (напр. чат не активен).
          {"type": "error", "detail": str}

    Входящие (оператор -> сервер):
      - new_message    — отправка сообщения в конкретный чат.
          {"type": "new_message", "chat_id": int, "text": str}
      - любые другие сообщения (включая ответ pong на ping) игнорируются.
    """
    try:
        operator = authenticate_ws_operator(token)
    except AuthorizationError:
        await websocket.close(code=_WS_UNAUTHORIZED)
        return

    await ws_manager.connect_operator(operator.id, websocket)
    ping_task = asyncio.create_task(_heartbeat(websocket))
    try:
        while True:
            data = await websocket.receive_json()
            try:
                await _handle_incoming(
                    chat_id=data.get('chat_id'),
                    sender=SENDER_OPERATOR,
                    data=data,
                    sender_id=operator.id,
                )
            except DomainError as exc:
                await websocket.send_json({'type': 'error', 'detail': str(exc)})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception('Ошибка в WebSocket оператора', operator_id=operator.id)
    finally:
        ping_task.cancel()
        ws_manager.disconnect_operator(operator.id)


@ws_router.websocket('/ws/client/{chat_id}')
async def ws_client(websocket: WebSocket, chat_id: int, token: str = Query(...)) -> None:
    """WebSocket клиентской стороны конкретного чата. Авторизация: client_token в query.

    Исходящие (сервер -> клиент):
      - new_message    — новое сообщение в этом чате.
          {"type": "new_message", "chat_id": int, "message_id": int,
           "sender": "client"|"operator", "sender_id": int|null,
           "text": str, "created_at": str (ISO-8601)}
      - session_closed — чат закрыт любой из сторон (UI блокируется).
          {"type": "session_closed", "chat_id": int}
      - ping           — heartbeat сервера каждые 15 секунд.
          {"type": "ping"}
      - error          — ошибка обработки входящего сообщения (напр. чат не активен).
          {"type": "error", "detail": str}
      Событие chat_assigned клиенту НЕ приходит — оно только для оператора.

    Входящие (клиент -> сервер):
      - new_message    — отправка сообщения (chat_id берётся из пути соединения).
          {"type": "new_message", "text": str}
      - любые другие сообщения (включая ответ pong на ping) игнорируются.
    """
    if not await verify_client_token(chat_id, token, redis_client):
        await websocket.close(code=_WS_UNAUTHORIZED)
        return

    await ws_manager.connect_client(chat_id, websocket)
    ping_task = asyncio.create_task(_heartbeat(websocket))
    try:
        while True:
            data = await websocket.receive_json()
            try:
                await _handle_incoming(
                    chat_id=chat_id,
                    sender=SENDER_CLIENT,
                    data=data,
                    sender_id=None,
                )
            except DomainError as exc:
                await websocket.send_json({'type': 'error', 'detail': str(exc)})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception('Ошибка в WebSocket клиента', chat_id=chat_id)
    finally:
        ping_task.cancel()
        ws_manager.disconnect_client(chat_id, websocket)
