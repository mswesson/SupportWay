"""Заполнение справочников начальными значениями.

Revision ID: 0002_seed_dictionaries
Revises: 0001_initial
Create Date: 2026-05-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002_seed_dictionaries'
down_revision: str | None = '0001_initial'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Значения справочников: имя таблицы -> список (code, name)
_SEED: dict[str, list[tuple[str, str]]] = {
    'roles': [
        ('operator', 'Оператор'),
        ('admin', 'Администратор'),
    ],
    'chat_statuses': [
        ('pending', 'В очереди'),
        ('reserved', 'Зарезервирован'),
        ('active', 'Активен'),
        ('closed', 'Закрыт'),
    ],
    'closed_by_types': [
        ('operator', 'Оператор'),
        ('client', 'Клиент'),
        ('system', 'Система'),
    ],
    'sender_types': [
        ('client', 'Клиент'),
        ('operator', 'Оператор'),
        ('system', 'Система'),
    ],
}


def upgrade() -> None:
    for table_name, rows in _SEED.items():
        table = sa.table(
            table_name,
            sa.column('code', sa.String),
            sa.column('name', sa.String),
        )
        op.bulk_insert(table, [{'code': code, 'name': name} for code, name in rows])


def downgrade() -> None:
    for table_name, rows in _SEED.items():
        codes = tuple(code for code, _ in rows)
        op.execute(
            sa.text(f'DELETE FROM {table_name} WHERE code IN :codes').bindparams(
                sa.bindparam('codes', value=codes, expanding=True)
            )
        )
