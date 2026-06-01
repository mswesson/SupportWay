"""Точка входа: сборка FastAPI приложения, WebSocket-инфраструктуры и роутеров."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core import logger  # noqa: F401 — применяет настройку loguru
from src.core.config import settings
from src.core.exceptions import (
    AuthorizationError,
    DomainError,
    EntityNotFoundError,
    InvalidChatStateError,
    InvalidCredentialsError,
)
from src.core.redis import redis_client
from src.core.ws_manager import ws_manager
from src.features.chat_sessions.router import router as chat_sessions_router
from src.features.clients.router import router as clients_router
from src.features.dictionaries.chat_statuses.router import router as chat_statuses_router
from src.features.dictionaries.closed_by_types.router import router as closed_by_types_router
from src.features.dictionaries.roles.router import router as roles_router
from src.features.dictionaries.sender_types.router import router as sender_types_router
from src.features.messages.router import router as messages_router
from src.features.operators.router import router as operators_router
from src.features.users.router import auth_router
from src.features.users.router import router as users_router
from src.use_cases.chat_lifecycle.router import router as chats_router
from src.use_cases.chat_lifecycle.router import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл: запуск слушателя Redis Pub/Sub для рассылки WS-эвентов."""
    await ws_manager.start(redis_client)
    yield
    await ws_manager.stop()
    await redis_client.aclose()


app = FastAPI(
    title=settings.SERVICE_NAME,
    description='Сервис агрегации чатов техподдержки: распределение обращений и реалтайм-обмен.',
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)


# --- CORS (временно открыт для всех источников; сузить перед продакшеном) ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    # JWT передаётся в заголовке Authorization, cookie не используются,
    # поэтому credentials не нужны (и несовместимы с allow_origins=['*']).
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


# --- Обработчики доменных исключений (маппинг в HTTP) ---


@app.exception_handler(EntityNotFoundError)
async def handle_not_found(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={'detail': str(exc)})


@app.exception_handler(InvalidChatStateError)
async def handle_invalid_state(request: Request, exc: InvalidChatStateError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={'detail': str(exc)})


@app.exception_handler(InvalidCredentialsError)
async def handle_invalid_credentials(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={'detail': str(exc)})


@app.exception_handler(AuthorizationError)
async def handle_authorization(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={'detail': str(exc)})


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={'detail': str(exc)})


# --- Сборка роутеров под /api/v1 ---

v1_router = APIRouter(prefix='/api/v1')

# Справочники
v1_router.include_router(roles_router)
v1_router.include_router(chat_statuses_router)
v1_router.include_router(closed_by_types_router)
v1_router.include_router(sender_types_router)

# Авторизация и пользователи
v1_router.include_router(auth_router)
v1_router.include_router(users_router)

# CRUD-сущности
v1_router.include_router(clients_router)
v1_router.include_router(chat_sessions_router)
v1_router.include_router(messages_router)

# Операторы (presence)
v1_router.include_router(operators_router)

# Жизненный цикл чата: REST + WebSocket
v1_router.include_router(chats_router)
v1_router.include_router(ws_router)

app.include_router(v1_router)
