"""Добавление статуса чата 'no_operator' (нет оператора).

Revision ID: 0003_seed_no_operator_status
Revises: 0002_seed_dictionaries
Create Date: 2026-06-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003_seed_no_operator_status'
down_revision: str | None = '0002_seed_dictionaries'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Терминальный статус для чатов, созданных без онлайн-операторов (только для истории)
_ROWS: list[tuple[str, str]] = [
    ('no_operator', 'Нет оператора'),
]


def upgrade() -> None:
    table = sa.table(
        'chat_statuses',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
    )
    op.bulk_insert(table, [{'code': code, 'name': name} for code, name in _ROWS])


def downgrade() -> None:
    codes = tuple(code for code, _ in _ROWS)
    op.execute(
        sa.text('DELETE FROM chat_statuses WHERE code IN :codes').bindparams(
            sa.bindparam('codes', value=codes, expanding=True)
        )
    )
