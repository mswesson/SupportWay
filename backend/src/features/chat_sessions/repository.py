"""Репозиторий сессий чата."""

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import BaseCrudRepository
from src.features.chat_sessions.models import ChatSession
from src.features.clients.models import Client


def _search_condition(search: str) -> ColumnElement[bool]:
    """Условие поиска чата: по имени клиента (ILIKE) или по точному id чата."""
    conditions: list[ColumnElement[bool]] = [Client.full_name.ilike(f'%{search}%')]
    if search.isdigit():
        conditions.append(ChatSession.id == int(search))
    return or_(*conditions)


class ChatSessionRepository(BaseCrudRepository[ChatSession]):
    """Доступ к данным таблицы chat_sessions."""

    def __init__(self) -> None:
        super().__init__(ChatSession)

    async def list_by_operator_and_statuses(
        self, session: AsyncSession, operator_id: int, status_ids: list[int]
    ) -> list[ChatSession]:
        """Возвращает чаты оператора в указанных статусах по возрастанию времени создания."""
        result = await session.execute(
            select(ChatSession)
            .where(
                ChatSession.operator_id == operator_id,
                ChatSession.status_id.in_(status_ids),
            )
            .order_by(ChatSession.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_closed_paginated(
        self,
        session: AsyncSession,
        operator_id: int,
        status_id: int,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[ChatSession], int]:
        """Постранично возвращает завершённые чаты оператора (свежие сверху, с поиском)."""
        rows = (
            select(ChatSession)
            .join(Client, Client.id == ChatSession.client_id)
            .where(ChatSession.operator_id == operator_id, ChatSession.status_id == status_id)
        )
        count = (
            select(func.count())
            .select_from(ChatSession)
            .join(Client, Client.id == ChatSession.client_id)
            .where(ChatSession.operator_id == operator_id, ChatSession.status_id == status_id)
        )
        if search:
            cond = _search_condition(search)
            rows = rows.where(cond)
            count = count.where(cond)

        total = (await session.execute(count)).scalar_one()
        records = (
            await session.execute(
                rows.order_by(ChatSession.closed_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(records), total


chat_session_repository = ChatSessionRepository()
