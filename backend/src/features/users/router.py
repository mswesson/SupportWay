"""HTTP API пользователей: CRUD и авторизация.

CRUD пользователей оставлен без обязательной авторизации, чтобы можно было создать
первого оператора (bootstrap). При необходимости защиту добавляют через
Depends(get_current_operator).
"""

from fastapi import APIRouter, Depends, Query, status

from src.features.users.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserGetResponse,
    UserListResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from src.features.users.service import UserService, get_user_service

router = APIRouter(prefix='/users', tags=['Пользователи'])
auth_router = APIRouter(prefix='/auth', tags=['Авторизация'])


@router.post('/', response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    service: UserService = Depends(get_user_service),
) -> UserCreateResponse:
    """Создаёт пользователя."""
    return await service.create(payload)


@router.get('/', response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """Возвращает постраничный список пользователей."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{user_id}', response_model=UserGetResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserGetResponse:
    """Возвращает пользователя по id."""
    return await service.get_one(user_id)


@router.put('/{user_id}', response_model=UserUpdateResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    service: UserService = Depends(get_user_service),
) -> UserUpdateResponse:
    """Обновляет пользователя."""
    return await service.update(user_id, payload)


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> None:
    """Удаляет пользователя."""
    await service.delete(user_id)


@auth_router.post('/login', response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> LoginResponse:
    """Аутентифицирует оператора и выдаёт JWT."""
    return await service.authenticate(payload)
