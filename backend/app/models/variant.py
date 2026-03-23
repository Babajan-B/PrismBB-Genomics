import uuid
from sqlalchemy import String, Integer, Float, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)

    # Genomic coordinates
    chrom: Mapped[str] = mapped_column(String)
    pos: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String)
    alt: Mapped[str] = mapped_column(String)
    variant_key: Mapped[str] = mapped_column(String, index=True)  # chrom:pos:ref:alt

    # Sample info
    sample_id: Mapped[str] = mapped_column(String, nullable=True)
    zygosity: Mapped[str] = mapped_column(String, nullable=True)  # HET / HOM / HEMI
    genotype: Mapped[str] = mapped_column(String, nullable=True)

    # Gene & transcript
    gene: Mapped[str] = mapped_column(String, nullable=True)
    transcript: Mapped[str] = mapped_column(String, nullable=True)
    hgvs_c: Mapped[str] = mapped_column(String, nullable=True)
    hgvs_p: Mapped[str] = mapped_column(String, nullable=True)
    consequence: Mapped[str] = mapped_column(String, nullable=True)
    impact: Mapped[str] = mapped_column(String, nullable=True)  # HIGH/MODERATE/LOW/MODIFIER

    # ClinVar
    clinvar_id: Mapped[str] = mapped_column(String, nullable=True)
    clinvar_significance: Mapped[str] = mapped_column(String, nullable=True)
    clinvar_review_status: Mapped[str] = mapped_column(String, nullable=True)

    # Population frequency
    gnomad_af: Mapped[float] = mapped_column(Float, nullable=True)
    gnomad_af_popmax: Mapped[float] = mapped_column(Float, nullable=True)

    # AlphaMissense (DeepMind AI pathogenicity)
    alphamissense_score: Mapped[float] = mapped_column(Float, nullable=True)
    alphamissense_class: Mapped[str] = mapped_column(String, nullable=True)  # likely_pathogenic / ambiguous / likely_benign

    # ACMG classification (computed during ranking)
    acmg_score: Mapped[int] = mapped_column(Integer, nullable=True)
    acmg_class: Mapped[str] = mapped_column(String, nullable=True)  # Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign
    acmg_rules: Mapped[list] = mapped_column(JSON, default=list)
    compound_het: Mapped[bool] = mapped_column(nullable=True)

    # Panel & phenotype
    panelapp_panels: Mapped[list] = mapped_column(JSON, default=list)
    hpo_matched_terms: Mapped[list] = mapped_column(JSON, default=list)

    # Ranking
    rank_score: Mapped[float] = mapped_column(Float, nullable=True)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=True)
    rank_details: Mapped[dict] = mapped_column(JSON, default=dict)

    # Check Agent OMIM validation
    validation_status: Mapped[str] = mapped_column(String, nullable=True)  # confirmed / conflict / unconfirmed / no_omim_entry
    omim_disease: Mapped[str] = mapped_column(String, nullable=True)
    omim_inheritance: Mapped[str] = mapped_column(String, nullable=True)  # AD / AR / XLR / XLD / MT

    # Raw annotation data (full VEP output)
    raw_annotation: Mapped[dict] = mapped_column(JSON, default=dict)
