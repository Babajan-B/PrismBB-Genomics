"""Report generation & export routes."""
import io
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.job import Job
from app.models.variant import Variant

router = APIRouter()


@router.get("/{job_id}/report")
async def generate_report(
    job_id: str,
    format: str = Query("json", regex="^(json|csv|excel)$"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Export ranked variant table as JSON, CSV, or Excel."""
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")

    variants_result = await db.execute(
        select(Variant)
        .where(Variant.job_id == job_id)
        .order_by(Variant.rank_position)
        .limit(limit)
    )
    variants = variants_result.scalars().all()

    rows = [
        {
            "Rank": v.rank_position,
            "Gene": v.gene,
            "Variant": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
            "HGVS_c": v.hgvs_c,
            "HGVS_p": v.hgvs_p,
            "Consequence": v.consequence,
            "Impact": v.impact,
            "Zygosity": v.zygosity,
            "gnomAD_AF": v.gnomad_af,
            "ClinVar_Significance": v.clinvar_significance,
            "ClinVar_Review_Status": v.clinvar_review_status,
            "ClinVar_ID": v.clinvar_id,
            "PanelApp_Panels": "; ".join(v.panelapp_panels or []),
            "Rank_Score": v.rank_score,
        }
        for v in variants
    ]

    metadata = {
        "job_id": job_id,
        "filename": job.vcf_filename,
        "genome_build": job.genome_build,
        "pipeline_version": job.pipeline_version,
        "hpo_terms": job.hpo_terms,
        "generated_at": datetime.utcnow().isoformat(),
        "total_candidates": len(rows),
        "disclaimer": "Decision-support only. Requires expert clinical review.",
    }

    if format == "json":
        return {"metadata": metadata, "variants": rows}

    elif format == "csv":
        import csv
        buf = io.StringIO()
        # Write metadata header
        buf.write(f"# Job ID: {job_id}\n")
        buf.write(f"# File: {job.vcf_filename}\n")
        buf.write(f"# Build: {job.genome_build}\n")
        buf.write(f"# Generated: {metadata['generated_at']}\n")
        buf.write(f"# Pipeline: v{job.pipeline_version}\n\n")

        if rows:
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        content = buf.getvalue().encode()
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=vcf_report_{job_id}.csv"}
        )

    elif format == "excel":
        import pandas as pd
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            # Variant table
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name="Ranked Candidates", index=False)

            # Metadata sheet
            meta_df = pd.DataFrame([
                {"Field": k, "Value": str(v)}
                for k, v in metadata.items()
            ])
            meta_df.to_excel(writer, sheet_name="Run Metadata", index=False)

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=vcf_report_{job_id}.xlsx"}
        )
