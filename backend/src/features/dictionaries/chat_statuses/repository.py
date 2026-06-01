"""Репозиторий справочника статусов чата."""

from src.core.crud import BaseCrudRepository
from src.features.dictionaries.chat_statuses.models import ChatStatus

chat_status_repository = BaseCrudRepository(ChatStatus)
