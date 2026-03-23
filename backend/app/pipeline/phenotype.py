"""
Phenotype Tools
===============
1. Monarch Initiative SemSim — send HPO terms → ranked rare disease candidates
   (replaces PubCaseFinder which is unreliable)
2. HPO term lookup — resolve HPO IDs to names

Monarch SemSim API:
  POST https://api.monarchinitiative.org/v3/api/semsim/search
  Body: { "termset": [...HPO IDs], "group": "Human Diseases", "limit": 10, ... }
  Returns semantically matched diseases ranked by phenotypic similarity
"""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MONARCH_SEMSIM_URL = "https://api.monarchinitiative.org/v3/api/semsim/search"
HPO_API_URL        = "https://ontology.jax.org/api/hp/terms"   # JAX HPO REST


async def query_disease_candidates(hpo_terms: list[str], limit: int = 10) -> list[dict]:
    """
    Query Monarch Initiative SemSim to find diseases matching the HPO profile.
    Returns top-N ranked disease candidates.

    Each result:
      - disease_id: MONDO/OMIM/Orphanet ID
      - disease_name: human-readable name
      - similarity_score: float
      - omim_ids: list of OMIM cross-references
    """
    if not hpo_terms:
        return []

    normalised = [
        t if t.upper().startswith("HP:") else f"HP:{t}"
        for t in hpo_terms
    ]

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.post(
                MONARCH_SEMSIM_URL,
                json={
                    "termset":       normalised,
                    "limit":         limit,
                    "is_weighted":   False,
                    "score_metric":  "ancestor_information_content",
                    "group":         "Human Diseases",
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            if r.status_code != 200:
                logger.warning(f"Monarch SemSim HTTP {r.status_code}")
                return []

            entries = r.json()
            if not isinstance(entries, list):
                entries = entries.get("results", [])

            results = []
            for entry in entries[:limit]:
                subj = entry.get("subject", {})
                xrefs = subj.get("xref", [])
                omim_ids = [x for x in xrefs if x.startswith("OMIM:")]
                results.append({
                    "disease_id":       subj.get("id", ""),
                    "disease_name":     subj.get("name") or subj.get("full_name", ""),
                    "similarity_score": round(float(entry.get("score", 0)), 4),
                    "omim_ids":         omim_ids,
                    "source":           "monarch",
                })
            return results

    except Exception as e:
        logger.warning(f"Monarch SemSim query failed: {e}")
        return []


async def lookup_hpo_term(hpo_id: str) -> Optional[dict]:
    """Resolve a single HPO ID to its name."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{HPO_API_URL}/{hpo_id}")
            if r.status_code == 200:
                d = r.json()
                return {"id": hpo_id, "name": d.get("name", ""), "definition": d.get("definition", "")}
    except Exception:
        pass
    return None


async def enrich_hpo_context(hpo_terms: list[str]) -> dict:
    """
    Given HPO term IDs, query Monarch SemSim for matching diseases.
    Returns enriched context used in ranking and Gemini Chat.
    """
    disease_candidates = await query_disease_candidates(hpo_terms)
    return {
        "disease_candidates": disease_candidates,
        "hpo_count":          len(hpo_terms),
        "query_terms":        hpo_terms,
    }
