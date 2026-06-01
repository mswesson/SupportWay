"""Модель сессии чата."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ChatSession(Base):
    """Таблица сессий чата между клиентом и оператором."""

    __tablename__ = 'chat_sessions'
    __table_args__ = {'comment': 'Сессии чата техподдержки.'}

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment='Идентификатор сессии.'
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('clients.id'), comment='Клиент-инициатор (FK на clients).'
    )
    operator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id'),
        nullable=True,
        comment='Назначенный оператор (FK на users).',
    )
    status_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('chat_statuses.id'),
        index=True,
        comment='Статус сессии (FK на справочник статусов).',
    )
    closed_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('closed_by_types.id'),
        nullable=True,
        comment='Кто закрыл сессию (FK на справочник).',
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=True, comment='Оценка качества от клиента (1..5).'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment='Дата и время создания.'
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, comment='Дата и время принятия оператором.'
    )
    closed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, comment='Дата и время закрытия.'
    )
