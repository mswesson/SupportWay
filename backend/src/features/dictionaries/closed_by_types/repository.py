"""Репозиторий справочника инициаторов закрытия чата."""

from src.core.crud import BaseCrudRepository
from src.features.dictionaries.closed_by_types.models import ClosedByType

closed_by_type_repository = BaseCrudRepository(ClosedByType)
