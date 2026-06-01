"""Репозиторий пользователей."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import BaseCrudRepository
from src.features.users.models import User


class UserRepository(BaseCrudRepository[User]):
    """Доступ к данным таблицы users."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_full_name(self, session: AsyncSession, full_name: str) -> User | None:
        """Возвращает пользователя по ФИО (используется при логине)."""
        result = await session.execute(select(User).where(User.full_name == full_name))
        return result.scalar_one_or_none()


user_repository = UserRepository()
