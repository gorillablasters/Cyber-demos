from alembic import op
import sqlalchemy as sa

revision = "20250902_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    tx_type = sa.Enum("income", "expense", name="txtype")

    freq = sa.Enum(
        "once",
        "weekly",
        "bi-weekly",
        "monthly",
        "quarterly",
        "yearly",
        name="frequency",
    )

    # tx_type.create(op.get_bind(), checkfirst=True)
    # freq.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "starting_amount", sa.Numeric(14, 2), nullable=False, server_default="0"
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", tx_type, nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("frequency", freq, nullable=False, server_default="once"),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("profiles")
    sa.Enum(name="frequency").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="txtype").drop(op.get_bind(), checkfirst=True)
