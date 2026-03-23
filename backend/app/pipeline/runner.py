"""
Pipeline Runner — Background job processor
Orchestrates: ingestion → preprocessing → annotation → ranking → DB storage

Annotation strategy (no local genome required):
  Phase 1  MyVariant.info bulk  — ALL variants   (~5 min for 100k)
  Phase 2  Ensembl VEP REST     — rare variants only (~20-30 min)
  Phase 3  PanelApp             — once per unique gene

All variants that pass the scoring threshold are stored.
No arbitrary variant caps.
"""
import os
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.job import Job, JobStatus
from app.models.variant import Variant
from app.models.audit import AuditLog
from app.pipeline.ingestion import validate_vcf
from app.pipeline.preprocessing import preprocess_vcf
from app.pipeline.annotation import annotate_variants_full, parse_vcf_variants
from app.pipeline.ranking import rank_variants
from app.pipeline.phenotype import enrich_hpo_context
from app.pipeline.check_agent import validate_top_candidates

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────
async def _log(
    db: AsyncSession,
    job_id: str,
    step: str,
    message: str,
    level: str = "INFO",
    details: str = None,
):
    log = AuditLog(
        id=str(uuid.uuid4()),
        job_id=job_id,
        step=step,
        level=level,
        message=message,
        details=details,
    )
    db.add(log)
    await db.commit()


async def _update_job_status(
    db: AsyncSession, job_id: str, status: JobStatus, **kwargs
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job:
        job.status = status
        for k, v in kwargs.items():
            setattr(job, k, v)
        await db.commit()


# ── Main pipeline ──────────────────────────────────────────────────────────
async def run_pipeline(
    job_id: str,
    vcf_path: str,
    genome_build: str,
    hpo_terms: list,
    gene_list: list,
    db: AsyncSession,
    clinical_mode: bool = False,
):
    """
    Full automated pipeline — no user intervention required.

    Steps:
      1  Validate VCF
      2  Normalise (bcftools or Python fallback)
      3  Parse ALL variants
      4a Phase 1 annotation — MyVariant bulk (ALL variants)
      4b Phase 2 annotation — VEP REST (rare/unknown only)
      4c Phase 3 annotation — PanelApp (unique genes)
      5  Score & rank
      6  Store ALL candidates to database
    """
    logger.info(f"Pipeline starting for job {job_id}")

    try:
        # ─── Step 1: Ingestion & Validation ─────────────────────────────
        await _update_job_status(db, job_id, JobStatus.INGESTING)
        await _log(db, job_id, "INGESTION", "Starting VCF validation")

        ingestion_result = validate_vcf(vcf_path)

        if not ingestion_result.is_valid:
            await _update_job_status(
                db, job_id, JobStatus.FAILED,
                error_message=f"VCF validation failed: {ingestion_result.error}",
            )
            await _log(
                db, job_id, "INGESTION",
                f"Validation failed: {ingestion_result.error}", "ERROR",
            )
            return

        detected_build = ingestion_result.genome_build or genome_build
        await _update_job_status(
            db, job_id, JobStatus.INGESTING,
            genome_build=detected_build,
            sample_count=len(ingestion_result.sample_ids),
            variant_count=ingestion_result.variant_count,
            qc_summary=ingestion_result.qc_summary,
        )
        await _log(
            db, job_id, "INGESTION",
            f"VCF valid: {ingestion_result.variant_count:,} variants, "
            f"{len(ingestion_result.sample_ids)} sample(s), build={detected_build}",
            details=str(ingestion_result.qc_summary),
        )

        # ─── Step 2: Preprocessing ───────────────────────────────────────
        await _update_job_status(db, job_id, JobStatus.PREPROCESSING)
        await _log(db, job_id, "PREPROCESSING", "Starting normalisation")

        work_dir = os.path.join(settings.upload_dir, job_id)
        prep_result = preprocess_vcf(
            vcf_path, work_dir, detected_build, settings.bcftools_path
        )

        if not prep_result.success:
            await _log(
                db, job_id, "PREPROCESSING",
                f"Normalisation warning: {prep_result.error} — using original file",
                "WARNING",
            )
            preprocessed_path = vcf_path
        else:
            preprocessed_path = prep_result.output_path
            await _log(
                db, job_id, "PREPROCESSING",
                f"Normalisation complete: {', '.join(prep_result.steps_applied)}",
                details=f"tool={prep_result.tool_used}",
            )

        # ─── Step 3: Parse ALL variants ───────────────────────────────────
        await _update_job_status(db, job_id, JobStatus.ANNOTATING)
        await _log(db, job_id, "ANNOTATION", "Parsing all variant records from VCF")

        raw_variants = parse_vcf_variants(preprocessed_path)
        total = len(raw_variants)

        await _log(
            db, job_id, "ANNOTATION",
            f"Parsed {total:,} variant records — full annotation will now run "
            f"automatically (no selection cap)",
            details=f"genome_build={detected_build}",
        )

        # ─── Step 4: Full Annotation (3 phases, no variant cap) ──────────
        await _log(
            db, job_id, "ANNOTATION",
            f"Phase 1/3: Bulk gnomAD + ClinVar lookup for all {total:,} variants "
            f"via MyVariant.info (batches of 1 000)",
        )

        # Progress callback writes incremental audit logs
        last_logged: dict = {"mv": 0, "vep": 0}

        async def _progress(phase: str, done: int, total_: int):
            pct = int(done / total_ * 100) if total_ else 0
            if phase == "myvariant" and pct - last_logged["mv"] >= 20:
                last_logged["mv"] = pct
                await _log(
                    db, job_id, "ANNOTATION",
                    f"  Phase 1 progress: {done:,}/{total_:,} variants ({pct}%)",
                )
            elif phase == "vep" and pct - last_logged["vep"] >= 25:
                last_logged["vep"] = pct
                await _log(
                    db, job_id, "ANNOTATION",
                    f"  Phase 2 progress: {done:,}/{total_:,} rare variants ({pct}%)",
                )

        annotation_results = await annotate_variants_full(
            raw_variants,
            genome_build=detected_build,
            af_threshold=0.05,
            progress_cb=_progress,
        )

        # Count what was annotated in each phase
        mv_hit  = sum(1 for ar in annotation_results if ar.gnomad_af is not None or ar.clinvar_significance)
        vep_hit = sum(1 for ar in annotation_results if ar.gene)
        await _log(
            db, job_id, "ANNOTATION",
            f"Annotation complete: {mv_hit:,} variants with gnomAD/ClinVar data, "
            f"{vep_hit:,} with VEP gene/consequence annotation",
        )

        # ─── Step 5: Merge & Rank ────────────────────────────────────────
        await _update_job_status(db, job_id, JobStatus.RANKING)
        await _log(db, job_id, "RANKING", "Scoring and ranking all annotated variants")

        merged = [
            {
                **rv,
                "gene":                ar.gene,
                "transcript":          ar.transcript,
                "hgvs_c":              ar.hgvs_c,
                "hgvs_p":              ar.hgvs_p,
                "consequence":         ar.consequence,
                "impact":              ar.impact,
                "gnomad_af":             ar.gnomad_af,
                "gnomad_af_popmax":      ar.gnomad_af_popmax,
                "clinvar_id":            ar.clinvar_id,
                "clinvar_significance":  ar.clinvar_significance,
                "clinvar_review_status": ar.clinvar_review_status,
                "alphamissense_score":   ar.alphamissense_score,
                "alphamissense_class":   ar.alphamissense_class,
                "panelapp_panels":       ar.panelapp_panels,
                "raw_annotation":        ar.raw_vep,
            }
            for rv, ar in zip(raw_variants, annotation_results)
        ]

        ranked = rank_variants(merged, query_hpo_terms=hpo_terms, clinical_mode=clinical_mode)

        # ─── HPO phenotype enrichment (PubCaseFinder) ────────────────────
        hpo_context = {}
        if hpo_terms:
            await _log(db, job_id, "RANKING",
                       f"Querying PubCaseFinder with {len(hpo_terms)} HPO terms")
            hpo_context = await enrich_hpo_context(hpo_terms)
            candidates = hpo_context.get("disease_candidates", [])
            if candidates:
                names = ", ".join(c["disease_name"] for c in candidates[:3])
                await _log(db, job_id, "RANKING",
                           f"PubCaseFinder top disease candidates: {names}",
                           details=str([c["disease_name"] for c in candidates]))

        common_skipped = sum(
            1 for v in merged
            if v.get("gnomad_af") is not None and v["gnomad_af"] > 0.05
        )
        await _log(
            db, job_id, "RANKING",
            f"Ranked {len(ranked):,} candidates "
            f"(from {total:,} total; {common_skipped:,} common AF>5% skipped; "
            f"{total - common_skipped - len(ranked):,} scored below threshold)",
            details=(
                f"top_score={ranked[0]['rank_score']:.3f}, "
                f"min_score={ranked[-1]['rank_score']:.3f}"
            ) if ranked else "no_candidates",
        )

        # ─── Step 5b: Check Agent — OMIM validation loop ─────────────────
        if ranked:
            mode_label = "ACMG clinical mode" if clinical_mode else "research mode"
            await _log(db, job_id, "RANKING",
                       f"Check Agent: validating top 30 candidates against OMIM ({mode_label})")
            ranked = await validate_top_candidates(ranked, top_n=30)
            confirmed = sum(1 for v in ranked[:30] if v.get("validation_status") == "confirmed")
            conflict  = sum(1 for v in ranked[:30] if v.get("validation_status") == "conflict")
            await _log(db, job_id, "RANKING",
                       f"Check Agent complete: {confirmed} confirmed, {conflict} conflicts in top 30")

        # ─── Step 6: Store ALL ranked variants ───────────────────────────
        await _log(
            db, job_id, "RANKING",
            f"Storing {len(ranked):,} candidates to database",
        )

        COMMIT_BATCH = 500   # commit in chunks to avoid huge transactions
        for i, rv in enumerate(ranked):
            v = Variant(
                id=str(uuid.uuid4()),
                job_id=job_id,
                chrom=rv.get("chrom", ""),
                pos=rv.get("pos", 0),
                ref=rv.get("ref", ""),
                alt=rv.get("alt", ""),
                variant_key=f"{rv.get('chrom')}:{rv.get('pos')}:{rv.get('ref')}:{rv.get('alt')}",
                sample_id=rv.get("sample_id"),
                zygosity=rv.get("zygosity"),
                genotype=rv.get("genotype"),
                gene=rv.get("gene"),
                transcript=rv.get("transcript"),
                hgvs_c=rv.get("hgvs_c"),
                hgvs_p=rv.get("hgvs_p"),
                consequence=rv.get("consequence"),
                impact=rv.get("impact"),
                clinvar_id=rv.get("clinvar_id"),
                clinvar_significance=rv.get("clinvar_significance"),
                clinvar_review_status=rv.get("clinvar_review_status"),
                gnomad_af=rv.get("gnomad_af"),
                gnomad_af_popmax=rv.get("gnomad_af_popmax"),
                alphamissense_score=rv.get("alphamissense_score"),
                alphamissense_class=rv.get("alphamissense_class"),
                acmg_score=rv.get("rank_details", {}).get("acmg_score"),
                acmg_class=rv.get("rank_details", {}).get("acmg_class"),
                acmg_rules=rv.get("rank_details", {}).get("acmg_rules", []),
                compound_het=rv.get("rank_details", {}).get("compound_het", False),
                validation_status=rv.get("validation_status"),
                omim_disease=rv.get("omim_disease"),
                omim_inheritance=rv.get("omim_inheritance"),
                panelapp_panels=rv.get("panelapp_panels", []),
                hpo_matched_terms=rv.get("hpo_matched_terms", []),
                rank_score=rv.get("rank_score"),
                rank_position=rv.get("rank_position"),
                rank_details=rv.get("rank_details", {}),
                raw_annotation=rv.get("raw_annotation", {}),
            )
            db.add(v)
            # Commit every COMMIT_BATCH rows to avoid memory pressure
            if (i + 1) % COMMIT_BATCH == 0:
                await db.commit()

        await db.commit()   # final commit for any remainder

        await _update_job_status(
            db, job_id, JobStatus.COMPLETED,
            variant_count=len(ranked),
        )
        await _log(
            db, job_id, "COMPLETED",
            f"Pipeline finished. {len(ranked):,} candidates stored and ready in workspace.",
        )
        logger.info(f"Pipeline complete for job {job_id}: {len(ranked)} variants stored")

    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}", exc_info=True)
        await _update_job_status(
            db, job_id, JobStatus.FAILED,
            error_message=str(e),
        )
        await _log(db, job_id, "ERROR", f"Pipeline failed: {str(e)}", "ERROR")
