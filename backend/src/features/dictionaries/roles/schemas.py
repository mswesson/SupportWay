"""Pydantic схемы справочника ролей."""

from pydantic import BaseModel


class RoleListItem(BaseModel):
    """Элемент списка для эндпоинта list_roles."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}


class RoleListResponse(BaseModel):
    """Ответ эндпоинта GET /roles — постраничный список."""

    items: list[RoleListItem]
    total: int
    page: int
    page_size: int


class RoleGetResponse(BaseModel):
    """Ответ эндпоинта GET /roles/{id} — одно значение."""

    id: int
    code: str
    name: str

    model_config = {'from_attributes': True}
