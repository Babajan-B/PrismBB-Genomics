"""
Backend tests for ingestion, preprocessing, and ranking.
"""
import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SAMPLE_VCF = os.path.join(os.path.dirname(__file__), "data", "sample.vcf")


# ─── Ingestion Tests ──────────────────────────────────────────────────────────

def test_valid_vcf_ingestion():
    from app.pipeline.ingestion import validate_vcf
    result = validate_vcf(SAMPLE_VCF)
    assert result.is_valid, f"Ingestion failed: {result.error}"
    assert result.variant_count == 10
    assert result.genome_build in ("GRCh38", "GRCh37")
    assert len(result.sample_ids) > 0
    assert "variant_count" in result.qc_summary


def test_invalid_vcf_ingestion(tmp_path):
    from app.pipeline.ingestion import validate_vcf
    bad_vcf = tmp_path / "bad.vcf"
    bad_vcf.write_text("NOT A VCF FILE\nsome garbage\n")
    result = validate_vcf(str(bad_vcf))
    assert not result.is_valid


def test_nonexistent_vcf():
    from app.pipeline.ingestion import validate_vcf
    result = validate_vcf("/nonexistent/path.vcf")
    assert not result.is_valid
    assert "not found" in result.error.lower()


def test_vcf_genome_build_detection():
    from app.pipeline.ingestion import _detect_build
    lines_38 = ["##reference=GRCh38.fa", "##contig=<ID=chr1,length=248956422>"]
    lines_37 = ["##reference=GRCh37.fa"]
    assert _detect_build(lines_38) == "GRCh38"
    assert _detect_build(lines_37) == "GRCh37"


# ─── Preprocessing Tests ──────────────────────────────────────────────────────

def test_python_preprocessing(tmp_path):
    from app.pipeline.preprocessing import _python_preprocess
    out_path = str(tmp_path / "out.vcf")
    result = _python_preprocess(SAMPLE_VCF, out_path)
    assert result.success, f"Preprocessing failed: {result.error}"
    assert os.path.exists(result.output_path)
    assert result.tool_used == "python"


def test_bcftools_detection():
    from app.pipeline.preprocessing import _bcftools_available
    # We just check it doesn't crash
    available = _bcftools_available("bcftools")
    assert isinstance(available, bool)


# ─── VCF Parsing Tests ────────────────────────────────────────────────────────

def test_parse_vcf_variants():
    from app.pipeline.annotation import parse_vcf_variants
    variants = parse_vcf_variants(SAMPLE_VCF)
    assert len(variants) == 10
    v = variants[0]
    assert "chrom" in v
    assert "pos" in v
    assert "ref" in v
    assert "alt" in v
    assert v["chrom"] == "chr13"
    assert isinstance(v["pos"], int)


# ─── Ranking Tests ────────────────────────────────────────────────────────────

def test_rarity_score():
    from app.pipeline.ranking import _rarity_score
    assert _rarity_score(0) == 1.0
    assert _rarity_score(0.00005) >= 0.9
    assert _rarity_score(0.01) < 0.6
    assert _rarity_score(0.1) == 0.0
    assert 0 < _rarity_score(None) < 1  # unknown = moderate


def test_clinvar_score():
    from app.pipeline.ranking import _clinvar_score
    assert _clinvar_score("Pathogenic") == 1.0
    assert _clinvar_score("Likely pathogenic") == 0.8
    assert _clinvar_score("Benign") == 0.0
    assert _clinvar_score(None) == 0.0


def test_impact_score():
    from app.pipeline.ranking import _impact_score
    assert _impact_score("HIGH", "stop_gained") >= 0.9
    assert _impact_score("MODERATE", "missense_variant") >= 0.6
    assert _impact_score("MODIFIER", None) == 0.0


def test_rank_variants():
    from app.pipeline.ranking import rank_variants
    variants = [
        {"chrom": "chr1", "pos": 100, "ref": "A", "alt": "T", "gnomad_af": 0, "impact": "HIGH", "consequence": "stop_gained", "clinvar_significance": "Pathogenic", "zygosity": "HET", "panelapp_panels": ["Epilepsy"]},
        {"chrom": "chr1", "pos": 200, "ref": "C", "alt": "G", "gnomad_af": 0.1, "impact": "MODIFIER", "consequence": "synonymous_variant", "clinvar_significance": None, "zygosity": "HET", "panelapp_panels": []},
    ]
    ranked = rank_variants(variants)
    assert len(ranked) >= 1
    # Ultra-rare pathogenic HIGH should rank first
    assert ranked[0]["gnomad_af"] == 0
    assert ranked[0]["rank_position"] == 1
    # Score breakdown present
    assert "rank_details" in ranked[0]


def test_score_variant_comprehensive():
    from app.pipeline.ranking import score_variant
    variant = {
        "gnomad_af": 0.00001,
        "impact": "HIGH",
        "consequence": "stop_gained",
        "clinvar_significance": "Pathogenic",
        "zygosity": "HET",
        "gene": "BRCA2",
        "panelapp_panels": ["Hereditary Breast and Ovarian Cancer"],
        "hpo_matched_terms": [],
    }
    score, details = score_variant(variant, query_hpo_terms=[], hpo_gene_map={})
    assert 0 < score <= 1.0
    assert details.rarity_score > 0.8
    assert details.impact_score >= 0.9
    assert details.clinvar_score == 1.0
    assert details.total_score == pytest.approx(score, rel=1e-6)
    assert "reasoning" in details.__dict__
