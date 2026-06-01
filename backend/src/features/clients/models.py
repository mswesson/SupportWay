"""Модель клиента — инициатора обращения."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Client(Base):
    """Таблица клиентов (источник обращения — любое внешнее приложение)."""

    __tablename__ = 'clients'
    __table_args__ = (
        # Связывание повторных обращений по внешнему id в рамках источника.
        Index(
            'uq_clients_source_external',
            'source',
            'external_id',
            unique=True,
            postgresql_where=text('external_id IS NOT NULL'),
        ),
        {'comment': 'Клиенты, обратившиеся в техподдержку.'},
    )

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment='Идентификатор клиента.'
    )
    full_name: Mapped[str] = mapped_column(String(256), comment='ФИО клиента (обязательно).')
    phone: Mapped[str] = mapped_column(String(32), nullable=True, comment='Номер телефона.')
    email: Mapped[str] = mapped_column(String(256), nullable=True, comment='Email клиента.')
    external_id: Mapped[str] = mapped_column(
        String(128), nullable=True, comment='Внешний id клиента в системе-источнике.'
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=True, comment='Метка источника обращения (telegram/web/...).'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment='Дата и время создания.'
    )
