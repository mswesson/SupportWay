"""Общие строительные блоки для справочников статусов (read-only).

Справочники одинаковы по структуре (id, code, name) и читаются только на чтение,
поэтому логика вынесена в базовые классы, а каждая подфича задаёт свои Pydantic-схемы.
"""

from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.crud import BaseCrudRepository
from src.core.database import Base
from src.core.exceptions import EntityNotFoundError


class DictionaryBase(Base):
    """Абстрактная базовая модель справочника (id, code, name)."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment='Идентификатор записи справочника.'
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, comment='Машинный код значения.'
    )
    name: Mapped[str] = mapped_column(String(128), comment='Человекочитаемое название.')


class BaseDictionaryService:
    """Базовый сервис справочника: получение одного значения и постраничного списка."""

    def __init__(
        self,
        session: Any,
        repository: BaseCrudRepository[Any],
        item_cls: type[Any],
        list_response_cls: type[Any],
        get_response_cls: type[Any],
    ) -> None:
        self._session = session
        self._repository = repository
        self._item_cls = item_cls
        self._list_response_cls = list_response_cls
        self._get_response_cls = get_response_cls

    async def get_list(self, page: int, page_size: int) -> Any:
        """Возвращает постраничный список значений справочника."""
        offset = (page - 1) * page_size
        records, total = await self._repository.get_list(self._session, offset, page_size)
        return self._list_response_cls(
            items=[self._item_cls.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_one(self, item_id: int) -> Any:
        """Возвращает одно значение справочника по id."""
        record = await self._repository.get(self._session, item_id)
        if record is None:
            raise EntityNotFoundError('Значение справочника не найдено')
        return self._get_response_cls.model_validate(record)
