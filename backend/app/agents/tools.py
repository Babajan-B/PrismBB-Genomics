"""
Multi-Agent Tool Definitions for Gemini Function Calling
All tools are grounded in the database — no hallucination.
"""
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool


# ─── Individual Function Declarations ─────────────────────────────────────────

list_jobs_fn = FunctionDeclaration(
    name="list_jobs",
    description="List all analysis jobs / runs in the system with their status.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of jobs to return (default 10)"
            }
        },
        "required": []
    }
)

get_job_status_fn = FunctionDeclaration(
    name="get_job_status",
    description="Get the current status and metadata for a specific analysis job.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The unique job ID (UUID)"
            }
        },
        "required": ["job_id"]
    }
)

get_job_variants_fn = FunctionDeclaration(
    name="get_job_variants",
    description="Retrieve the ranked list of candidate variants for an analysis job. Returns variants sorted by priority score.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The unique job ID (UUID)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of variants to return (default 20)"
            },
            "min_impact": {
                "type": "string",
                "description": "Filter by minimum impact class: HIGH, MODERATE, LOW, MODIFIER"
            }
        },
        "required": ["job_id"]
    }
)

get_variant_detail_fn = FunctionDeclaration(
    name="get_variant_detail",
    description="Get full evidence card for a specific variant including all annotation fields, ClinVar data, gnomAD frequency, and ranking score breakdown.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The unique job ID"
            },
            "variant_id": {
                "type": "string",
                "description": "The variant database ID"
            }
        },
        "required": ["job_id", "variant_id"]
    }
)

explain_ranking_fn = FunctionDeclaration(
    name="explain_ranking",
    description="Explain why a specific variant was given its priority rank. Returns detailed score breakdown across all evidence dimensions.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The job ID"
            },
            "variant_id": {
                "type": "string",
                "description": "The variant ID to explain"
            }
        },
        "required": ["job_id", "variant_id"]
    }
)

compare_variants_fn = FunctionDeclaration(
    name="compare_variants",
    description="Compare two or more variants side by side, showing differences in consequence, frequency, ClinVar evidence, and rank scores.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The job ID"
            },
            "variant_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of variant IDs to compare (2-5)"
            }
        },
        "required": ["job_id", "variant_ids"]
    }
)

search_pubmed_fn = FunctionDeclaration(
    name="search_pubmed",
    description="Search PubMed for literature about a gene and disease/phenotype. Returns relevant abstracts.",
    parameters={
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g., BRCA2, SCN1A)"
            },
            "condition": {
                "type": "string",
                "description": "Disease or phenotype to search for"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of abstracts to return (default 3)"
            }
        },
        "required": ["gene"]
    }
)

get_panelapp_gene_fn = FunctionDeclaration(
    name="get_panelapp_gene",
    description="Look up a gene in PanelApp to see which disease panels it belongs to and its evidence level.",
    parameters={
        "type": "object",
        "properties": {
            "gene_symbol": {
                "type": "string",
                "description": "Gene symbol (e.g., BRCA1)"
            }
        },
        "required": ["gene_symbol"]
    }
)

draft_report_section_fn = FunctionDeclaration(
    name="draft_report_section",
    description="Draft a structured clinical evidence summary section for one or more shortlisted variants, suitable for inclusion in a case report.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The job ID"
            },
            "variant_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variant IDs to include in the report section"
            },
            "report_style": {
                "type": "string",
                "description": "Report style: 'clinical' or 'research' (default: clinical)"
            }
        },
        "required": ["job_id", "variant_ids"]
    }
)

get_clinvar_entry_fn = FunctionDeclaration(
    name="get_clinvar_entry",
    description="Retrieve the ClinVar entry for a variant by its ClinVar ID or variant notation.",
    parameters={
        "type": "object",
        "properties": {
            "clinvar_id": {
                "type": "string",
                "description": "ClinVar Variation ID"
            },
            "gene": {
                "type": "string",
                "description": "Gene symbol as fallback search"
            }
        },
        "required": []
    }
)

lookup_omim_fn = FunctionDeclaration(
    name="lookup_omim",
    description="Look up a gene in OMIM to find associated diseases, inheritance mode (AD/AR/XL), MIM numbers, and known allelic variants. Essential for validating pathogenicity in a clinical context.",
    parameters={
        "type": "object",
        "properties": {
            "gene_symbol": {
                "type": "string",
                "description": "Gene symbol (e.g. BRCA1, SCN5A, MYBPC3)"
            }
        },
        "required": ["gene_symbol"]
    }
)

query_alphagenome_fn = FunctionDeclaration(
    name="query_alphagenome",
    description="Query the DeepMind AlphaGenome model for regulatory variant effect predictions, chromatin features, and splicing disruption scores.",
    parameters={
        "type": "object",
        "properties": {
            "variant_id": {
                "type": "string",
                "description": "Variant ID or notation (e.g. 1-12345-A-T or rs123)"
            },
            "context_sequence": {
                "type": "string",
                "description": "Optional flanking DNA sequence if known"
            }
        },
        "required": ["variant_id"]
    }
)

# ─── Tool Collection ───────────────────────────────────────────────────────────

AGENT_TOOLS = Tool(
    function_declarations=[
        list_jobs_fn,
        get_job_status_fn,
        get_job_variants_fn,
        get_variant_detail_fn,
        explain_ranking_fn,
        compare_variants_fn,
        search_pubmed_fn,
        get_panelapp_gene_fn,
        draft_report_section_fn,
        get_clinvar_entry_fn,
        lookup_omim_fn,
        query_alphagenome_fn,
    ]
)
