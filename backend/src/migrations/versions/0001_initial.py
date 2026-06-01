"""Начальная схема: справочники и доменные сущности.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _dictionary_table(name: str, comment: str) -> None:
    """Создаёт типовую таблицу-справочник (id, code, name)."""
    op.create_table(
        name,
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment='Идентификатор записи справочника.',
        ),
        sa.Column('code', sa.String(length=64), nullable=False, comment='Машинный код значения.'),
        sa.Column(
            'name', sa.String(length=128), nullable=False, comment='Человекочитаемое название.'
        ),
        sa.PrimaryKeyConstraint('id'),
        comment=comment,
    )
    op.create_index(f'ix_{name}_code', name, ['code'], unique=True)


def upgrade() -> None:
    # --- Справочники ---
    _dictionary_table('roles', 'Справочник ролей пользователей системы.')
    _dictionary_table('chat_statuses', 'Справочник статусов сессии чата.')
    _dictionary_table('closed_by_types', 'Справочник: кто закрыл сессию чата.')
    _dictionary_table('sender_types', 'Справочник типов отправителя сообщения.')

    # --- Пользователи ---
    op.create_table(
        'users',
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment='Идентификатор пользователя.',
        ),
        sa.Column(
            'full_name', sa.String(length=256), nullable=False, comment='ФИО для отображения.'
        ),
        sa.Column('password', sa.String(length=256), nullable=False, comment='Bcrypt-хеш пароля.'),
        sa.Column(
            'role_id',
            sa.Integer(),
            nullable=False,
            comment='Роль пользователя (FK на справочник ролей).',
        ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('id'),
        comment='Операторы и администраторы техподдержки.',
    )

    # --- Клиенты ---
    op.create_table(
        'clients',
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment='Идентификатор клиента.',
        ),
        sa.Column(
            'full_name',
            sa.String(length=256),
            nullable=False,
            comment='ФИО клиента (обязательно).',
        ),
        sa.Column('phone', sa.String(length=32), nullable=True, comment='Номер телефона.'),
        sa.Column('email', sa.String(length=256), nullable=True, comment='Email клиента.'),
        sa.Column(
            'external_id',
            sa.String(length=128),
            nullable=True,
            comment='Внешний id клиента в системе-источнике.',
        ),
        sa.Column(
            'source',
            sa.String(length=64),
            nullable=True,
            comment='Метка источника обращения (telegram/web/...).',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
            comment='Дата и время создания.',
        ),
        sa.PrimaryKeyConstraint('id'),
        comment='Клиенты, обратившиеся в техподдержку.',
    )
    op.create_index(
        'uq_clients_source_external',
        'clients',
        ['source', 'external_id'],
        unique=True,
        postgresql_where=sa.text('external_id IS NOT NULL'),
    )

    # --- Сессии чата ---
    op.create_table(
        'chat_sessions',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False, comment='Идентификатор сессии.'
        ),
        sa.Column(
            'client_id', sa.Integer(), nullable=False, comment='Клиент-инициатор (FK на clients).'
        ),
        sa.Column(
            'operator_id',
            sa.Integer(),
            nullable=True,
            comment='Назначенный оператор (FK на users).',
        ),
        sa.Column(
            'status_id',
            sa.Integer(),
            nullable=False,
            comment='Статус сессии (FK на справочник статусов).',
        ),
        sa.Column(
            'closed_by_id',
            sa.Integer(),
            nullable=True,
            comment='Кто закрыл сессию (FK на справочник).',
        ),
        sa.Column(
            'rating', sa.Integer(), nullable=True, comment='Оценка качества от клиента (1..5).'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
            comment='Дата и время создания.',
        ),
        sa.Column(
            'accepted_at',
            sa.DateTime(),
            nullable=True,
            comment='Дата и время принятия оператором.',
        ),
        sa.Column('closed_at', sa.DateTime(), nullable=True, comment='Дата и время закрытия.'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['operator_id'], ['users.id']),
        sa.ForeignKeyConstraint(['status_id'], ['chat_statuses.id']),
        sa.ForeignKeyConstraint(['closed_by_id'], ['closed_by_types.id']),
        sa.PrimaryKeyConstraint('id'),
        comment='Сессии чата техподдержки.',
    )
    op.create_index('ix_chat_sessions_status_id', 'chat_sessions', ['status_id'])

    # --- Сообщения ---
    op.create_table(
        'messages',
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment='Идентификатор сообщения.',
        ),
        sa.Column(
            'chat_session_id',
            sa.Integer(),
            nullable=False,
            comment='Сессия чата (FK на chat_sessions).',
        ),
        sa.Column(
            'sender_type_id',
            sa.Integer(),
            nullable=False,
            comment='Тип отправителя (FK на справочник типов отправителя).',
        ),
        sa.Column(
            'sender_id',
            sa.Integer(),
            nullable=True,
            comment='Id оператора-отправителя (если отправитель — оператор).',
        ),
        sa.Column('text', sa.Text(), nullable=False, comment='Текст сообщения.'),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
            comment='Дата и время отправки.',
        ),
        sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id']),
        sa.ForeignKeyConstraint(['sender_type_id'], ['sender_types.id']),
        sa.PrimaryKeyConstraint('id'),
        comment='Сообщения переписки в чатах.',
    )
    op.create_index('ix_messages_chat_session_id', 'messages', ['chat_session_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('chat_sessions')
    op.drop_index('uq_clients_source_external', table_name='clients')
    op.drop_table('clients')
    op.drop_table('users')
    op.drop_table('sender_types')
    op.drop_table('closed_by_types')
    op.drop_table('chat_statuses')
    op.drop_table('roles')
