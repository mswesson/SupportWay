"""Модель справочника инициаторов закрытия чата."""

from src.features.dictionaries.base import DictionaryBase


class ClosedByType(DictionaryBase):
    """Справочник инициаторов закрытия: operator / client / system."""

    __tablename__ = 'closed_by_types'
    __table_args__ = {'comment': 'Справочник: кто закрыл сессию чата.'}
