from sqlalchemy import Column, Boolean, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import BaseModel


class OutletTaxConfig(BaseModel):
    __tablename__ = "outlet_tax_config"

    outlet_id = Column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Pajak (PB1 / Pajak Restoran)
    pb1_enabled = Column(Boolean(), server_default="false", nullable=False)
    tax_pct = Column(Float(), server_default="10.0", nullable=False)  # default 10%

    # PPN (jika PKP)
    ppn_enabled = Column(Boolean(), server_default="false", nullable=False)
    pkp_registered = Column(Boolean(), server_default="false", nullable=False)

    # Service Charge
    service_charge_enabled = Column(Boolean(), server_default="false", nullable=False)
    service_charge_pct = Column(Float(), server_default="0.0", nullable=False)

    # Harga sudah termasuk pajak?
    tax_inclusive = Column(Boolean(), server_default="false", nullable=False)

    row_version = Column(Integer, server_default="0", nullable=False)
