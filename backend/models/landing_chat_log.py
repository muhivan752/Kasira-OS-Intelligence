import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID

from backend.core.database import Base


class LandingChatLog(Base):
    """Pertanyaan pengunjung landing page + jawaban asisten.

    Riset produk: keberatan apa yang muncul sebelum orang daftar.
    Sengaja TANPA tenant_id/RLS (pengunjung belum punya tenant) dan tanpa data
    yang bisa ngidentifikasi orang — `session_id` cuma angka acak dari browser.
    """
    __tablename__ = "landing_chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                server_default=text("gen_random_uuid()"))
    session_id = Column(String(64), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    turn = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=text("now()"))
