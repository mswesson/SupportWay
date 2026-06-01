"""Репозиторий справочника типов отправителя."""

from src.core.crud import BaseCrudRepository
from src.features.dictionaries.sender_types.models import SenderType

sender_type_repository = BaseCrudRepository(SenderType)
