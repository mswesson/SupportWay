"""Модель справочника типов отправителя сообщения."""

from src.features.dictionaries.base import DictionaryBase


class SenderType(DictionaryBase):
    """Справочник типов отправителя: client / operator / system."""

    __tablename__ = 'sender_types'
    __table_args__ = {'comment': 'Справочник типов отправителя сообщения.'}
