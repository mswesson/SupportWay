"""Репозиторий сообщений."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import BaseCrudRepository
from src.features.messages.models import Message


class MessageRepository(BaseCrudRepository[Message]):
    """Доступ к данным таблицы messages."""

    def __init__(self) -> None:
        super().__init__(Message)

    async def get_by_chat(self, session: AsyncSession, chat_session_id: int) -> list[Message]:
        """Возвращает все сообщения чата по возрастанию времени (для истории)."""
        result = await session.execute(
            select(Message)
            .where(Message.chat_session_id == chat_session_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(result.scalars().all())


message_repository = MessageRepository()
