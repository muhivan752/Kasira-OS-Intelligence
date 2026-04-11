from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.models.base import BaseModel


class KnowledgeGraphEdge(BaseModel):
    __tablename__ = "knowledge_graph_edges"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    source_node_type = Column(String, nullable=False)   # product, ingredient, category, supplier
    source_node_id = Column(UUID(as_uuid=True), nullable=False)
    target_node_type = Column(String, nullable=False)
    target_node_id = Column(UUID(as_uuid=True), nullable=False)
    relation_type = Column(String, nullable=False)       # contains, belongs_to, similar_to, affects
    weight = Column(Numeric(5, 4), server_default='1.0', nullable=False)
    metadata_payload = Column(JSONB, nullable=True)      # extra context (qty, unit, etc.)
