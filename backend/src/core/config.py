"""Настройки приложения через Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация сервиса из переменных окружения."""

    # Сервисные настройки
    SERVICE_NAME: str = 'SupportWay'
    SERVICE_VERSION: str = '1.0.0'

    # База данных
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str

    @property
    def database_url(self) -> str:
        """Строка подключения к PostgreSQL (asyncpg)."""
        return (
            f'postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}'
            f'@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}'
        )

    # Redis
    REDIS_URL: str

    # Канал Redis Pub/Sub для рассылки WebSocket-эвентов между воркерами
    WS_EVENTS_CHANNEL: str = 'ws_events'

    # JWT для авторизации операторов
    JWT_SECRET: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_TTL_MINUTES: int = 60

    # Опциональный статический ключ для защиты создания чата (server-to-server).
    # Если None — проверка ключа отключена.
    INTEGRATION_API_KEY: str | None = None

    # Время жизни одноразового токена клиентской стороны (секунды)
    CLIENT_TOKEN_TTL_SECONDS: int = 60 * 60 * 24

    # Время жизни чёрного списка операторов по чату (секунды)
    CHAT_REJECTED_TTL_SECONDS: int = 60 * 60 * 24

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        env_prefix='SUPPORT_',
    )


settings = Settings()  # type: ignore
