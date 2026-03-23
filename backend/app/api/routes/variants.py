"""Variant retrieval and filtering routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.variant import Variant

router = APIRouter()


@router.get("/{job_id}/variants")
async def get_variants(
    job_id: str,
    limit: int = Query(50, le=500),
    offset: int = 0,
    min_impact: Optional[str] = None,
    max_af: Optional[float] = None,
    gene: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get ranked variants for a job with optional filters."""
    query = select(Variant).where(Variant.job_id == job_id)

    if min_impact:
        impact_order = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}
        min_val = impact_order.get(min_impact.upper(), 0)
        allowed = [k for k, v in impact_order.items() if v >= min_val]
        query = query.where(Variant.impact.in_(allowed))

    if max_af is not None:
        query = query.where(
            (Variant.gnomad_af <= max_af) | (Variant.gnomad_af == None)
        )

    if gene:
        query = query.where(Variant.gene.ilike(f"%{gene}%"))

    query = query.order_by(Variant.rank_position).offset(offset).limit(limit)
    result = await db.execute(query)
    variants = result.scalars().all()

    return {
        "job_id": job_id,
        "count": len(variants),
        "offset": offset,
        "variants": [
            {
                "id": v.id,
                "rank": v.rank_position,
                "chrom": v.chrom,
                "pos": v.pos,
                "ref": v.ref,
                "alt": v.alt,
                "gene": v.gene,
                "hgvs_c": v.hgvs_c,
                "hgvs_p": v.hgvs_p,
                "consequence": v.consequence,
                "impact": v.impact,
                "zygosity": v.zygosity,
                "gnomad_af": v.gnomad_af,
                "clinvar_significance": v.clinvar_significance,
                "clinvar_review_status": v.clinvar_review_status,
                "alphamissense_score": v.alphamissense_score,
                "alphamissense_class": v.alphamissense_class,
                "acmg_class": v.acmg_class,
                "acmg_rules": v.acmg_rules,
                "compound_het": v.compound_het,
                "validation_status": v.validation_status,
                "omim_disease": v.omim_disease,
                "omim_inheritance": v.omim_inheritance,
                "panelapp_panels": v.panelapp_panels,
                "rank_score": v.rank_score,
            }
            for v in variants
        ]
    }


@router.get("/{job_id}/variants/{variant_id}")
async def get_variant_detail(
    job_id: str, variant_id: str, db: AsyncSession = Depends(get_db)
):
    """Get full evidence card for a single variant."""
    result = await db.execute(
        select(Variant).where(Variant.id == variant_id, Variant.job_id == job_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Variant not found")

    return {
        "id": v.id,
        "job_id": v.job_id,
        "rank_position": v.rank_position,
        "rank_score": v.rank_score,
        "rank_details": v.rank_details,
        "chrom": v.chrom,
        "pos": v.pos,
        "ref": v.ref,
        "alt": v.alt,
        "variant_key": v.variant_key,
        "gene": v.gene,
        "transcript": v.transcript,
        "hgvs_c": v.hgvs_c,
        "hgvs_p": v.hgvs_p,
        "consequence": v.consequence,
        "impact": v.impact,
        "sample_id": v.sample_id,
        "zygosity": v.zygosity,
        "genotype": v.genotype,
        "gnomad_af": v.gnomad_af,
        "gnomad_af_popmax": v.gnomad_af_popmax,
        "clinvar_id": v.clinvar_id,
        "clinvar_significance": v.clinvar_significance,
        "clinvar_review_status": v.clinvar_review_status,
        "alphamissense_score": v.alphamissense_score,
        "alphamissense_class": v.alphamissense_class,
        "acmg_score": v.acmg_score,
        "acmg_class": v.acmg_class,
        "acmg_rules": v.acmg_rules,
        "compound_het": v.compound_het,
        "validation_status": v.validation_status,
        "omim_disease": v.omim_disease,
        "omim_inheritance": v.omim_inheritance,
        "panelapp_panels": v.panelapp_panels,
        "hpo_matched_terms": v.hpo_matched_terms,
        "raw_annotation": v.raw_annotation,
    }
