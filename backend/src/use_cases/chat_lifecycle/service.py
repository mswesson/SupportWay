"""Сквозная бизнес-логика жизненного цикла чата.

Оркестрирует фичи: clients, chat_sessions, messages (БД), operators (Redis) и
рассылку WebSocket-эвентов через ws_manager.
"""

import secrets
from datetime import datetime
from typing import Any

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import (
    AuthorizationError,
    EntityNotFoundError,
    InvalidChatStateError,
)
from src.core.redis import get_redis
from src.core.security import issue_client_token
from src.core.ws_manager import ws_manager
from src.features.chat_sessions.repository import chat_session_repository
from src.features.clients.repository import client_repository
from src.features.dictionaries.chat_statuses.models import ChatStatus
from src.features.dictionaries.closed_by_types.models import ClosedByType
from src.features.dictionaries.sender_types.models import SenderType
from src.features.messages.repository import message_repository
from src.features.operators.repository import operator_presence_repository
from src.use_cases.chat_lifecycle.schemas import (
    AcceptChatResponse,
    ClosedChatItem,
    ClosedChatsResponse,
    CloseChatResponse,
    CreateChatRequest,
    CreateChatResponse,
    HistoryMessageItem,
    HistoryResponse,
    MyChatItem,
    MyChatsResponse,
    PendingChatItem,
    PendingChatsResponse,
    PendingClientInfo,
    RatingResponse,
    RejectChatResponse,
    TakeChatResponse,
)

# Коды справочника статусов чата
_STATUS_PENDING = 'pending'
_STATUS_RESERVED = 'reserved'
_STATUS_ACTIVE = 'active'
_STATUS_CLOSED = 'closed'

# Коды справочника типов отправителя
SENDER_CLIENT = 'client'
SENDER_OPERATOR = 'operator'


class ChatLifecycleService:
    """Сервис сценариев жизненного цикла чата."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis

    # --- Вспомогательное: код справочника -> id ---

    async def _code_to_id(self, model: type[Any], code: str) -> int:
        """Возвращает id значения справочника по его коду."""
        result = await self._session.execute(select(model.id).where(model.code == code))
        value = result.scalar_one_or_none()
        if value is None:
            raise EntityNotFoundError(f'Значение справочника не найдено: {code}')
        return value

    # --- Вспомогательное: данные клиента для ответов и эвентов ---

    @staticmethod
    def _client_info(client: Any) -> PendingClientInfo:
        """Собирает данные клиента для ответов REST (включая проект и внешний id)."""
        return PendingClientInfo(
            full_name=client.full_name if client else '',
            phone=client.phone if client else None,
            email=client.email if client else None,
            source=client.source if client else None,
            external_id=client.external_id if client else None,
        )

    @staticmethod
    def _client_event(client: Any) -> dict[str, Any]:
        """Собирает данные клиента для WebSocket-эвента chat_assigned."""
        return {
            'full_name': client.full_name if client else None,
            'phone': client.phone if client else None,
            'email': client.email if client else None,
            'source': client.source if client else None,
            'external_id': client.external_id if client else None,
        }

    # --- Создание чата с авто-резервом оператора ---

    async def create_chat(self, payload: CreateChatRequest) -> CreateChatResponse:
        """Создаёт клиента и сессию, выдаёт client_token и сразу резервирует оператора."""
        pending_id = await self._code_to_id(ChatStatus, _STATUS_PENDING)
        client = await client_repository.get_or_create_by_external(
            self._session,
            {
                'full_name': payload.full_name,
                'phone': payload.phone,
                'email': payload.email,
                'external_id': payload.external_id,
                'source': payload.source,
            },
        )
        chat = await chat_session_repository.create(
            self._session, {'client_id': client.id, 'status_id': pending_id}
        )

        token = secrets.token_urlsafe(32)
        await issue_client_token(self._redis, chat.id, token)

        assigned = await self._try_assign(chat.id)
        status = _STATUS_RESERVED if assigned else 'no_operators_available'
        return CreateChatResponse(chat_id=chat.id, client_token=token, status=status)

    async def _try_assign(self, chat_id: int) -> bool:
        """Находит наименее загруженного оператора (не из чёрного списка) и резервирует чат."""
        chat = await chat_session_repository.get(self._session, chat_id)
        if chat is None:
            raise EntityNotFoundError('Сессия чата не найдена')

        rejected = await operator_presence_repository.get_rejected(self._redis, chat_id)
        operator_id = await operator_presence_repository.find_available_operator(
            self._redis, rejected
        )
        if operator_id is None:
            return False

        reserved_id = await self._code_to_id(ChatStatus, _STATUS_RESERVED)
        await chat_session_repository.update(
            self._session, chat_id, {'operator_id': operator_id, 'status_id': reserved_id}
        )

        client = await client_repository.get(self._session, chat.client_id)
        await ws_manager.send_to_operator(
            operator_id,
            'chat_assigned',
            {'chat_id': chat_id, 'client': self._client_event(client)},
        )
        return True

    # --- Очередь ожидающих чатов (pull-модель) ---

    async def list_pending(
        self, page: int = 1, page_size: int = 20, search: str | None = None
    ) -> PendingChatsResponse:
        """Постранично возвращает очередь чатов в статусе pending (с поиском)."""
        pending_id = await self._code_to_id(ChatStatus, _STATUS_PENDING)
        chats, total = await chat_session_repository.list_pending_paginated(
            self._session, pending_id, offset=(page - 1) * page_size, limit=page_size, search=search
        )
        items: list[PendingChatItem] = []
        for chat in chats:
            client = await client_repository.get(self._session, chat.client_id)
            items.append(
                PendingChatItem(
                    chat_id=chat.id,
                    created_at=chat.created_at,
                    client=self._client_info(client),
                )
            )
        return PendingChatsResponse(items=items, total=total, page=page, page_size=page_size)

    async def list_my_chats(self, operator_id: int) -> MyChatsResponse:
        """Возвращает чаты оператора в статусах reserved и active."""
        reserved_id = await self._code_to_id(ChatStatus, _STATUS_RESERVED)
        active_id = await self._code_to_id(ChatStatus, _STATUS_ACTIVE)
        chats = await chat_session_repository.list_by_operator_and_statuses(
            self._session, operator_id, [reserved_id, active_id]
        )
        status_map = {reserved_id: _STATUS_RESERVED, active_id: _STATUS_ACTIVE}
        items: list[MyChatItem] = []
        for chat in chats:
            client = await client_repository.get(self._session, chat.client_id)
            items.append(
                MyChatItem(
                    chat_id=chat.id,
                    status=status_map[chat.status_id],
                    accepted_at=chat.accepted_at,
                    created_at=chat.created_at,
                    client=self._client_info(client),
                )
            )
        return MyChatsResponse(items=items)

    async def list_closed_chats(
        self, operator_id: int, page: int = 1, page_size: int = 20, search: str | None = None
    ) -> ClosedChatsResponse:
        """Постранично возвращает завершённые чаты оператора (с поиском)."""
        closed_id = await self._code_to_id(ChatStatus, _STATUS_CLOSED)
        chats, total = await chat_session_repository.list_closed_paginated(
            self._session,
            operator_id,
            closed_id,
            offset=(page - 1) * page_size,
            limit=page_size,
            search=search,
        )
        items: list[ClosedChatItem] = []
        for chat in chats:
            client = await client_repository.get(self._session, chat.client_id)
            items.append(
                ClosedChatItem(
                    chat_id=chat.id,
                    status=_STATUS_CLOSED,
                    created_at=chat.created_at,
                    closed_at=chat.closed_at,
                    rating=chat.rating,
                    client=self._client_info(client),
                )
            )
        return ClosedChatsResponse(items=items, total=total, page=page, page_size=page_size)

    async def take_chat(self, chat_id: int, operator_id: int) -> TakeChatResponse:
        """Оператор сам берёт ожидающий чат из очереди — чат резервируется за ним."""
        chat = await self._get_chat_or_raise(chat_id)
        pending_id = await self._code_to_id(ChatStatus, _STATUS_PENDING)
        if chat.status_id != pending_id:
            raise InvalidChatStateError('Чат уже не в очереди (не pending)')

        status = await operator_presence_repository.get_status(self._redis, operator_id)
        if status != 'online':
            raise InvalidChatStateError('Оператор не в сети')

        reserved_id = await self._code_to_id(ChatStatus, _STATUS_RESERVED)
        await chat_session_repository.update(
            self._session, chat_id, {'operator_id': operator_id, 'status_id': reserved_id}
        )

        client = await client_repository.get(self._session, chat.client_id)
        await ws_manager.send_to_operator(
            operator_id,
            'chat_assigned',
            {'chat_id': chat_id, 'client': self._client_event(client)},
        )
        return TakeChatResponse(chat_id=chat_id, status=_STATUS_RESERVED)

    # --- Принятие чата оператором ---

    async def accept_chat(self, chat_id: int, operator_id: int) -> AcceptChatResponse:
        """Переводит зарезервированный чат в active и увеличивает нагрузку оператора."""
        chat = await self._get_chat_or_raise(chat_id)
        reserved_id = await self._code_to_id(ChatStatus, _STATUS_RESERVED)
        if chat.status_id != reserved_id:
            raise InvalidChatStateError('Чат не в статусе reserved')
        if chat.operator_id != operator_id:
            raise AuthorizationError('Чат зарезервирован за другим оператором')

        active_id = await self._code_to_id(ChatStatus, _STATUS_ACTIVE)
        await chat_session_repository.update(
            self._session,
            chat_id,
            {'status_id': active_id, 'accepted_at': datetime.now()},
        )
        await operator_presence_repository.change_load(self._redis, operator_id, 1)
        return AcceptChatResponse(chat_id=chat_id, status=_STATUS_ACTIVE)

    # --- Отклонение чата оператором ---

    async def reject_chat(self, chat_id: int, operator_id: int) -> RejectChatResponse:
        """Возвращает чат в очередь, добавляет оператора в чёрный список и переназначает."""
        chat = await self._get_chat_or_raise(chat_id)
        reserved_id = await self._code_to_id(ChatStatus, _STATUS_RESERVED)
        if chat.status_id != reserved_id:
            raise InvalidChatStateError('Чат не в статусе reserved')
        if chat.operator_id != operator_id:
            raise AuthorizationError('Чат зарезервирован за другим оператором')

        await operator_presence_repository.add_rejected(self._redis, chat_id, operator_id)
        pending_id = await self._code_to_id(ChatStatus, _STATUS_PENDING)
        await chat_session_repository.update(
            self._session, chat_id, {'operator_id': None, 'status_id': pending_id}
        )

        assigned = await self._try_assign(chat_id)
        status = _STATUS_RESERVED if assigned else _STATUS_PENDING
        return RejectChatResponse(chat_id=chat_id, status=status)

    # --- Закрытие чата ---

    async def close_chat(self, chat_id: int, closed_by: str) -> CloseChatResponse:
        """Закрывает сессию, уменьшает нагрузку оператора и уведомляет обе стороны."""
        chat = await self._get_chat_or_raise(chat_id)
        closed_id = await self._code_to_id(ChatStatus, _STATUS_CLOSED)
        if chat.status_id == closed_id:
            return CloseChatResponse(chat_id=chat_id, status=_STATUS_CLOSED)

        active_id = await self._code_to_id(ChatStatus, _STATUS_ACTIVE)
        was_active = chat.status_id == active_id
        operator_id = chat.operator_id
        closed_by_id = await self._code_to_id(ClosedByType, closed_by)

        await chat_session_repository.update(
            self._session,
            chat_id,
            {'status_id': closed_id, 'closed_by_id': closed_by_id, 'closed_at': datetime.now()},
        )
        if was_active and operator_id is not None:
            await operator_presence_repository.change_load(self._redis, operator_id, -1)
        await operator_presence_repository.clear_rejected(self._redis, chat_id)

        await ws_manager.send_to_chat(chat_id, 'session_closed', {'chat_id': chat_id})
        if operator_id is not None:
            await ws_manager.send_to_operator(operator_id, 'session_closed', {'chat_id': chat_id})
        return CloseChatResponse(chat_id=chat_id, status=_STATUS_CLOSED)

    # --- Оценка качества клиентом ---

    async def set_rating(self, chat_id: int, rating: int) -> RatingResponse:
        """Сохраняет оценку клиента после закрытия чата."""
        chat = await self._get_chat_or_raise(chat_id)
        closed_id = await self._code_to_id(ChatStatus, _STATUS_CLOSED)
        if chat.status_id != closed_id:
            raise InvalidChatStateError('Оценку можно поставить только закрытому чату')
        await chat_session_repository.update(self._session, chat_id, {'rating': rating})
        return RatingResponse(chat_id=chat_id, rating=rating)

    # --- История сообщений ---

    async def get_history(self, chat_id: int) -> HistoryResponse:
        """Возвращает все сообщения чата по возрастанию времени."""
        await self._get_chat_or_raise(chat_id)
        messages = await message_repository.get_by_chat(self._session, chat_id)
        return HistoryResponse(
            chat_id=chat_id,
            items=[HistoryMessageItem.model_validate(m) for m in messages],
        )

    # --- Обмен сообщениями (вызывается из WebSocket-обработчиков) ---

    async def relay_message(
        self, chat_id: int, sender: str, text: str, sender_id: int | None = None
    ) -> None:
        """Пишет сообщение в БД и рассылает new_message обеим сторонам.

        Закрытый чат недоступен никому. Оператор может писать только в active
        (сначала «Принять»). Клиент может писать уже в pending/reserved/active —
        так оператор после принятия видит контекст, а не пустое окно.
        """
        chat = await self._get_chat_or_raise(chat_id)
        closed_id = await self._code_to_id(ChatStatus, _STATUS_CLOSED)
        if chat.status_id == closed_id:
            raise InvalidChatStateError('Чат закрыт')
        if sender == SENDER_OPERATOR:
            active_id = await self._code_to_id(ChatStatus, _STATUS_ACTIVE)
            if chat.status_id != active_id:
                raise InvalidChatStateError('Сначала примите чат')

        sender_type_id = await self._code_to_id(SenderType, sender)
        message = await message_repository.create(
            self._session,
            {
                'chat_session_id': chat_id,
                'sender_type_id': sender_type_id,
                'sender_id': sender_id,
                'text': text,
            },
        )
        payload = {
            'chat_id': chat_id,
            'message_id': message.id,
            'sender': sender,
            'sender_id': sender_id,
            'text': text,
            'created_at': message.created_at.isoformat(),
        }
        await ws_manager.send_to_chat(chat_id, 'new_message', payload)
        if chat.operator_id is not None:
            await ws_manager.send_to_operator(chat.operator_id, 'new_message', payload)

    async def _get_chat_or_raise(self, chat_id: int):
        chat = await chat_session_repository.get(self._session, chat_id)
        if chat is None:
            raise EntityNotFoundError('Сессия чата не найдена')
        return chat


def get_chat_lifecycle_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> ChatLifecycleService:
    """Dependency: сервис жизненного цикла чата с сессией и Redis запроса."""
    return ChatLifecycleService(session, redis)
