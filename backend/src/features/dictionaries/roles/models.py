"""Модель справочника ролей пользователей."""

from src.features.dictionaries.base import DictionaryBase


class Role(DictionaryBase):
    """Справочник ролей: operator / admin."""

    __tablename__ = 'roles'
    __table_args__ = {'comment': 'Справочник ролей пользователей системы.'}
