"""
Check Agent — OMIM Validation Loop (DeepRare pattern)
======================================================
After ranking, validates top candidates against OMIM to confirm:
  1. Gene is a known OMIM disease gene
  2. Inheritance mode matches observed zygosity
  3. ACMG classification is consistent with known disease mechanism

For each top variant:
  - Query OMIM via NCBI E-utilities (no API key required for basic access)
  - Extract: disease name, inheritance mode, MIM number, allelic variant info
  - Set validation_status: confirmed / unconfirmed / conflict / no_omim_entry

Result is stored in variant's rank_details.omim_validation dict.
"""
import httpx
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OMIM_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
OMIM_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


async def lookup_omim_gene(
    gene_symbol: str,
    client: httpx.AsyncClient,
) -> dict:
    """
    Query OMIM via NCBI E-utilities for a gene symbol.
    Returns dict with disease name, inheritance mode, MIM numbers.
    """
    if not gene_symbol:
        return {}
    try:
        # Step 1: Search OMIM for the gene
        r = await client.get(
            OMIM_ESEARCH_URL,
            params={
                "db": "omim",
                "term": f"{gene_symbol}[GENE] AND genemap2[Filter]",
                "retmax": 3,
                "retmode": "json",
            },
            timeout=12.0,
        )
        if r.status_code != 200:
            return {}

        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return {"gene": gene_symbol, "omim_found": False}

        # Step 2: Fetch summary for first result
        r2 = await client.get(
            OMIM_ESUMMARY_URL,
            params={
                "db": "omim",
                "id": ",".join(ids[:2]),
                "retmode": "json",
            },
            timeout=12.0,
        )
        if r2.status_code != 200:
            return {"gene": gene_symbol, "omim_found": True, "omim_ids": ids}

        result_data = r2.json().get("result", {})
        entries = []
        for uid in ids[:2]:
            record = result_data.get(str(uid), {})
            if not record:
                continue
            title = record.get("title", "")
            # Extract inheritance from title keywords
            inheritance = _infer_inheritance(title, record)
            entries.append({
                "mim_number": uid,
                "title": title,
                "inheritance": inheritance,
                "url": f"https://www.omim.org/entry/{uid}",
            })

        return {
            "gene": gene_symbol,
            "omim_found": True,
            "omim_ids": ids[:2],
            "entries": entries,
            "primary_disease": entries[0]["title"] if entries else "",
            "primary_inheritance": entries[0]["inheritance"] if entries else "",
        }

    except Exception as e:
        logger.warning(f"OMIM lookup failed for {gene_symbol}: {e}")
        return {}


def _infer_inheritance(title: str, record: dict) -> str:
    """Infer inheritance mode from OMIM title or record text."""
    text = (title + " " + str(record)).lower()
    if "autosomal dominant" in text or ", ad" in text:
        return "AD"
    if "autosomal recessive" in text or ", ar" in text:
        return "AR"
    if "x-linked dominant" in text:
        return "XLD"
    if "x-linked recessive" in text or "x-linked" in text:
        return "XLR"
    if "mitochondrial" in text:
        return "MT"
    if "y-linked" in text:
        return "YL"
    return "Unknown"


def _check_zygosity_consistency(
    zygosity: Optional[str],
    inheritance: str,
) -> tuple[bool, str]:
    """
    Check if observed zygosity is consistent with OMIM inheritance mode.
    Returns (is_consistent, explanation).
    """
    if not zygosity or inheritance == "Unknown":
        return True, "Cannot verify — zygosity or inheritance unknown"

    zyg = (zygosity or "").upper()

    if inheritance == "AD":
        if zyg == "HET":
            return True, "HET zygosity consistent with AD inheritance"
        elif zyg == "HOM":
            return True, "HOM also possible in AD (severe phenotype)"
        else:
            return False, f"Zygosity {zyg} unusual for AD"

    elif inheritance == "AR":
        if zyg == "HOM":
            return True, "HOM zygosity consistent with AR inheritance"
        elif zyg == "HET":
            return False, "Single HET variant alone insufficient for AR — possible compound het"
        else:
            return False, f"Zygosity {zyg} unusual for AR"

    elif inheritance in ("XLR", "XLD"):
        if zyg in ("HOM", "HEMI", "HET"):
            return True, f"Zygosity {zyg} plausible for X-linked"
        return False, f"Zygosity {zyg} unexpected for X-linked"

    return True, "Zygosity check not applicable"


def _get_validation_status(
    acmg_class: Optional[str],
    omim_found: bool,
    zygosity_ok: bool,
    is_compound_het: bool,
    inheritance: str,
) -> str:
    """
    Determine overall validation status.
    confirmed / likely_confirmed / unconfirmed / conflict / no_omim_entry
    """
    if not omim_found:
        return "no_omim_entry"

    pathogenic = acmg_class in ("Pathogenic", "Likely Pathogenic")

    if pathogenic and zygosity_ok:
        return "confirmed"
    elif pathogenic and not zygosity_ok:
        if is_compound_het and inheritance == "AR":
            return "confirmed"  # compound het resolves the AR mismatch
        return "conflict"
    elif not pathogenic and zygosity_ok:
        return "unconfirmed"
    else:
        return "unconfirmed"


async def validate_top_candidates(
    ranked_variants: list[dict],
    top_n: int = 30,
) -> list[dict]:
    """
    Run OMIM validation loop on top-N ranked variants.
    Adds 'omim_validation' key to each variant's rank_details.
    Returns the same list with validation data added in-place.
    """
    if not ranked_variants:
        return ranked_variants

    top = ranked_variants[:top_n]

    # Collect unique genes to avoid duplicate OMIM lookups
    unique_genes: set[str] = set()
    for v in top:
        g = v.get("gene")
        if g:
            unique_genes.add(g)

    gene_omim_cache: dict[str, dict] = {}

    async with httpx.AsyncClient() as client:
        for gene in unique_genes:
            result = await lookup_omim_gene(gene, client)
            gene_omim_cache[gene] = result
            await asyncio.sleep(0.15)  # NCBI rate limit: ~7 req/s without key

    # Apply validation to each top variant
    for v in top:
        gene = v.get("gene", "")
        omim_data = gene_omim_cache.get(gene, {})
        omim_found = omim_data.get("omim_found", False)
        inheritance = omim_data.get("primary_inheritance", "Unknown")

        rd = v.get("rank_details", {})
        acmg_class = rd.get("acmg_class") if isinstance(rd, dict) else None
        is_compound_het = rd.get("compound_het", False) if isinstance(rd, dict) else False
        zygosity = v.get("zygosity")

        zygosity_ok, zyg_note = _check_zygosity_consistency(zygosity, inheritance)

        status = _get_validation_status(
            acmg_class, omim_found, zygosity_ok, is_compound_het, inheritance
        )

        validation = {
            "status": status,                          # confirmed / conflict / unconfirmed / no_omim_entry
            "omim_found": omim_found,
            "omim_disease": omim_data.get("primary_disease", ""),
            "omim_inheritance": inheritance,
            "omim_ids": omim_data.get("omim_ids", []),
            "omim_url": f"https://www.omim.org/search?search={gene}" if gene else "",
            "zygosity_consistent": zygosity_ok,
            "zygosity_note": zyg_note,
            "acmg_class": acmg_class,
        }

        # Embed in rank_details for storage
        if isinstance(rd, dict):
            rd["omim_validation"] = validation
        v["rank_details"] = rd
        v["omim_disease"] = omim_data.get("primary_disease", "")
        v["omim_inheritance"] = inheritance
        v["validation_status"] = status

    logger.info(
        f"Check Agent complete: validated {len(top)} variants across "
        f"{len(unique_genes)} genes. "
        f"confirmed={sum(1 for v in top if v.get('validation_status')=='confirmed')}, "
        f"conflict={sum(1 for v in top if v.get('validation_status')=='conflict')}"
    )

    return ranked_variants
