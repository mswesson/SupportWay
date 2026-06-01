"""Модель оператора/администратора техподдержки."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class User(Base):
    """Таблица пользователей системы ТП (операторы и админы)."""

    __tablename__ = 'users'
    __table_args__ = {'comment': 'Операторы и администраторы техподдержки.'}

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment='Идентификатор пользователя.'
    )
    full_name: Mapped[str] = mapped_column(String(256), comment='ФИО для отображения.')
    password: Mapped[str] = mapped_column(String(256), comment='Bcrypt-хеш пароля.')
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('roles.id'), comment='Роль пользователя (FK на справочник ролей).'
    )
