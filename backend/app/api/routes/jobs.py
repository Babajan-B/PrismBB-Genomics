"""Jobs status & listing routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.job import Job

router = APIRouter()


@router.get("")
async def list_jobs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(limit))
    jobs = result.scalars().all()
    return {
        "jobs": [
            {
                "id": j.id,
                "status": j.status,
                "filename": j.vcf_filename,
                "genome_build": j.genome_build,
                "variant_count": j.variant_count,
                "sample_count": j.sample_count,
                "created_at": str(j.created_at),
                "hpo_terms": j.hpo_terms,
            }
            for j in jobs
        ]
    }


@router.get("/{job_id}/status")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return {
        "id": job.id,
        "status": job.status,
        "filename": job.vcf_filename,
        "genome_build": job.genome_build,
        "sample_count": job.sample_count,
        "variant_count": job.variant_count,
        "hpo_terms": job.hpo_terms,
        "qc_summary": job.qc_summary,
        "error_message": job.error_message,
        "pipeline_version": job.pipeline_version,
        "created_at": str(job.created_at),
        "updated_at": str(job.updated_at),
    }
