"""Pydantic схемы справочника инициаторов закрытия чата."""

from pydantic import BaseModel


class ClosedByTypeListItem(BaseModel):
    """Элемент списка для эндпоинта list_closed_by_types."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}


class ClosedByTypeListResponse(BaseModel):
    """Ответ эндпоинта GET /closed-by-types — постраничный список."""

    items: list[ClosedByTypeListItem]
    total: int
    page: int
    page_size: int


class ClosedByTypeGetResponse(BaseModel):
    """Ответ эндпоинта GET /closed-by-types/{id} — одно значение."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}
