"""
VCF Ingestion Module
- Validates VCF format (headers, mandatory columns)
- Detects genome build from VCF headers
- Counts samples and variants
- Generates QC summary
"""
import gzip
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, field


MANDATORY_COLUMNS = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]


@dataclass
class IngestionResult:
    is_valid: bool
    error: Optional[str] = None
    genome_build: str = "GRCh38"
    sample_ids: list = field(default_factory=list)
    variant_count: int = 0
    qc_summary: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def _open_vcf(path: str):
    """Open VCF, handling both gzipped and plain."""
    if path.endswith(".gz") or path.endswith(".bgz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def _detect_build(header_lines: list[str]) -> str:
    """Detect genome build from VCF header lines."""
    for line in header_lines:
        line_lower = line.lower()
        if "grch38" in line_lower or "hg38" in line_lower or "GRCh38" in line:
            return "GRCh38"
        if "grch37" in line_lower or "hg19" in line_lower or "GRCh37" in line:
            return "GRCh37"
        if "reference=" in line_lower:
            if "38" in line:
                return "GRCh38"
            if "37" in line or "19" in line:
                return "GRCh37"
        # Check contig lines for chr naming
        if "##contig" in line_lower:
            if "GRCh38" in line:
                return "GRCh38"
            if "GRCh37" in line:
                return "GRCh37"
    return "GRCh38"  # default


def validate_vcf(vcf_path: str) -> IngestionResult:
    """Validate VCF and return ingestion result."""
    result = IngestionResult(is_valid=False)

    if not os.path.exists(vcf_path):
        result.error = f"File not found: {vcf_path}"
        return result

    try:
        header_lines = []
        column_header = None
        variant_count = 0
        sample_ids = []

        with _open_vcf(vcf_path) as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("##"):
                    header_lines.append(line)
                elif line.startswith("#CHROM"):
                    column_header = line
                    parts = column_header.split("\t")
                    # Columns 9+ are sample IDs
                    if len(parts) > 9:
                        sample_ids = parts[9:]
                    elif len(parts) == 9:
                        sample_ids = ["Sample_1"]
                    # Validate mandatory columns
                    for col in MANDATORY_COLUMNS:
                        if col not in parts:
                            result.error = f"Missing mandatory column: {col}"
                            return result
                else:
                    if column_header is None:
                        result.error = (
                            "VCF is missing the mandatory #CHROM header line. "
                            "The file may be truncated or malformed."
                        )
                        return result
                    variant_count += 1

        if column_header is None:
            result.error = (
                "VCF is missing the mandatory #CHROM header line. "
                "The file may be truncated or malformed."
            )
            return result

        if variant_count == 0:
            result.warnings.append("VCF contains no variant records")

        genome_build = _detect_build(header_lines)

        # QC summary
        chrom_counts = _count_by_chrom(vcf_path)
        has_format = any("##FORMAT" in h for h in header_lines)

        result.is_valid = True
        result.genome_build = genome_build
        result.sample_ids = sample_ids
        result.variant_count = variant_count
        result.qc_summary = {
            "variant_count": variant_count,
            "sample_count": len(sample_ids),
            "sample_ids": sample_ids,
            "genome_build": genome_build,
            "header_line_count": len(header_lines),
            "has_format_fields": has_format,
            "chrom_distribution": chrom_counts,
            "warnings": result.warnings,
        }

    except Exception as e:
        result.error = f"Failed to parse VCF: {str(e)}"

    return result


def _count_by_chrom(vcf_path: str) -> dict:
    """Count variants per chromosome (first 10k records)."""
    counts: dict = {}
    try:
        with _open_vcf(vcf_path) as f:
            processed = 0
            for line in f:
                if line.startswith("#"):
                    continue
                if processed >= 10000:
                    break
                chrom = line.split("\t")[0]
                counts[chrom] = counts.get(chrom, 0) + 1
                processed += 1
    except Exception:
        pass
    return counts
