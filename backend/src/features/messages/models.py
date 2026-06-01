"""Модель сообщения чата."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Message(Base):
    """Таблица сообщений внутри сессии чата."""

    __tablename__ = 'messages'
    __table_args__ = {'comment': 'Сообщения переписки в чатах.'}

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment='Идентификатор сообщения.'
    )
    chat_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('chat_sessions.id'),
        index=True,
        comment='Сессия чата (FK на chat_sessions).',
    )
    sender_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('sender_types.id'),
        comment='Тип отправителя (FK на справочник типов отправителя).',
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, nullable=True, comment='Id оператора-отправителя (если отправитель — оператор).'
    )
    text: Mapped[str] = mapped_column(Text, comment='Текст сообщения.')
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True, comment='Дата и время отправки.'
    )
