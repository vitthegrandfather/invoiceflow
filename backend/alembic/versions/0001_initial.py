"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-12
"""

from __future__ import annotations

from alembic import op

from app.db.base import Base
from app.models import load_models

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    load_models()
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    load_models()
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
