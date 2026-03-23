"""
Literature Agent — PubMed E-utilities search
Fetches relevant abstracts for gene + disease queries.
"""
import httpx
from typing import Optional
from app.config import settings


NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


async def search_pubmed(
    gene: str,
    condition: Optional[str] = None,
    max_results: int = 3,
) -> dict:
    """
    Search PubMed for literature about a gene ± condition.
    Returns structured results with titles and abstracts.
    """
    query_parts = [f"{gene}[gene]"]
    if condition:
        query_parts.append(f'"{condition}"')
    query = " AND ".join(query_parts)

    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if settings.ncbi_api_key:
        esearch_params["api_key"] = settings.ncbi_api_key

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for IDs
            r = await client.get(NCBI_ESEARCH, params=esearch_params)
            r.raise_for_status()
            search_data = r.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                return {
                    "gene": gene,
                    "condition": condition,
                    "results": [],
                    "message": "No PubMed results found"
                }

            # Fetch abstracts
            efetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "json",
            }
            if settings.ncbi_api_key:
                efetch_params["api_key"] = settings.ncbi_api_key

            r2 = await client.get(NCBI_ESUMMARY, params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            })
            r2.raise_for_status()
            summary_data = r2.json()

            results = []
            uids = summary_data.get("result", {}).get("uids", [])
            for uid in uids:
                article = summary_data["result"].get(uid, {})
                results.append({
                    "pmid": uid,
                    "title": article.get("title", ""),
                    "authors": [a.get("name", "") for a in article.get("authors", [])[:3]],
                    "journal": article.get("source", ""),
                    "pubdate": article.get("pubdate", ""),
                    "abstract": article.get("title", ""),  # summary doesn't include full abstract
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                })

            return {
                "gene": gene,
                "condition": condition,
                "query": query,
                "total_found": search_data.get("esearchresult", {}).get("count", "0"),
                "results": results,
            }

    except Exception as e:
        return {
            "gene": gene,
            "condition": condition,
            "error": str(e),
            "results": [],
        }
