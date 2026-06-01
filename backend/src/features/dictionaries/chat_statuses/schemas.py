"""Pydantic схемы справочника статусов чата."""

from pydantic import BaseModel


class ChatStatusListItem(BaseModel):
    """Элемент списка для эндпоинта list_chat_statuses."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}


class ChatStatusListResponse(BaseModel):
    """Ответ эндпоинта GET /chat-statuses — постраничный список."""

    items: list[ChatStatusListItem]
    total: int
    page: int
    page_size: int


class ChatStatusGetResponse(BaseModel):
    """Ответ эндпоинта GET /chat-statuses/{id} — одно значение."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}
