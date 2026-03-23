import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    PREPROCESSING = "preprocessing"
    ANNOTATING = "annotating"
    RANKING = "ranking"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    vcf_filename: Mapped[str] = mapped_column(String)
    vcf_path: Mapped[str] = mapped_column(String)
    genome_build: Mapped[str] = mapped_column(String, default="GRCh38")
    sample_count: Mapped[int] = mapped_column(default=0)
    variant_count: Mapped[int] = mapped_column(default=0)
    hpo_terms: Mapped[list] = mapped_column(JSON, default=list)
    gene_list: Mapped[list] = mapped_column(JSON, default=list)
    qc_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    clinical_mode: Mapped[bool] = mapped_column(default=False)
    pipeline_version: Mapped[str] = mapped_column(String, default="1.0.0")
