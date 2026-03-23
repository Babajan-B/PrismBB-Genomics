"""
Annotation Module — Two-Phase Pipeline
===========================================
Phase 1  MyVariant.info bulk POST (1 000 variants/request)
         → gnomAD AF + ClinVar for ALL variants  (~5 min for 100k)
Phase 2  Ensembl VEP REST (200 variants/request)
         → gene / transcript / HGVS / impact
         → only for variants that survive the AF pre-filter (~20% of total)
Phase 3  PanelApp — once per UNIQUE GENE (not per variant)

No local genome or local VEP installation required.
"""
import httpx
import asyncio
import gzip
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from app.config import settings

logger = logging.getLogger(__name__)

# ── API endpoints ──────────────────────────────────────────────────────────
ENSEMBL_VEP_REST_38 = "https://rest.ensembl.org/vep/human/region"
ENSEMBL_VEP_REST_37 = "https://grch37.rest.ensembl.org/vep/human/region"
MYVARIANT_QUERY_URL = "https://myvariant.info/v1/query"
PANELAPP_URL        = "https://panelapp.genomicsengland.co.uk/api/v1/genes"

IMPACT_ORDER = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}


# ── Data class ─────────────────────────────────────────────────────────────
@dataclass
class AnnotationResult:
    variant_key: str
    gene: Optional[str] = None
    transcript: Optional[str] = None
    hgvs_c: Optional[str] = None
    hgvs_p: Optional[str] = None
    consequence: Optional[str] = None
    impact: Optional[str] = None
    clinvar_id: Optional[str] = None
    clinvar_significance: Optional[str] = None
    clinvar_review_status: Optional[str] = None
    gnomad_af: Optional[float] = None
    gnomad_af_popmax: Optional[float] = None
    alphamissense_score: Optional[float] = None
    alphamissense_class: Optional[str] = None
    panelapp_panels: list = field(default_factory=list)
    raw_vep: dict = field(default_factory=dict)
    error: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────
def _build_vep_url(genome_build: str) -> str:
    return ENSEMBL_VEP_REST_37 if genome_build == "GRCh37" else ENSEMBL_VEP_REST_38


def _variant_to_region(chrom: str, pos: int, ref: str, alt: str) -> str:
    """Convert VCF fields to VEP region notation (no chr prefix).
    Format: chromosome:start-end:strand/allele_string
    """
    c = chrom.replace("chr", "")
    if len(ref) == 1 and len(alt) == 1:
        # SNP
        return f"{c}:{pos}-{pos}:1/{alt}"
    elif len(ref) > len(alt):
        # Deletion
        end = pos + len(ref) - 1
        return f"{c}:{pos}-{end}:1/{alt}"
    else:
        # Insertion
        return f"{c}:{pos}-{pos}:1/{alt}"


def _variant_to_hgvs(chrom: str, pos: int, ref: str, alt: str) -> str:
    """Build a HGVS-style ID for MyVariant.info queries.
    Works reliably for SNPs; approximate for indels (MyVariant will return
    notfound=True for those, which is handled gracefully).
    """
    c = chrom.replace("chr", "")
    return f"chr{c}:g.{pos}{ref}>{alt}"


def _parse_myvariant(mv_data: dict) -> dict:
    """Extract gnomAD AF and ClinVar fields from a MyVariant hit."""
    out: dict = {}
    if not mv_data:
        return out

    # gnomAD — prefer exome, fall back to genome
    gnomad = mv_data.get("gnomad_exome") or mv_data.get("gnomad_genome") or {}
    if gnomad:
        af_block = gnomad.get("af", {})
        if isinstance(af_block, dict):
            out["gnomad_af"] = af_block.get("af")
        else:
            out["gnomad_af"] = af_block  # sometimes a float directly
        popmax = gnomad.get("af_popmax")
        if popmax is not None:
            out["gnomad_af_popmax"] = float(popmax)

    # ClinVar
    clinvar = mv_data.get("clinvar", {})
    if clinvar:
        out["clinvar_id"] = str(clinvar.get("variant_id", ""))
        rcv = clinvar.get("rcv", {})
        if isinstance(rcv, list) and rcv:
            rcv = rcv[0]
        if isinstance(rcv, dict):
            out["clinvar_significance"] = rcv.get("clinical_significance")
            out["clinvar_review_status"] = rcv.get("review_status")

    # AlphaMissense (DeepMind AI pathogenicity score for missense variants)
    # Available via MyVariant.info for missense SNPs
    am = mv_data.get("alphamissense", {})
    if am:
        score = am.get("am_pathogenicity")
        if score is not None:
            out["alphamissense_score"] = float(score)
            # Threshold from DeepRare / variant-agents: >= 0.564 = likely pathogenic
            out["alphamissense_class"] = (
                "likely_pathogenic" if float(score) >= 0.564
                else "likely_benign" if float(score) < 0.34
                else "ambiguous"
            )

    return out


def _parse_vep_result(vep_data: dict) -> dict:
    """Parse VEP REST transcript_consequences into a flat dict."""
    out: dict = {}
    if not vep_data:
        return out
    tc = vep_data.get("transcript_consequences", [])
    best = next((t for t in tc if t.get("canonical") == 1), None)
    if best is None and tc:
        best = tc[0]
    if best:
        out["gene"]       = best.get("gene_symbol")
        out["transcript"] = best.get("transcript_id")
        out["hgvs_c"]     = best.get("hgvs_c")
        out["hgvs_p"]     = best.get("hgvs_p")
        csq = best.get("consequence_terms", [])
        out["consequence"] = ",".join(csq) if csq else None
        out["impact"]      = best.get("impact")
    out["variant_class"] = vep_data.get("variant_class")
    return out


# ── Phase 1: MyVariant bulk ────────────────────────────────────────────────
async def _myvariant_bulk_batch(
    batch: list[dict],
    assembly: str,
    client: httpx.AsyncClient,
) -> dict[str, dict]:
    """
    Query MyVariant.info for up to 1 000 variants in one POST.
    Returns {variant_key → parsed annotation dict}.
    """
    id_list: list[str] = []
    hgvs_to_key: dict[str, str] = {}

    for v in batch:
        key  = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        hgvs = _variant_to_hgvs(v["chrom"], v["pos"], v["ref"], v["alt"])
        id_list.append(hgvs)
        hgvs_to_key[hgvs] = key

    try:
        r = await client.post(
            MYVARIANT_QUERY_URL,
            json={
                "q":      id_list,
                "fields": "gnomad_exome,gnomad_genome,clinvar,alphamissense",
            },
            headers={"Content-Type": "application/json"},
            timeout=90.0,
        )
        if r.status_code != 200:
            logger.warning(f"MyVariant batch HTTP {r.status_code}")
            return {}

        out: dict[str, dict] = {}
        for item in r.json():
            if item.get("notfound"):
                continue
            query_id = item.get("query", "")
            var_key  = hgvs_to_key.get(query_id)
            if var_key:
                out[var_key] = _parse_myvariant(item)
        return out

    except Exception as e:
        logger.warning(f"MyVariant bulk batch failed: {e}")
        return {}


async def annotate_myvariant_all(
    variants: list[dict],
    genome_build: str = "GRCh38",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict[str, dict]:
    """
    Bulk-query MyVariant.info for ALL variants.
    Returns {variant_key → {gnomad_af, gnomad_af_popmax, clinvar_*, ...}}.
    Processes in batches of 1 000 with a shared HTTP client.
    """
    assembly = "hg38" if genome_build == "GRCh38" else "hg19"
    combined: dict[str, dict] = {}
    BATCH = 1000

    async with httpx.AsyncClient() as client:
        for i in range(0, len(variants), BATCH):
            batch = variants[i : i + BATCH]
            chunk = await _myvariant_bulk_batch(batch, assembly, client)
            combined.update(chunk)
            if progress_cb:
                progress_cb(min(i + BATCH, len(variants)), len(variants))
            # Polite rate-limiting (MyVariant allows ~10 req/s without key)
            await asyncio.sleep(0.15)

    return combined


# ── Phase 2: VEP batch ─────────────────────────────────────────────────────
async def _vep_batch(
    variants: list[dict],
    genome_build: str,
    client: httpx.AsyncClient,
) -> dict[str, dict]:
    """
    Send up to 200 variants to VEP REST API.
    Returns {variant_key → parsed VEP dict}.
    """
    url     = _build_vep_url(genome_build)
    regions = [_variant_to_region(v["chrom"], v["pos"], v["ref"], v["alt"]) for v in variants]

    # Build region → variant_key map before the call
    region_to_key: dict[str, str] = {}
    for v, region in zip(variants, regions):
        key = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        region_to_key[region] = key

    try:
        r = await client.post(
            url,
            json={
                "variants":  regions,
                "hgvs":      True,
                "canonical": True,
                "pick":      True,
                "variant_class": True,
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=180.0,
        )
        if r.status_code != 200:
            logger.warning(f"VEP batch HTTP {r.status_code}")
            return {}

        # VEP returns results with an "input" field = the region string we sent
        out: dict[str, dict] = {}
        for vr in r.json():
            input_str = vr.get("input", "").strip()
            # Direct match
            if input_str in region_to_key:
                key = region_to_key[input_str]
                out[key] = _parse_vep_result(vr)
                continue
            # Positional fallback (strips allele suffix)
            pos_prefix = input_str.split("/")[0] if "/" in input_str else input_str
            for region, key in region_to_key.items():
                if region.startswith(pos_prefix) or pos_prefix == region.split("/")[0]:
                    out[key] = _parse_vep_result(vr)
                    break
        return out

    except Exception as e:
        logger.warning(f"VEP batch failed: {e}")
        return {}


async def annotate_vep_candidates(
    variants: list[dict],
    genome_build: str = "GRCh38",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict[str, dict]:
    """
    Run VEP annotation on a list of variants (already pre-filtered to rare ones).
    Returns {variant_key → parsed VEP dict}.
    """
    combined: dict[str, dict] = {}
    VEP_BATCH = 200   # VEP REST supports up to 300; 200 is stable

    async with httpx.AsyncClient() as client:
        for i in range(0, len(variants), VEP_BATCH):
            batch = variants[i : i + VEP_BATCH]
            chunk = await _vep_batch(batch, genome_build, client)
            combined.update(chunk)
            if progress_cb:
                progress_cb(min(i + VEP_BATCH, len(variants)), len(variants))
            await asyncio.sleep(0.3)   # avoid overwhelming Ensembl

    return combined


# ── Phase 3: PanelApp (per unique gene) ───────────────────────────────────
async def get_panelapp_info(
    gene_symbol: str,
    client: httpx.AsyncClient,
) -> list[str]:
    """Return the PanelApp disease panels that contain this gene (up to 5).
    Returns empty list on 429 (rate-limit) or any error — non-blocking.
    """
    if not gene_symbol:
        return []
    try:
        r = await client.get(PANELAPP_URL, params={"entity_name": gene_symbol})
        if r.status_code == 429:
            return []   # rate-limited — skip silently
        if r.status_code == 200:
            panels = [
                res.get("panel", {}).get("name")
                for res in r.json().get("results", [])
            ]
            return [p for p in panels if p][:5]
    except Exception as e:
        logger.warning(f"PanelApp lookup failed for {gene_symbol}: {e}")
    return []


async def annotate_panelapp_genes(
    gene_set: set[str],
    max_genes: int = 300,
) -> dict[str, list[str]]:
    """
    Query PanelApp once per unique gene.
    Capped at max_genes to avoid rate-limiting.
    Returns {gene → [panel, ...]}.
    """
    gene_panels: dict[str, list[str]] = {}
    genes = list(gene_set)[:max_genes]
    async with httpx.AsyncClient(timeout=15.0) as client:
        for gene in genes:
            gene_panels[gene] = await get_panelapp_info(gene, client)
            await asyncio.sleep(0.3)   # polite rate-limiting (3 req/s max)
    return gene_panels


# ── Main entry point ───────────────────────────────────────────────────────
async def annotate_variants_full(
    variants: list[dict],
    genome_build: str = "GRCh38",
    af_threshold: float = 0.05,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> list[AnnotationResult]:
    """
    Full two-phase annotation for ALL variants in a VCF.

    Phase 1 — MyVariant bulk (all variants)
        Retrieves gnomAD AF + ClinVar in batches of 1 000.
        Typical time: ~5 min for 100 k variants.

    Phase 2 — VEP REST (rare/unknown variants only)
        Variants with gnomad_af > af_threshold are skipped.
        Variants with any ClinVar entry are always included.
        Typical input after filter: 15–25% of total.
        VEP batches of 200; typical time: 20–40 min.

    Phase 3 — PanelApp (one call per unique gene)
        Fills panel membership for all annotated genes.

    Returns a list of AnnotationResult, one per input variant,
    in the same order as the input list.
    """
    total = len(variants)
    logger.info(f"Annotation starting: {total} variants, build={genome_build}")

    # ── index by key for fast lookup ───────────────────────────────────────
    results_map: dict[str, AnnotationResult] = {}
    for v in variants:
        key = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        results_map[key] = AnnotationResult(variant_key=key)

    # ── Phase 1: MyVariant bulk ────────────────────────────────────────────
    logger.info("Phase 1: MyVariant bulk query")

    def _mv_progress(done: int, total_: int):
        if progress_cb:
            progress_cb("myvariant", done, total_)

    mv_results = await annotate_myvariant_all(variants, genome_build, _mv_progress)

    mv_found = 0
    for key, ar in results_map.items():
        mv = mv_results.get(key, {})
        ar.gnomad_af             = mv.get("gnomad_af")
        ar.gnomad_af_popmax      = mv.get("gnomad_af_popmax")
        ar.clinvar_id            = mv.get("clinvar_id")
        ar.clinvar_significance  = mv.get("clinvar_significance")
        ar.clinvar_review_status = mv.get("clinvar_review_status")
        ar.alphamissense_score   = mv.get("alphamissense_score")
        ar.alphamissense_class   = mv.get("alphamissense_class")
        if mv:
            mv_found += 1

    logger.info(f"Phase 1 complete: {mv_found}/{total} variants matched in MyVariant")

    # ── Phase 1b: Apply SnpEff ANN annotations from VCF (if already present) ─
    # Many VCFs are pre-annotated with SnpEff — use that data directly to avoid
    # a slow VEP REST call. Only variants missing gene/impact need VEP.
    ann_found = 0
    for v in variants:
        key = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        ar  = results_map[key]
        if v.get("gene"):
            ar.gene        = v.get("gene")
            ar.transcript  = v.get("transcript")
            ar.hgvs_c      = v.get("hgvs_c")
            ar.hgvs_p      = v.get("hgvs_p")
            ar.consequence = v.get("consequence")
            ar.impact      = v.get("impact")
            ann_found += 1

    logger.info(
        f"Phase 1b: {ann_found}/{total} variants have SnpEff ANN annotations from VCF"
    )

    # ── Phase 2: VEP — only for rare variants WITHOUT existing annotation ──
    vep_keys = set()
    for v in variants:
        key = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        ar  = results_map[key]
        af  = ar.gnomad_af
        # Skip VEP if we already have gene/impact from SnpEff ANN
        if ar.gene and ar.impact:
            continue
        # Include if: unknown AF, rare AF, or has any ClinVar entry
        if af is None or af <= af_threshold or ar.clinvar_significance:
            vep_keys.add(key)

    vep_variants = [v for v in variants
                    if f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}" in vep_keys]

    if vep_variants:
        logger.info(
            f"Phase 2: VEP annotation for {len(vep_variants)} variants "
            f"({len(variants) - len(vep_variants)} skipped: common AF or already ANN-annotated)"
        )

        def _vep_progress(done: int, total_: int):
            if progress_cb:
                progress_cb("vep", done, total_)

        vep_results = await annotate_vep_candidates(vep_variants, genome_build, _vep_progress)

        vep_found = 0
        for key, parsed in vep_results.items():
            if key in results_map and parsed:
                ar = results_map[key]
                ar.gene        = parsed.get("gene")
                ar.transcript  = parsed.get("transcript")
                ar.hgvs_c      = parsed.get("hgvs_c")
                ar.hgvs_p      = parsed.get("hgvs_p")
                ar.consequence = parsed.get("consequence")
                ar.impact      = parsed.get("impact")
                ar.raw_vep     = parsed
                vep_found += 1

        logger.info(f"Phase 2 complete: {vep_found} variants VEP-annotated")
    else:
        logger.info("Phase 2: Skipped — all variants already annotated via SnpEff ANN field")

    # ── Phase 3: PanelApp — only for HIGH/MODERATE impact genes ──────────
    # Querying PanelApp for all genes (incl. thousands of MODIFIER intergenic)
    # causes rate-limiting. Only clinically relevant genes need panel context.
    relevant_impacts = {"HIGH", "MODERATE"}
    unique_genes = {
        ar.gene for ar in results_map.values()
        if ar.gene and ar.impact in relevant_impacts
    }
    logger.info(f"Phase 3: PanelApp for {len(unique_genes)} HIGH/MODERATE genes (capped at 300)")

    gene_panels = await annotate_panelapp_genes(unique_genes)

    for ar in results_map.values():
        if ar.gene:
            ar.panelapp_panels = gene_panels.get(ar.gene, [])

    # ── Return in original order ───────────────────────────────────────────
    ordered = []
    for v in variants:
        key = f"{v['chrom']}:{v['pos']}:{v['ref']}:{v['alt']}"
        ordered.append(results_map[key])

    logger.info(f"Annotation complete: {len(ordered)} results returned")
    return ordered


# ── ANN field parser (SnpEff) ──────────────────────────────────────────────
_IMPACT_RANK = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}


def _parse_ann_field(info_str: str) -> dict:
    """
    Parse the SnpEff ANN= field from a VCF INFO column.
    Selects the highest-impact annotation (by impact class, then effect specificity).
    Returns a dict with gene, transcript, hgvs_c, hgvs_p, consequence, impact.
    """
    ann_raw = None
    for token in info_str.split(";"):
        if token.startswith("ANN="):
            ann_raw = token[4:]
            break
    if not ann_raw:
        return {}

    best: dict = {}
    best_rank = -1

    for annotation in ann_raw.split(","):
        fields = annotation.split("|")
        if len(fields) < 4:
            continue
        consequence = fields[1].strip() if len(fields) > 1 else None
        impact      = fields[2].strip() if len(fields) > 2 else None
        gene        = fields[3].strip() if len(fields) > 3 else None
        transcript  = fields[6].strip() if len(fields) > 6 else None
        hgvs_c      = fields[9].strip()  if len(fields) > 9  else None
        hgvs_p      = fields[10].strip() if len(fields) > 10 else None

        rank = _IMPACT_RANK.get(impact or "MODIFIER", 1)
        # Prefer NM_ (coding) transcripts over NR_ (non-coding)
        is_coding = transcript and transcript.startswith("NM_")
        score = rank * 10 + (1 if is_coding else 0)

        if score > best_rank:
            best_rank = score
            best = {
                "gene":        gene or None,
                "transcript":  transcript or None,
                "hgvs_c":      hgvs_c or None,
                "hgvs_p":      hgvs_p or None,
                "consequence": consequence or None,
                "impact":      impact or None,
            }

    return best


# ── VCF parser ─────────────────────────────────────────────────────────────
def parse_vcf_variants(vcf_path: str) -> list[dict]:
    """
    Parse VCF and return all variant records as dicts.
    Extracts SnpEff ANN annotations (gene, impact, consequence, HGVS) when present
    so the pipeline can skip the VEP REST API for pre-annotated VCFs.
    """
    variants = []
    sample_ids: list[str] = []

    def open_vcf(path: str):
        if path.endswith(".gz") or path.endswith(".bgz"):
            return gzip.open(path, "rt")
        return open(path, "r")

    with open_vcf(vcf_path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                parts = line.split("\t")
                sample_ids = parts[9:] if len(parts) > 9 else ["SAMPLE"]
                continue

            parts = line.split("\t")
            if len(parts) < 5:
                continue

            chrom, pos, vid, ref, alt = (
                parts[0], int(parts[1]), parts[2], parts[3], parts[4]
            )
            filter_val   = parts[6] if len(parts) > 6 else "."
            info_str     = parts[7] if len(parts) > 7 else ""
            format_field = parts[8] if len(parts) > 8 else None
            zygosity     = None
            genotype     = None

            if format_field and len(parts) > 9:
                fmt_keys    = format_field.split(":")
                sample_vals = parts[9].split(":")
                fmt_dict    = dict(zip(fmt_keys, sample_vals))
                gt          = fmt_dict.get("GT", "./.")
                genotype    = gt
                if gt in ("1/1", "1|1"):
                    zygosity = "HOM"
                elif gt in ("0/1", "1/0", "0|1", "1|0"):
                    zygosity = "HET"
                elif gt == "1":
                    zygosity = "HEMI"

            # Parse SnpEff ANN field if present — avoids VEP REST call later
            ann = _parse_ann_field(info_str)

            variant = {
                "chrom":      chrom,
                "pos":        pos,
                "ref":        ref,
                "alt":        alt,
                "variant_id": vid,
                "filter":     filter_val,
                "sample_id":  sample_ids[0] if sample_ids else "SAMPLE",
                "zygosity":   zygosity,
                "genotype":   genotype,
            }
            if ann:
                variant.update(ann)   # gene, transcript, hgvs_c, hgvs_p, consequence, impact

            variants.append(variant)

    return variants
