"""Pydantic схемы сценариев жизненного цикла чата."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    """Тело запроса POST /chats — создание обращения внешним приложением."""

    full_name: str
    phone: str | None = None
    email: str | None = None
    external_id: str | None = None
    source: str | None = None


class CreateChatResponse(BaseModel):
    """Ответ эндпоинта POST /chats."""

    chat_id: int
    client_token: str
    # reserved — оператор найден; no_operators_available — операторов нет
    status: str


class AcceptChatResponse(BaseModel):
    """Ответ эндпоинта POST /chats/{id}/accept."""

    chat_id: int
    status: str


class RejectChatResponse(BaseModel):
    """Ответ эндпоинта POST /chats/{id}/reject."""

    chat_id: int
    status: str


class CloseChatRequest(BaseModel):
    """Тело запроса POST /chats/{id}/close."""

    closed_by: Literal['operator', 'client', 'system'] = 'operator'


class CloseChatResponse(BaseModel):
    """Ответ эндпоинта POST /chats/{id}/close."""

    chat_id: int
    status: str


class RatingRequest(BaseModel):
    """Тело запроса POST /chats/{id}/rating."""

    rating: int = Field(ge=1, le=5)


class RatingResponse(BaseModel):
    """Ответ эндпоинта POST /chats/{id}/rating."""

    chat_id: int
    rating: int


class HistoryMessageItem(BaseModel):
    """Элемент истории сообщений."""

    id: int
    sender_type_id: int
    sender_id: int | None
    text: str
    created_at: datetime

    model_config = {'from_attributes': True}


class HistoryResponse(BaseModel):
    """Ответ эндпоинта GET /chats/{id}/history."""

    chat_id: int
    items: list[HistoryMessageItem]


class PendingClientInfo(BaseModel):
    """Данные клиента в элементе очереди."""

    full_name: str
    phone: str | None
    email: str | None
    source: str | None = None
    external_id: str | None = None


class PendingChatItem(BaseModel):
    """Элемент списка ожидающих чатов."""

    chat_id: int
    client: PendingClientInfo
    created_at: datetime


class PendingChatsResponse(BaseModel):
    """Ответ эндпоинта GET /chats/pending — очередь ожидающих чатов (постранично)."""

    items: list[PendingChatItem]
    total: int
    page: int
    page_size: int


class TakeChatResponse(BaseModel):
    """Ответ эндпоинта POST /chats/{id}/take."""

    chat_id: int
    status: str


class MyChatItem(BaseModel):
    """Элемент списка чатов оператора."""

    chat_id: int
    status: str
    client: PendingClientInfo
    created_at: datetime
    accepted_at: datetime | None


class MyChatsResponse(BaseModel):
    """Ответ эндпоинта GET /chats/my — чаты текущего оператора (reserved + active)."""

    items: list[MyChatItem]


class ClosedChatItem(BaseModel):
    """Элемент списка завершённых чатов оператора."""

    chat_id: int
    status: str
    client: PendingClientInfo
    created_at: datetime
    closed_at: datetime | None
    rating: int | None


class ClosedChatsResponse(BaseModel):
    """Ответ эндпоинта GET /chats/closed — завершённые чаты оператора (постранично)."""

    items: list[ClosedChatItem]
    total: int
    page: int
    page_size: int
