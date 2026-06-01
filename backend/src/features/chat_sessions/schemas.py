"""Pydantic схемы фичи сессий чата (CRUD)."""

from datetime import datetime

from pydantic import BaseModel


class ChatSessionCreateRequest(BaseModel):
    """Тело запроса POST /chat-sessions."""

    client_id: int
    status_id: int
    operator_id: int | None = None


class ChatSessionUpdateRequest(BaseModel):
    """Тело запроса PUT /chat-sessions/{id}. Все поля опциональны."""

    operator_id: int | None = None
    status_id: int | None = None
    closed_by_id: int | None = None
    rating: int | None = None
    accepted_at: datetime | None = None
    closed_at: datetime | None = None


class ChatSessionCreateResponse(BaseModel):
    """Ответ эндпоинта POST /chat-sessions."""

    id: int
    client_id: int
    operator_id: int | None
    status_id: int
    created_at: datetime

    model_config = {'from_attributes': True}


class ChatSessionGetResponse(BaseModel):
    """Ответ эндпоинта GET /chat-sessions/{id}."""

    id: int
    client_id: int
    operator_id: int | None
    status_id: int
    closed_by_id: int | None
    rating: int | None
    created_at: datetime
    accepted_at: datetime | None
    closed_at: datetime | None

    model_config = {'from_attributes': True}


class ChatSessionUpdateResponse(BaseModel):
    """Ответ эндпоинта PUT /chat-sessions/{id}."""

    id: int
    client_id: int
    operator_id: int | None
    status_id: int
    closed_by_id: int | None
    rating: int | None
    created_at: datetime
    accepted_at: datetime | None
    closed_at: datetime | None

    model_config = {'from_attributes': True}


class ChatSessionListItem(BaseModel):
    """Элемент списка для эндпоинта GET /chat-sessions."""

    id: int
    client_id: int
    operator_id: int | None
    status_id: int
    created_at: datetime

    model_config = {'from_attributes': True}


class ChatSessionListResponse(BaseModel):
    """Ответ эндпоинта GET /chat-sessions — постраничный список."""

    items: list[ChatSessionListItem]
    total: int
    page: int
    page_size: int
