"""Модель справочника статусов чата."""

from src.features.dictionaries.base import DictionaryBase


class ChatStatus(DictionaryBase):
    """Справочник статусов чата: pending / reserved / active / closed."""

    __tablename__ = 'chat_statuses'
    __table_args__ = {'comment': 'Справочник статусов сессии чата.'}
