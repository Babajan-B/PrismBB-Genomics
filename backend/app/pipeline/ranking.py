"""
Variant Ranking & Prioritization Module
Composite scoring: rarity + impact + ClinVar + ACMG + phenotype + inheritance + panel
"""
from typing import Optional
from dataclasses import dataclass, field
from app.pipeline.acmg import classify_acmg, detect_compound_hets
from app.pipeline.clinical_genes import ACMG_ACTIONABLE_GENES


# Scoring weights (sum to 1.0)
WEIGHTS = {
    "rarity": 0.25,
    "impact": 0.25,
    "clinvar": 0.20,
    "phenotype": 0.15,
    "inheritance": 0.10,
    "panel": 0.05,
}

# Consequence impact scores (HIGH=1.0, MODIFIER=0.0)
IMPACT_SCORES = {
    "HIGH": 1.0,
    "MODERATE": 0.6,
    "LOW": 0.3,
    "MODIFIER": 0.0,
}

# Consequence term bonuses
HIGH_IMPACT_TERMS = {
    "stop_gained", "frameshift_variant", "splice_acceptor_variant",
    "splice_donor_variant", "start_lost", "stop_lost",
    "transcript_ablation", "transcript_amplification"
}
MODERATE_IMPACT_TERMS = {
    "missense_variant", "inframe_insertion", "inframe_deletion",
    "protein_altering_variant", "splice_region_variant"
}

# ClinVar significance scores — ordered from most to least specific
# (longer/more-specific strings must come first to avoid substring collision)
CLINVAR_SCORES = [
    ("likely pathogenic", 0.8),
    ("pathogenic", 1.0),
    ("uncertain significance", 0.3),
    ("likely benign", 0.1),
    ("benign", 0.0),
]


@dataclass
class RankDetails:
    rarity_score: float = 0.0
    impact_score: float = 0.0
    clinvar_score: float = 0.0
    phenotype_score: float = 0.0
    inheritance_score: float = 0.0
    panel_score: float = 0.0
    acmg_score: int = 0
    acmg_class: str = ""
    acmg_rules: list = field(default_factory=list)
    compound_het: bool = False
    total_score: float = 0.0
    reasoning: dict = field(default_factory=dict)


def _rarity_score(gnomad_af: Optional[float]) -> float:
    """Score based on population frequency. Rarer = higher score."""
    if gnomad_af is None:
        return 0.7  # unknown frequency - moderate score
    if gnomad_af == 0:
        return 1.0
    if gnomad_af < 0.0001:
        return 0.95
    if gnomad_af < 0.001:
        return 0.8
    if gnomad_af < 0.01:
        return 0.5
    if gnomad_af < 0.05:
        return 0.2
    return 0.0  # common variant


def _impact_score(impact: Optional[str], consequence: Optional[str]) -> float:
    """Score based on predicted functional impact."""
    base = IMPACT_SCORES.get(impact or "MODIFIER", 0.0)
    # Bonus for specific high-impact terms
    if consequence:
        terms = set(consequence.lower().split(","))
        if terms & HIGH_IMPACT_TERMS:
            return max(base, 0.9)
        if terms & MODERATE_IMPACT_TERMS:
            return max(base, 0.6)
    return base


def _clinvar_score(clinvar_significance: Optional[str]) -> float:
    """Score based on ClinVar clinical significance."""
    if not clinvar_significance:
        return 0.0
    sig_lower = clinvar_significance.lower().strip()
    for key, val in CLINVAR_SCORES:
        if key in sig_lower:
            return val
    return 0.0


def _phenotype_score(
    gene: Optional[str],
    hpo_matched_terms: list,
    hpo_gene_map: dict,  # {gene_symbol: [hpo_term_ids]}
    query_hpo_terms: list,
) -> float:
    """Score based on HPO phenotype overlap with the gene."""
    if not gene or not query_hpo_terms:
        return 0.0
    gene_hpos = hpo_gene_map.get(gene, [])
    if not gene_hpos:
        return 0.0
    overlap = len(set(query_hpo_terms) & set(gene_hpos))
    if overlap == 0:
        return 0.0
    return min(1.0, overlap / max(len(query_hpo_terms), 1) * 1.5)


def _inheritance_score(
    zygosity: Optional[str],
    inheritance_mode: Optional[str] = None
) -> float:
    """Score based on zygosity-inheritance compatibility."""
    if not zygosity:
        return 0.3
    zyg = zygosity.upper()
    mode = (inheritance_mode or "").upper()

    if "AD" in mode:  # Autosomal dominant
        return 0.8 if zyg == "HET" else 0.2
    if "AR" in mode:  # Autosomal recessive
        return 0.9 if zyg == "HOM" else 0.4
    if "XL" in mode:  # X-linked
        return 0.8 if zyg in ("HOM", "HEMI") else 0.4

    # No inheritance mode — score based on zygosity alone
    if zyg == "HOM":
        return 0.7
    if zyg == "HET":
        return 0.5
    return 0.3


def _panel_score(panelapp_panels: list) -> float:
    """Score based on panel membership."""
    if not panelapp_panels:
        return 0.0
    return min(1.0, len(panelapp_panels) * 0.3)


def score_variant(
    variant: dict,
    query_hpo_terms: list = None,
    hpo_gene_map: dict = None,
    inheritance_mode: Optional[str] = None,
    compound_het_genes: set = None,
) -> tuple[float, RankDetails]:
    """
    Compute composite score for a variant.
    Returns (total_score, RankDetails).
    """
    query_hpo_terms = query_hpo_terms or []
    hpo_gene_map = hpo_gene_map or {}
    compound_het_genes = compound_het_genes or set()

    rarity = _rarity_score(variant.get("gnomad_af"))
    impact = _impact_score(variant.get("impact"), variant.get("consequence"))
    clinvar = _clinvar_score(variant.get("clinvar_significance"))
    phenotype = _phenotype_score(
        variant.get("gene"),
        variant.get("hpo_matched_terms", []),
        hpo_gene_map,
        query_hpo_terms,
    )
    inheritance = _inheritance_score(variant.get("zygosity"), inheritance_mode)
    panel = _panel_score(variant.get("panelapp_panels", []))

    # ACMG classification
    acmg = classify_acmg(
        consequence=variant.get("consequence"),
        impact=variant.get("impact"),
        gnomad_af=variant.get("gnomad_af"),
        clinvar_significance=variant.get("clinvar_significance"),
    )

    # ACMG score bonus: Pathogenic/Likely Pathogenic boost the rank score
    acmg_bonus = 0.0
    if acmg["acmg_class"] == "Pathogenic":
        acmg_bonus = 0.20
    elif acmg["acmg_class"] == "Likely Pathogenic":
        acmg_bonus = 0.12
    elif acmg["acmg_class"] == "VUS":
        acmg_bonus = 0.04

    # AlphaMissense bonus (DeepMind AI pathogenicity for missense variants)
    am_class = variant.get("alphamissense_class")
    alphamissense_bonus = 0.10 if am_class == "likely_pathogenic" else 0.03 if am_class == "ambiguous" else 0.0

    # Compound het flag — boosts score if gene has ≥2 HET candidates
    is_compound_het = variant.get("gene") in compound_het_genes
    compound_het_bonus = 0.08 if is_compound_het else 0.0

    total = min(1.0, (
        WEIGHTS["rarity"] * rarity
        + WEIGHTS["impact"] * impact
        + WEIGHTS["clinvar"] * clinvar
        + WEIGHTS["phenotype"] * phenotype
        + WEIGHTS["inheritance"] * inheritance
        + WEIGHTS["panel"] * panel
        + acmg_bonus
        + compound_het_bonus
        + alphamissense_bonus
    ))

    details = RankDetails(
        rarity_score=round(rarity, 4),
        impact_score=round(impact, 4),
        clinvar_score=round(clinvar, 4),
        phenotype_score=round(phenotype, 4),
        inheritance_score=round(inheritance, 4),
        panel_score=round(panel, 4),
        acmg_score=acmg["acmg_score"],
        acmg_class=acmg["acmg_class"],
        acmg_rules=acmg["acmg_rules"],
        compound_het=is_compound_het,
        total_score=round(total, 4),
        reasoning={
            "rarity": {
                "score": round(rarity, 4),
                "weight": WEIGHTS["rarity"],
                "gnomad_af": variant.get("gnomad_af"),
                "note": _rarity_note(variant.get("gnomad_af")),
            },
            "impact": {
                "score": round(impact, 4),
                "weight": WEIGHTS["impact"],
                "impact_class": variant.get("impact"),
                "consequence": variant.get("consequence"),
            },
            "clinvar": {
                "score": round(clinvar, 4),
                "weight": WEIGHTS["clinvar"],
                "significance": variant.get("clinvar_significance"),
                "review_status": variant.get("clinvar_review_status"),
            },
            "phenotype": {
                "score": round(phenotype, 4),
                "weight": WEIGHTS["phenotype"],
                "hpo_query": query_hpo_terms,
                "matched_terms": variant.get("hpo_matched_terms", []),
            },
            "inheritance": {
                "score": round(inheritance, 4),
                "weight": WEIGHTS["inheritance"],
                "zygosity": variant.get("zygosity"),
                "inheritance_mode": inheritance_mode,
            },
            "panel": {
                "score": round(panel, 4),
                "weight": WEIGHTS["panel"],
                "panels": variant.get("panelapp_panels", []),
            },
            "acmg": {
                "score": acmg["acmg_score"],
                "class": acmg["acmg_class"],
                "rules": acmg["acmg_rules"],
                "evidence": acmg.get("acmg_evidence", {}),
                "bonus_applied": round(acmg_bonus, 4),
            },
            "compound_het": {
                "detected": is_compound_het,
                "bonus_applied": round(compound_het_bonus, 4),
            },
            "alphamissense": {
                "score": variant.get("alphamissense_score"),
                "class": am_class,
                "bonus_applied": round(alphamissense_bonus, 4),
            },
        }
    )
    return total, details


def _rarity_note(af: Optional[float]) -> str:
    if af is None:
        return "Frequency unknown (not in gnomAD); moderate score assigned"
    if af == 0:
        return "Absent from gnomAD — very rare"
    if af < 0.0001:
        return f"Ultra-rare (AF={af:.2e})"
    if af < 0.001:
        return f"Rare (AF={af:.4f})"
    if af < 0.01:
        return f"Low frequency (AF={af:.4f})"
    return f"Common variant (AF={af:.4f}) — likely filtered"


def rank_variants(
    variants: list[dict],
    query_hpo_terms: list = None,
    hpo_gene_map: dict = None,
    inheritance_mode: Optional[str] = None,
    af_threshold: float = 0.05,
    consequence_classes: list = None,
    min_score: float = 0.25,
    max_candidates: int = 500,
    clinical_mode: bool = False,
) -> list[dict]:
    """
    Filter and rank a list of annotated variant dicts.
    Returns sorted list with rank_score and rank_details added.

    Filtering logic (in order):
    1. Skip common variants (gnomad_af > af_threshold).
    2. If consequence_classes is explicitly provided, also filter by impact
       (allowing ClinVar-pathogenic variants to bypass the impact filter).
    3. Score all remaining variants; drop any below min_score.
    4. Return at most max_candidates, sorted by score descending.
    """
    query_hpo_terms = query_hpo_terms or []
    # consequence_classes defaults to None — scoring handles prioritisation.

    filtered = []
    for v in variants:
        af = v.get("gnomad_af")
        # 0. Clinical mode — restrict to ACMG actionable genes only
        if clinical_mode:
            gene = (v.get("gene") or "").upper()
            if gene not in ACMG_ACTIONABLE_GENES:
                continue
        # 1. Allele frequency filter — skip common variants
        if af is not None and af > af_threshold:
            continue
        # 2. Optional hard impact class filter
        if consequence_classes:
            impact = v.get("impact") or "MODIFIER"
            if impact not in consequence_classes:
                # Always pass ClinVar pathogenic regardless of impact class
                sig = (v.get("clinvar_significance") or "").lower()
                if "pathogenic" not in sig:
                    continue
        filtered.append(v)

    # Detect compound heterozygosity across all filtered variants
    compound_het_genes: set = set(detect_compound_hets(filtered).keys())
    if compound_het_genes:
        import logging
        logging.getLogger(__name__).info(
            f"Compound het candidates detected in {len(compound_het_genes)} genes: "
            + ", ".join(sorted(compound_het_genes)[:10])
            + ("..." if len(compound_het_genes) > 10 else "")
        )

    # Score each variant
    scored = []
    for v in filtered:
        score, details = score_variant(
            v, query_hpo_terms, hpo_gene_map, inheritance_mode, compound_het_genes
        )
        if score < min_score:
            continue
        v["rank_score"] = score
        v["rank_details"] = details.__dict__
        scored.append(v)

    # Sort descending by score
    scored.sort(key=lambda x: x["rank_score"], reverse=True)

    # Cap to max_candidates
    scored = scored[:max_candidates]

    # Assign rank positions
    for i, v in enumerate(scored):
        v["rank_position"] = i + 1

    return scored
