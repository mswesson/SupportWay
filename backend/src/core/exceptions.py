"""Доменные исключения сервиса (не знают про HTTP)."""


class DomainError(Exception):
    """Базовое доменное исключение."""

    pass


class EntityNotFoundError(DomainError):
    """Сущность не найдена в БД."""

    pass


class NoOperatorsAvailableError(DomainError):
    """Нет свободных операторов онлайн для назначения чата."""

    pass


class InvalidChatStateError(DomainError):
    """Операция недопустима в текущем статусе чата."""

    pass


class InvalidCredentialsError(DomainError):
    """Неверный логин или пароль оператора."""

    pass


class AuthorizationError(DomainError):
    """Ошибка авторизации: невалидный токен/ключ или нет доступа."""

    pass
