"""Pydantic схемы фичи клиентов (CRUD)."""

from datetime import datetime

from pydantic import BaseModel


class ClientCreateRequest(BaseModel):
    """Тело запроса POST /clients."""

    full_name: str
    phone: str | None = None
    email: str | None = None
    external_id: str | None = None
    source: str | None = None


class ClientUpdateRequest(BaseModel):
    """Тело запроса PUT /clients/{id}. Все поля опциональны."""

    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    external_id: str | None = None
    source: str | None = None


class ClientCreateResponse(BaseModel):
    """Ответ эндпоинта POST /clients."""

    id: int
    full_name: str
    phone: str | None
    email: str | None
    external_id: str | None
    source: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class ClientGetResponse(BaseModel):
    """Ответ эндпоинта GET /clients/{id}."""

    id: int
    full_name: str
    phone: str | None
    email: str | None
    external_id: str | None
    source: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class ClientUpdateResponse(BaseModel):
    """Ответ эндпоинта PUT /clients/{id}."""

    id: int
    full_name: str
    phone: str | None
    email: str | None
    external_id: str | None
    source: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class ClientListItem(BaseModel):
    """Элемент списка для эндпоинта GET /clients."""

    id: int
    full_name: str
    phone: str | None
    email: str | None
    external_id: str | None
    source: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class ClientListResponse(BaseModel):
    """Ответ эндпоинта GET /clients — постраничный список."""

    items: list[ClientListItem]
    total: int
    page: int
    page_size: int
