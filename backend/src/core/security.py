"""Безопасность: bcrypt-хеши паролей, JWT, авторизация операторов и клиентов."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from src.core.config import settings
from src.core.exceptions import AuthorizationError
from src.core.redis import get_redis


@dataclass
class CurrentOperator:
    """Аутентифицированный оператор из JWT."""

    id: int
    role_id: int


# --- Пароли (bcrypt) ---


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля его bcrypt-хешу."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# --- JWT ---


def create_access_token(operator_id: int, role_id: int) -> str:
    """Создаёт JWT для оператора."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_TTL_MINUTES)
    payload = {'sub': str(operator_id), 'role_id': role_id, 'exp': expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> CurrentOperator:
    """Декодирует и валидирует JWT. Кидает AuthorizationError при ошибке."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return CurrentOperator(id=int(payload['sub']), role_id=int(payload['role_id']))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthorizationError('Невалидный токен') from exc


# --- Авторизация операторов по HTTP ---

_bearer_scheme = HTTPBearer(auto_error=True)


def get_current_operator(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentOperator:
    """Dependency: достаёт и валидирует JWT из заголовка Authorization."""
    return decode_access_token(credentials.credentials)


# --- Авторизация операторов по WebSocket (токен из query) ---


def authenticate_ws_operator(token: str) -> CurrentOperator:
    """Валидирует JWT, переданный при подключении к WebSocket оператора."""
    return decode_access_token(token)


# --- Авторизация клиентской стороны (одноразовый client_token в Redis) ---


def _client_token_key(chat_id: int) -> str:
    return f'chat:{chat_id}:client_token'


async def issue_client_token(redis: Redis, chat_id: int, token: str) -> None:
    """Сохраняет одноразовый токен клиента в Redis с TTL."""
    await redis.set(
        _client_token_key(chat_id),
        token,
        ex=settings.CLIENT_TOKEN_TTL_SECONDS,
    )


async def verify_client_token(
    chat_id: int,
    token: str,
    redis: Redis = Depends(get_redis),
) -> bool:
    """Проверяет client_token конкретного чата."""
    stored = await redis.get(_client_token_key(chat_id))
    return stored is not None and stored == token


def verify_integration_key(provided_key: str | None) -> None:
    """Проверяет статический integration-ключ создания чата.

    Если ключ в настройках не задан — проверка отключена.
    """
    if settings.INTEGRATION_API_KEY is None:
        return
    if provided_key != settings.INTEGRATION_API_KEY:
        raise AuthorizationError('Неверный integration-ключ')
