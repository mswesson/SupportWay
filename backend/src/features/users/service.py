"""Бизнес-логика фичи пользователей: CRUD и авторизация."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import EntityNotFoundError, InvalidCredentialsError
from src.core.security import create_access_token, hash_password, verify_password
from src.features.users.repository import user_repository
from src.features.users.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserGetResponse,
    UserListItem,
    UserListResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)


class UserService:
    """Сервис управления пользователями и аутентификации."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: UserCreateRequest) -> UserCreateResponse:
        """Создаёт пользователя с захешированным паролем."""
        values = {
            'full_name': payload.full_name,
            'password': hash_password(payload.password),
            'role_id': payload.role_id,
        }
        record = await user_repository.create(self._session, values)
        return UserCreateResponse.model_validate(record)

    async def get_one(self, user_id: int) -> UserGetResponse:
        """Возвращает пользователя по id."""
        record = await user_repository.get(self._session, user_id)
        if record is None:
            raise EntityNotFoundError('Пользователь не найден')
        return UserGetResponse.model_validate(record)

    async def get_list(self, page: int, page_size: int) -> UserListResponse:
        """Возвращает постраничный список пользователей."""
        offset = (page - 1) * page_size
        records, total = await user_repository.get_list(self._session, offset, page_size)
        return UserListResponse(
            items=[UserListItem.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(self, user_id: int, payload: UserUpdateRequest) -> UserUpdateResponse:
        """Обновляет пользователя. Пароль при наличии — хешируется."""
        values = payload.model_dump(exclude_unset=True)
        if 'password' in values:
            values['password'] = hash_password(values['password'])
        record = await user_repository.update(self._session, user_id, values)
        if record is None:
            raise EntityNotFoundError('Пользователь не найден')
        return UserUpdateResponse.model_validate(record)

    async def delete(self, user_id: int) -> None:
        """Удаляет пользователя."""
        deleted = await user_repository.delete(self._session, user_id)
        if not deleted:
            raise EntityNotFoundError('Пользователь не найден')

    async def authenticate(self, payload: LoginRequest) -> LoginResponse:
        """Проверяет учётные данные и выдаёт JWT."""
        user = await user_repository.get_by_full_name(self._session, payload.full_name)
        if user is None or not verify_password(payload.password, user.password):
            raise InvalidCredentialsError('Неверный логин или пароль')
        token = create_access_token(operator_id=user.id, role_id=user.role_id)
        return LoginResponse(access_token=token)


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    """Dependency: сервис пользователей с сессией запроса."""
    return UserService(session)
