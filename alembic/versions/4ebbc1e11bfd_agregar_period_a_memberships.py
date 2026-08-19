"""agregar period a memberships

Revision ID: 4ebbc1e11bfd
Revises: 1b7415b8f7af
Create Date: 2026-08-19 20:27:09.947439

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4ebbc1e11bfd"
down_revision: Union[str, Sequence[str], None] = "1b7415b8f7af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    membership_period = sa.Enum(
        "daily", "weekly", "biweekly", "monthly", "quarterly", name="membershipperiod"
    )
    membership_period.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "memberships",
        sa.Column(
            "period",
            sa.Enum(
                "daily",
                "weekly",
                "biweekly",
                "monthly",
                "quarterly",
                name="membershipperiod",
                create_type=False,
            ),
            nullable=False,
            server_default="monthly",
        ),
    )
    op.alter_column("memberships", "period", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("memberships", "period")
    sa.Enum(name="membershipperiod").drop(op.get_bind(), checkfirst=True)
