"""Коллектор импортов моделей для Alembic autogenerate.

Каждая новая модель ОБЯЗАТЕЛЬНО импортируется здесь, иначе Alembic не увидит её.
"""

from src.core.database import Base  # noqa: F401
from src.features.chat_sessions.models import ChatSession  # noqa: F401
from src.features.clients.models import Client  # noqa: F401
from src.features.dictionaries.chat_statuses.models import ChatStatus  # noqa: F401
from src.features.dictionaries.closed_by_types.models import ClosedByType  # noqa: F401

# Справочники
from src.features.dictionaries.roles.models import Role  # noqa: F401
from src.features.dictionaries.sender_types.models import SenderType  # noqa: F401
from src.features.messages.models import Message  # noqa: F401

# Доменные сущности
from src.features.users.models import User  # noqa: F401

__all__ = ['Base']
