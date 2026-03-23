"""Audit log routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.audit import AuditLog

router = APIRouter()


@router.get("/{job_id}/audit")
async def get_audit_log(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve the full audit trail for an analysis job."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.job_id == job_id)
        .order_by(AuditLog.timestamp)
    )
    logs = result.scalars().all()
    if not logs:
        raise HTTPException(404, "No audit log found for this job")
    return [
        {
            "id": l.id,
            "step": l.step,
            "level": l.level,
            "message": l.message,
            "details": l.details,
            "timestamp": str(l.timestamp),
            "pipeline_version": l.pipeline_version,
            "tool_version": l.tool_version,
        }
        for l in logs
    ]
