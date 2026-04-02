from decimal import Decimal
from sqlalchemy import Column, Numeric, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from backend.models.base import BaseModel


class CustomerPoints(BaseModel):
    __tablename__ = "customer_points"

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    balance = Column(Numeric(12, 2), server_default="0", nullable=False)
    lifetime_earned = Column(Numeric(12, 2), server_default="0", nullable=False)
    lifetime_redeemed = Column(Numeric(12, 2), server_default="0", nullable=False)
    # Golden Rule #29
    row_version = Column(Integer, server_default="0", nullable=False)


_point_txn_type = ENUM(
    "earn", "redeem", "adjustment", "refund",
    name="point_transaction_type",
    create_type=False,
)


class PointTransaction(BaseModel):
    __tablename__ = "point_transactions"

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type = Column(_point_txn_type, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
