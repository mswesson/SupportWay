"""Pydantic схемы фичи операторов."""

from pydantic import BaseModel


class OperatorStatusRequest(BaseModel):
    """Тело запроса POST /operators/status."""

    online: bool


class OperatorStatusResponse(BaseModel):
    """Ответ эндпоинта POST /operators/status."""

    operator_id: int
    status: str


class OperatorMeResponse(BaseModel):
    """Ответ эндпоинта GET /operators/me."""

    operator_id: int
    status: str
    active_chats_count: int
