"""Upload & Job creation route."""
import os
import uuid
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import Job, JobStatus
from app.pipeline.ingestion import validate_vcf
from app.pipeline.runner import run_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_vcf(
    background_tasks: BackgroundTasks,
    vcf_file: UploadFile = File(...),
    genome_build: str = Form("GRCh38"),
    hpo_terms: str = Form(""),        # comma-separated: HP:0001250,HP:0000822
    gene_list: str = Form(""),        # comma-separated gene symbols
    clinical_mode: bool = Form(False), # restrict to 81 ACMG actionable genes
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a VCF file and start the analysis pipeline.
    Returns job_id for status polling.
    """
    # Validate file extension
    filename = os.path.basename(vcf_file.filename or "upload.vcf")
    if not (filename.endswith(".vcf") or filename.endswith(".vcf.gz")):
        raise HTTPException(400, "Only .vcf or .vcf.gz files are accepted")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(settings.upload_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)

    vcf_path = os.path.join(job_dir, filename)

    # Save uploaded file
    content = await vcf_file.read()
    with open(vcf_path, "wb") as f:
        f.write(content)

    # Validate immediately so malformed uploads return a useful error
    ingestion_result = validate_vcf(vcf_path)
    if not ingestion_result.is_valid:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(400, f"Invalid VCF upload: {ingestion_result.error}")

    # Parse HPO terms and gene list
    hpo_list = [t.strip() for t in hpo_terms.split(",") if t.strip()] if hpo_terms else []
    gene_list_parsed = [g.strip() for g in gene_list.split(",") if g.strip()] if gene_list else []

    # Create job record
    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        vcf_filename=filename,
        vcf_path=vcf_path,
        genome_build=genome_build,
        hpo_terms=hpo_list,
        gene_list=gene_list_parsed,
        clinical_mode=clinical_mode,
    )
    db.add(job)
    await db.commit()

    # Start pipeline in background
    background_tasks.add_task(
        _run_pipeline_task,
        job_id, vcf_path, genome_build, hpo_list, gene_list_parsed, clinical_mode
    )

    logger.info(f"Created job {job_id} for file {filename}")

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis pipeline started. Poll /api/jobs/{job_id}/status for updates.",
        "filename": filename,
    }


async def _run_pipeline_task(job_id, vcf_path, genome_build, hpo_terms, gene_list, clinical_mode=False):
    """Wrapper to run pipeline with a fresh DB session."""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await run_pipeline(job_id, vcf_path, genome_build, hpo_terms, gene_list, session, clinical_mode)
