"""Pydantic схемы справочника типов отправителя."""

from pydantic import BaseModel


class SenderTypeListItem(BaseModel):
    """Элемент списка для эндпоинта list_sender_types."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}


class SenderTypeListResponse(BaseModel):
    """Ответ эндпоинта GET /sender-types — постраничный список."""

    items: list[SenderTypeListItem]
    total: int
    page: int
    page_size: int


class SenderTypeGetResponse(BaseModel):
    """Ответ эндпоинта GET /sender-types/{id} — одно значение."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}
