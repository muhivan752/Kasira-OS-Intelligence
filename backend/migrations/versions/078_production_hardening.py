"""Production hardening: order_number unique, role permissions, order discount tracking

Revision ID: 078
Revises: 077
"""
from alembic import op
import sqlalchemy as sa

revision = '078'
down_revision = '077'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Order number UNIQUE constraint
    op.create_unique_constraint('uq_orders_order_number', 'orders', ['order_number'])

    # 2. Role permission flags for refund & discount override
    op.add_column('roles', sa.Column('can_refund', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('roles', sa.Column('can_approve_refund', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('roles', sa.Column('can_discount_override', sa.Boolean(), server_default='false', nullable=False))

    # 3. Order discount tracking (who approved, reason)
    op.add_column('orders', sa.Column('discount_approved_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('orders', sa.Column('discount_reason', sa.String(200), nullable=True))

    # 4. Grant owner roles all new permissions
    op.execute("""
        UPDATE roles SET can_refund = true, can_approve_refund = true, can_discount_override = true
        WHERE name IN ('owner', 'Owner', 'admin', 'Admin') OR is_system = true
    """)


def downgrade():
    op.drop_column('orders', 'discount_reason')
    op.drop_column('orders', 'discount_approved_by')
    op.drop_column('roles', 'can_discount_override')
    op.drop_column('roles', 'can_approve_refund')
    op.drop_column('roles', 'can_refund')
    op.drop_constraint('uq_orders_order_number', 'orders', type_='unique')
