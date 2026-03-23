"""
ACMG Rule-Based Classifier
Implements core ACMG/AMP 2015 criteria for pathogenicity classification.

Rules implemented:
  PVS1  — Loss-of-function in a gene where LOF is disease mechanism (8 pts)
  PM2   — Absent/rare in population databases (AF < 0.001 or unknown)  (2 pts)
  PM4   — Protein length change (inframe indel, stop_lost)              (2 pts)
  PP3   — Multiple computational evidence of deleterious effect         (1 pt)
  BA1   — Allele frequency > 5% in gnomAD                             (-10 pts)
  BS1   — Allele frequency > 1% in gnomAD                              (-3 pts)
  BP4   — Multiple computational evidence of benign                    (-1 pt)

Tiers:
  score >= 8  → Pathogenic
  score >= 6  → Likely Pathogenic
  score >= 3  → VUS (Variant of Uncertain Significance)
  score >= 1  → Likely Benign
  score <  1  → Benign
"""

from typing import Optional


# LOF consequence terms that trigger PVS1
LOF_TERMS = {
    "stop_gained",
    "frameshift_variant",
    "splice_acceptor_variant",
    "splice_donor_variant",
    "start_lost",
    "transcript_ablation",
    "exon_loss_variant",
}

# Inframe change terms that trigger PM4
INFRAME_TERMS = {
    "inframe_insertion",
    "inframe_deletion",
    "stop_lost",
    "protein_altering_variant",
}


def classify_acmg(
    consequence: Optional[str],
    impact: Optional[str],
    gnomad_af: Optional[float],
    clinvar_significance: Optional[str],
) -> dict:
    """
    Apply ACMG scoring rules to a variant.
    Returns dict with:
      - acmg_score: int
      - acmg_class: str (Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign)
      - acmg_rules: list of triggered rule codes with points
      - acmg_evidence: dict of per-rule evidence
    """
    score = 0
    rules_triggered: list[str] = []
    evidence: dict = {}

    csq_terms: set[str] = set()
    if consequence:
        csq_terms = {t.strip() for t in consequence.replace("&", ",").split(",")}

    # ── Pathogenic evidence ──────────────────────────────────────────────
    # PVS1: LOF variant in disease gene
    if csq_terms & LOF_TERMS:
        score += 8
        rules_triggered.append("PVS1")
        evidence["PVS1"] = f"LOF variant: {consequence}"

    # PM2: Absent/ultra-rare in population
    if gnomad_af is None:
        score += 2
        rules_triggered.append("PM2")
        evidence["PM2"] = "Absent from gnomAD"
    elif gnomad_af < 0.001:
        score += 2
        rules_triggered.append("PM2")
        evidence["PM2"] = f"Ultra-rare in gnomAD (AF={gnomad_af:.2e})"

    # PM4: Protein length change (inframe indel or stop-loss)
    if csq_terms & INFRAME_TERMS:
        score += 2
        rules_triggered.append("PM4")
        evidence["PM4"] = f"Protein length change: {consequence}"

    # PP3: Computational evidence (using impact as proxy)
    if impact in ("HIGH", "MODERATE") and "PVS1" not in rules_triggered:
        score += 1
        rules_triggered.append("PP3")
        evidence["PP3"] = f"Predicted {impact} impact by consequence annotation"

    # ClinVar pathogenic bonus (not strict ACMG but clinically informative)
    if clinvar_significance:
        sig = clinvar_significance.lower()
        if "pathogenic" in sig and "likely" not in sig:
            score += 3
            rules_triggered.append("ClinVar_P")
            evidence["ClinVar_P"] = clinvar_significance
        elif "likely pathogenic" in sig:
            score += 2
            rules_triggered.append("ClinVar_LP")
            evidence["ClinVar_LP"] = clinvar_significance

    # ── Benign evidence ──────────────────────────────────────────────────
    # BA1: Common variant (AF > 5%)
    if gnomad_af is not None and gnomad_af > 0.05:
        score -= 10
        rules_triggered.append("BA1")
        evidence["BA1"] = f"Common variant in gnomAD (AF={gnomad_af:.3f})"

    # BS1: Relatively common (AF > 1%)
    elif gnomad_af is not None and gnomad_af > 0.01:
        score -= 3
        rules_triggered.append("BS1")
        evidence["BS1"] = f"Relatively common in gnomAD (AF={gnomad_af:.3f})"

    # BP4: Benign computational evidence (MODIFIER non-coding)
    if impact == "MODIFIER" and not (csq_terms & LOF_TERMS):
        score -= 1
        rules_triggered.append("BP4")
        evidence["BP4"] = "Non-coding MODIFIER variant"

    # ClinVar benign
    if clinvar_significance:
        sig = clinvar_significance.lower()
        if sig in ("benign", "likely benign"):
            score -= 3
            rules_triggered.append("ClinVar_B")
            evidence["ClinVar_B"] = clinvar_significance

    # ── Classification ───────────────────────────────────────────────────
    if score >= 8:
        acmg_class = "Pathogenic"
    elif score >= 6:
        acmg_class = "Likely Pathogenic"
    elif score >= 3:
        acmg_class = "VUS"
    elif score >= 1:
        acmg_class = "Likely Benign"
    else:
        acmg_class = "Benign"

    return {
        "acmg_score":   score,
        "acmg_class":   acmg_class,
        "acmg_rules":   rules_triggered,
        "acmg_evidence": evidence,
    }


def detect_compound_hets(variants: list[dict]) -> dict[str, list[str]]:
    """
    Identify genes with ≥2 heterozygous variants (potential compound heterozygotes).
    Returns {gene → [variant_key, ...]} for genes with compound het candidates.

    Compound heterozygosity: two HET variants in the same gene on different
    alleles — a key mechanism for autosomal recessive disease.
    """
    from collections import defaultdict

    gene_het_map: dict[str, list[str]] = defaultdict(list)

    for v in variants:
        gene = v.get("gene")
        zyg  = (v.get("zygosity") or "").upper()
        impact = v.get("impact") or "MODIFIER"

        # Only consider HET variants with functional impact
        if gene and zyg == "HET" and impact in ("HIGH", "MODERATE"):
            key = f"{v.get('chrom')}:{v.get('pos')}:{v.get('ref')}:{v.get('alt')}"
            gene_het_map[gene].append(key)

    # Return only genes with ≥2 HET candidates
    return {
        gene: keys
        for gene, keys in gene_het_map.items()
        if len(keys) >= 2
    }
