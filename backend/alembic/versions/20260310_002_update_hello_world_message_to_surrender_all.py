"""update hello_world message to surrender all

Revision ID: 20260310_002
Revises: 20260310_001
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260310_002'
down_revision: Union[str, None] = '20260310_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update the hello_world message from "Let light shine from heaven" to "Surrender all"
    op.execute(
        sa.text("UPDATE hello_world SET message = 'Surrender all' WHERE message = 'Let light shine from heaven'")
    )


def downgrade() -> None:
    # Revert the message back to "Let light shine from heaven"
    op.execute(
        sa.text("UPDATE hello_world SET message = 'Let light shine from heaven' WHERE message = 'Surrender all'")
    )
