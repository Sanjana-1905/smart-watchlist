"""add auth fields to users

Revision ID: b2f14a9c7d3e
Revises: 714816d38004
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2f14a9c7d3e'
down_revision = '714816d38004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade():
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
