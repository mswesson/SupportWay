"""Репозиторий справочника ролей."""

from src.core.crud import BaseCrudRepository
from src.features.dictionaries.roles.models import Role

role_repository = BaseCrudRepository(Role)
