import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)
    step: Mapped[str] = mapped_column(String)  # ingestion / preprocessing / annotation / ranking
    level: Mapped[str] = mapped_column(String, default="INFO")  # INFO / WARNING / ERROR
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    pipeline_version: Mapped[str] = mapped_column(String, default="1.0.0")
    tool_version: Mapped[str] = mapped_column(String, nullable=True)
