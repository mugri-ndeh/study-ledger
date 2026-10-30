"""Private plan templates (only offered to admins).

Revision ID: 0002
Revises: f2cda1a7ced9
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "f2cda1a7ced9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_templates", sa.Column("is_public", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("plan_templates", "is_public")
