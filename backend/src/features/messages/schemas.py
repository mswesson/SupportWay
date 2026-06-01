"""Pydantic схемы фичи сообщений (CRUD)."""

from datetime import datetime

from pydantic import BaseModel


class MessageCreateRequest(BaseModel):
    """Тело запроса POST /messages."""

    chat_session_id: int
    sender_type_id: int
    text: str
    sender_id: int | None = None


class MessageUpdateRequest(BaseModel):
    """Тело запроса PUT /messages/{id}. Все поля опциональны."""

    text: str | None = None


class MessageCreateResponse(BaseModel):
    """Ответ эндпоинта POST /messages."""

    id: int
    chat_session_id: int
    sender_type_id: int
    sender_id: int | None
    text: str
    created_at: datetime

    model_config = {'from_attributes': True}


class MessageGetResponse(BaseModel):
    """Ответ эндпоинта GET /messages/{id}."""

    id: int
    chat_session_id: int
    sender_type_id: int
    sender_id: int | None
    text: str
    created_at: datetime

    model_config = {'from_attributes': True}


class MessageUpdateResponse(BaseModel):
    """Ответ эндпоинта PUT /messages/{id}."""

    id: int
    chat_session_id: int
    sender_type_id: int
    sender_id: int | None
    text: str
    created_at: datetime

    model_config = {'from_attributes': True}


class MessageListItem(BaseModel):
    """Элемент списка для эндпоинта GET /messages."""

    id: int
    chat_session_id: int
    sender_type_id: int
    sender_id: int | None
    text: str
    created_at: datetime

    model_config = {'from_attributes': True}


class MessageListResponse(BaseModel):
    """Ответ эндпоинта GET /messages — постраничный список."""

    items: list[MessageListItem]
    total: int
    page: int
    page_size: int
