"""update hello_world message to light

Revision ID: 20260310_001
Revises: 3902771f5439
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260310_001'
down_revision: Union[str, None] = '3902771f5439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update the hello_world message from "Hello World from Postgres" to "Let light shine from heaven"
    op.execute(
        sa.text("UPDATE hello_world SET message = 'Let light shine from heaven' WHERE message = 'Hello World from Postgres'")
    )


def downgrade() -> None:
    # Revert the message back to "Hello World from Postgres"
    op.execute(
        sa.text("UPDATE hello_world SET message = 'Hello World from Postgres' WHERE message = 'Let light shine from heaven'")
    )
