"""Pydantic схемы фичи пользователей (CRUD + авторизация)."""

from pydantic import BaseModel

# --- CRUD ---


class UserCreateRequest(BaseModel):
    """Тело запроса POST /users."""

    full_name: str
    password: str
    role_id: int


class UserUpdateRequest(BaseModel):
    """Тело запроса PUT /users/{id}. Все поля опциональны."""

    full_name: str | None = None
    password: str | None = None
    role_id: int | None = None


class UserCreateResponse(BaseModel):
    """Ответ эндпоинта POST /users."""

    id: int
    full_name: str
    role_id: int

    model_config = {'from_attributes': True}


class UserGetResponse(BaseModel):
    """Ответ эндпоинта GET /users/{id}."""

    id: int
    full_name: str
    role_id: int

    model_config = {'from_attributes': True}


class UserUpdateResponse(BaseModel):
    """Ответ эндпоинта PUT /users/{id}."""

    id: int
    full_name: str
    role_id: int

    model_config = {'from_attributes': True}


class UserListItem(BaseModel):
    """Элемент списка для эндпоинта GET /users."""

    id: int
    full_name: str
    role_id: int

    model_config = {'from_attributes': True}


class UserListResponse(BaseModel):
    """Ответ эндпоинта GET /users — постраничный список."""

    items: list[UserListItem]
    total: int
    page: int
    page_size: int


# --- Авторизация ---


class LoginRequest(BaseModel):
    """Тело запроса POST /auth/login."""

    full_name: str
    password: str


class LoginResponse(BaseModel):
    """Ответ эндпоинта POST /auth/login."""

    access_token: str
    token_type: str = 'bearer'
