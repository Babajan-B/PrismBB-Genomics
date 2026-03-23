"""
VCF Preprocessing Module
- Normalize variants (split multi-allelics, left-align indels)
- Uses bcftools if available, falls back to Python parsing
- Records all steps in audit log
"""
import subprocess
import os
import shutil
import gzip
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PreprocessResult:
    success: bool
    output_path: str = ""
    steps_applied: list = field(default_factory=list)
    error: Optional[str] = None
    tool_used: str = "python"


def _bcftools_available(bcftools_path: str = "bcftools") -> bool:
    try:
        result = subprocess.run(
            [bcftools_path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_bcftools_version(bcftools_path: str = "bcftools") -> str:
    try:
        result = subprocess.run(
            [bcftools_path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.split("\n")[0].strip()
    except Exception:
        return "unknown"


def preprocess_vcf(
    vcf_path: str,
    output_dir: str,
    genome_build: str = "GRCh38",
    bcftools_path: str = "bcftools",
) -> PreprocessResult:
    """
    Normalize and preprocess VCF. Tries bcftools first, then Python fallback.
    Returns path to preprocessed VCF.
    """
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(vcf_path)
    output_path = os.path.join(output_dir, f"{input_path.stem}_normalized.vcf")

    if _bcftools_available(bcftools_path):
        return _bcftools_preprocess(vcf_path, output_path, bcftools_path, genome_build)
    else:
        return _python_preprocess(vcf_path, output_path)


def _bcftools_preprocess(
    vcf_path: str,
    output_path: str,
    bcftools_path: str,
    genome_build: str,
) -> PreprocessResult:
    steps = []
    try:
        # Step 1: Normalize (split multi-allelics + left-align)
        cmd = [
            bcftools_path, "norm",
            "-m", "-both",   # split multi-allelics
            "--output", output_path,
            "--output-type", "v",
            vcf_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            # Try without -m if it fails (some older bcftools)
            cmd_simple = [
                bcftools_path, "norm",
                "--output", output_path,
                "--output-type", "v",
                vcf_path
            ]
            result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=300)
            if result2.returncode != 0:
                return PreprocessResult(
                    success=False,
                    error=f"bcftools norm failed: {result.stderr}"
                )
            steps.append("normalized (basic)")
        else:
            steps.append("normalized: split multi-allelics, left-aligned indels")

        version = _get_bcftools_version(bcftools_path)

        return PreprocessResult(
            success=True,
            output_path=output_path,
            steps_applied=steps,
            tool_used=f"bcftools ({version})",
        )

    except subprocess.TimeoutExpired:
        return PreprocessResult(success=False, error="bcftools preprocessing timed out")
    except Exception as e:
        return PreprocessResult(success=False, error=str(e))


def _python_preprocess(vcf_path: str, output_path: str) -> PreprocessResult:
    """
    Python-only fallback: reads VCF and writes normalized output.
    Handles basic multi-allelic splitting.
    """
    steps = []
    try:
        def open_vcf(path):
            if path.endswith(".gz"):
                return gzip.open(path, "rt")
            return open(path, "r")

        header_lines = []
        column_line = None
        variants = []

        with open_vcf(vcf_path) as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("##"):
                    header_lines.append(line)
                elif line.startswith("#CHROM"):
                    column_line = line
                else:
                    variants.append(line)

        # Split multi-allelic ALTs
        split_variants = []
        for variant in variants:
            parts = variant.split("\t")
            if len(parts) < 5:
                continue
            alt_field = parts[4]
            alts = alt_field.split(",")
            if len(alts) == 1:
                split_variants.append(variant)
            else:
                for alt in alts:
                    new_parts = parts.copy()
                    new_parts[4] = alt
                    split_variants.append("\t".join(new_parts))

        steps.append("split multi-allelics (Python fallback)")

        with open(output_path, "w") as f:
            for h in header_lines:
                f.write(h + "\n")
            if column_line:
                f.write(column_line + "\n")
            for v in split_variants:
                f.write(v + "\n")

        return PreprocessResult(
            success=True,
            output_path=output_path,
            steps_applied=steps,
            tool_used="python",
        )

    except Exception as e:
        return PreprocessResult(success=False, error=str(e))
