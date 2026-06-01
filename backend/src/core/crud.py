"""Базовый generic-репозиторий CRUD — устраняет дублирование между фичами."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base


class BaseCrudRepository[ModelType: Base]:
    """Базовый CRUD поверх одной модели.

    Сессия не хранится в репозитории — передаётся в каждый метод параметром.
    Коммиты выполняет репозиторий.
    """

    def __init__(self, model: type[ModelType]) -> None:
        # Класс модели задаётся один раз при создании singleton-инстанса.
        self._model = model

    async def create(self, session: AsyncSession, values: dict[str, Any]) -> ModelType:
        """Создаёт запись и коммитит."""
        record = self._model(**values)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def get(self, session: AsyncSession, record_id: int) -> ModelType | None:
        """Возвращает запись по id или None."""
        return await session.get(self._model, record_id)

    async def get_list(
        self, session: AsyncSession, offset: int, limit: int
    ) -> tuple[list[ModelType], int]:
        """Возвращает постраничный список записей и общее количество."""
        total = (await session.execute(select(func.count()).select_from(self._model))).scalar_one()
        records = (
            (
                await session.execute(
                    select(self._model).order_by(self._model.id).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(records), total

    async def update(
        self, session: AsyncSession, record_id: int, values: dict[str, Any]
    ) -> ModelType | None:
        """Обновляет поля записи и коммитит. None, если записи нет."""
        record = await session.get(self._model, record_id)
        if record is None:
            return None
        for key, value in values.items():
            setattr(record, key, value)
        await session.commit()
        await session.refresh(record)
        return record

    async def delete(self, session: AsyncSession, record_id: int) -> bool:
        """Удаляет запись. True, если удалили, False — если записи не было."""
        record = await session.get(self._model, record_id)
        if record is None:
            return False
        await session.delete(record)
        await session.commit()
        return True
