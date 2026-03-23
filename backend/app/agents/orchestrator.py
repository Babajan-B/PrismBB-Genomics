"""
Orchestrator Agent — Multi-Agent Gemini System
Routes user queries to specialized sub-agents via function calling.
All answers are grounded in database evidence — no hallucination.
"""
import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import google.generativeai as genai

from app.config import settings
from app.agents.tools import AGENT_TOOLS
from app.agents.literature_agent import search_pubmed
from app.agents.alphagenome_agent import alphagenome_agent
from app.pipeline.annotation import get_panelapp_info
from app.pipeline.check_agent import lookup_omim_gene
from app.models.job import Job
from app.models.variant import Variant
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Variant Interpretation Agent, an AI assistant specializing in clinical genomics and VCF analysis.

You help clinicians, researchers, and bioinformaticians interpret genomic variants from VCF files.

CRITICAL RULES:
1. You MUST only answer from computed evidence stored in the database. Use the provided tools to retrieve data.
2. NEVER fabricate variant classifications, frequencies, gene-disease relationships, or paper citations.
3. Always cite your evidence source (ClinVar ID, gnomAD AF, PubMed PMID, etc.)
4. Clearly label outputs as "decision-support" — not clinical diagnosis.
5. If the data is unavailable, say so clearly rather than guessing.

You have access to these tools:
- list_jobs / get_job_status: View analysis runs
- get_job_variants: Retrieve ranked candidate variants
- get_variant_detail / explain_ranking: Deep evidence for a specific variant
- compare_variants: Side-by-side comparison
- search_pubmed: Literature search (PubMed)
- get_panelapp_gene: Gene panel membership
- draft_report_section: Generate structured report text
- get_clinvar_entry: ClinVar record lookup
- lookup_omim: OMIM gene-disease lookup — returns disease name, inheritance mode (AD/AR/XL), MIM numbers
- query_alphagenome: DeepMind prediction for regulatory variants

When asked about a variant's disease relevance or inheritance, ALWAYS call lookup_omim first to ground your answer.
Always be concise, evidence-based, and cite specific data points."""


class OrchestratorAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            tools=[AGENT_TOOLS],
            system_instruction=SYSTEM_PROMPT,
        )

    async def chat(
        self,
        user_message: str,
        job_id: Optional[str] = None,
        chat_history: list = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the agent loop.
        Returns {response: str, tool_calls: list, evidence_sources: list}
        """
        if not settings.gemini_api_key:
            return {
                "response": "Gemini API key not configured. Please set GEMINI_API_KEY in your .env file.",
                "tool_calls": [],
                "evidence_sources": [],
            }

        # Build context message
        context = ""
        if job_id:
            context = f"\n[Current analysis job: {job_id}]"

        messages = []
        if chat_history:
            messages = chat_history.copy()

        messages.append({
            "role": "user",
            "parts": [user_message + context]
        })

        tool_calls_log = []
        evidence_sources = []
        max_iterations = 8
        iteration = 0

        chat = self.model.start_chat(history=messages[:-1] if len(messages) > 1 else [])

        try:
            response = await self._async_generate(chat, messages[-1]["parts"][0])

            while iteration < max_iterations:
                iteration += 1

                # Check for function calls
                if not response.candidates:
                    break

                candidate = response.candidates[0]
                if not candidate.content.parts:
                    break

                has_function_call = any(
                    hasattr(p, "function_call") and p.function_call.name
                    for p in candidate.content.parts
                )

                if not has_function_call:
                    # Final text response
                    break

                # Process all function calls
                tool_results = []
                for part in candidate.content.parts:
                    if not hasattr(part, "function_call") or not part.function_call.name:
                        continue

                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)

                    logger.info(f"Agent calling tool: {fn_name}({fn_args})")
                    tool_calls_log.append({"tool": fn_name, "args": fn_args})

                    result = await self._dispatch_tool(fn_name, fn_args, job_id)
                    evidence_sources.extend(self._extract_sources(fn_name, result))

                    tool_results.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": json.dumps(result, default=str)}
                            )
                        )
                    )

                # Send tool results back to model
                response = await self._async_send_tool_results(chat, tool_results)

        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "tool_calls": tool_calls_log,
                "evidence_sources": evidence_sources,
            }

        # Extract final text
        final_text = ""
        try:
            final_text = response.text
        except Exception:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text"):
                    final_text += part.text

        return {
            "response": final_text or "I was unable to generate a response. Please try rephrasing.",
            "tool_calls": tool_calls_log,
            "evidence_sources": evidence_sources,
        }

    async def _async_generate(self, chat, message: str):
        """Async wrapper for Gemini chat."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: chat.send_message(message))

    async def _async_send_tool_results(self, chat, tool_results):
        """Async wrapper for sending tool results."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: chat.send_message(tool_results))

    async def _dispatch_tool(self, fn_name: str, args: dict, job_id: Optional[str]) -> dict:
        """Dispatch tool call to the appropriate handler."""
        try:
            if fn_name == "list_jobs":
                return await self._tool_list_jobs(args.get("limit", 10))

            elif fn_name == "get_job_status":
                return await self._tool_get_job_status(args.get("job_id", job_id))

            elif fn_name == "get_job_variants":
                jid = args.get("job_id", job_id)
                return await self._tool_get_variants(
                    jid, args.get("limit", 20), args.get("min_impact")
                )

            elif fn_name == "get_variant_detail":
                return await self._tool_get_variant_detail(
                    args.get("job_id", job_id), args.get("variant_id")
                )

            elif fn_name == "explain_ranking":
                return await self._tool_explain_ranking(
                    args.get("job_id", job_id), args.get("variant_id")
                )

            elif fn_name == "compare_variants":
                return await self._tool_compare_variants(
                    args.get("job_id", job_id), args.get("variant_ids", [])
                )

            elif fn_name == "search_pubmed":
                return await search_pubmed(
                    gene=args.get("gene", ""),
                    condition=args.get("condition"),
                    max_results=args.get("max_results", 3),
                )

            elif fn_name == "get_panelapp_gene":
                panels = await get_panelapp_info(args.get("gene_symbol", ""))
                return {"gene": args.get("gene_symbol"), "panels": panels}

            elif fn_name == "draft_report_section":
                return await self._tool_draft_report(
                    args.get("job_id", job_id),
                    args.get("variant_ids", []),
                    args.get("report_style", "clinical"),
                )

            elif fn_name == "get_clinvar_entry":
                return await self._tool_get_clinvar(
                    args.get("clinvar_id"), args.get("gene")
                )

            elif fn_name == "lookup_omim":
                return await self._tool_lookup_omim(args.get("gene_symbol", ""))

            elif fn_name == "query_alphagenome":
                return alphagenome_agent.query_regulatory_effect(
                    args.get("variant_id"), args.get("context_sequence")
                )

            else:
                return {"error": f"Unknown tool: {fn_name}"}

        except Exception as e:
            logger.error(f"Tool {fn_name} error: {e}")
            return {"error": str(e)}

    # ─── Tool Implementations ───────────────────────────────────────────────

    async def _tool_list_jobs(self, limit: int = 10) -> dict:
        result = await self.db.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit)
        )
        jobs = result.scalars().all()
        return {
            "jobs": [
                {
                    "id": j.id,
                    "status": j.status,
                    "filename": j.vcf_filename,
                    "genome_build": j.genome_build,
                    "variant_count": j.variant_count,
                    "created_at": str(j.created_at),
                }
                for j in jobs
            ]
        }

    async def _tool_get_job_status(self, job_id: str) -> dict:
        if not job_id:
            return {"error": "No job_id provided"}
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return {"error": f"Job {job_id} not found"}
        return {
            "id": job.id,
            "status": job.status,
            "filename": job.vcf_filename,
            "genome_build": job.genome_build,
            "sample_count": job.sample_count,
            "variant_count": job.variant_count,
            "hpo_terms": job.hpo_terms,
            "qc_summary": job.qc_summary,
            "pipeline_version": job.pipeline_version,
            "created_at": str(job.created_at),
        }

    async def _tool_get_variants(
        self, job_id: str, limit: int = 20, min_impact: str = None
    ) -> dict:
        if not job_id:
            return {"error": "No job_id provided"}
        query = select(Variant).where(Variant.job_id == job_id)
        if min_impact:
            impact_order = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}
            min_val = impact_order.get(min_impact.upper(), 0)
            allowed = [k for k, v in impact_order.items() if v >= min_val]
            query = query.where(Variant.impact.in_(allowed))
        query = query.order_by(Variant.rank_position).limit(limit)
        result = await self.db.execute(query)
        variants = result.scalars().all()
        return {
            "job_id": job_id,
            "count": len(variants),
            "variants": [
                {
                    "id": v.id,
                    "rank": v.rank_position,
                    "variant": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
                    "gene": v.gene,
                    "consequence": v.consequence,
                    "impact": v.impact,
                    "zygosity": v.zygosity,
                    "gnomad_af": v.gnomad_af,
                    "clinvar": v.clinvar_significance,
                    "rank_score": v.rank_score,
                    "hgvs_p": v.hgvs_p,
                }
                for v in variants
            ]
        }

    async def _tool_get_variant_detail(self, job_id: str, variant_id: str) -> dict:
        result = await self.db.execute(
            select(Variant).where(Variant.id == variant_id, Variant.job_id == job_id)
        )
        v = result.scalar_one_or_none()
        if not v:
            return {"error": f"Variant {variant_id} not found"}
        return {
            "id": v.id,
            "variant": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
            "gene": v.gene,
            "transcript": v.transcript,
            "hgvs_c": v.hgvs_c,
            "hgvs_p": v.hgvs_p,
            "consequence": v.consequence,
            "impact": v.impact,
            "zygosity": v.zygosity,
            "genotype": v.genotype,
            "gnomad_af": v.gnomad_af,
            "gnomad_af_popmax": v.gnomad_af_popmax,
            "clinvar_id": v.clinvar_id,
            "clinvar_significance": v.clinvar_significance,
            "clinvar_review_status": v.clinvar_review_status,
            "panelapp_panels": v.panelapp_panels,
            "rank_score": v.rank_score,
            "rank_position": v.rank_position,
            "rank_details": v.rank_details,
        }

    async def _tool_explain_ranking(self, job_id: str, variant_id: str) -> dict:
        result = await self.db.execute(
            select(Variant).where(Variant.id == variant_id, Variant.job_id == job_id)
        )
        v = result.scalar_one_or_none()
        if not v:
            return {"error": f"Variant {variant_id} not found"}
        return {
            "variant": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
            "gene": v.gene,
            "rank_position": v.rank_position,
            "total_score": v.rank_score,
            "score_breakdown": v.rank_details,
            "explanation_context": {
                "gnomad_af": v.gnomad_af,
                "impact": v.impact,
                "consequence": v.consequence,
                "clinvar_significance": v.clinvar_significance,
                "zygosity": v.zygosity,
                "panelapp_panels": v.panelapp_panels,
            }
        }

    async def _tool_compare_variants(self, job_id: str, variant_ids: list) -> dict:
        if not variant_ids:
            return {"error": "No variant IDs provided"}
        result = await self.db.execute(
            select(Variant).where(Variant.id.in_(variant_ids), Variant.job_id == job_id)
        )
        variants = result.scalars().all()
        return {
            "comparison": [
                {
                    "id": v.id,
                    "rank": v.rank_position,
                    "variant": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
                    "gene": v.gene,
                    "hgvs_p": v.hgvs_p,
                    "impact": v.impact,
                    "consequence": v.consequence,
                    "gnomad_af": v.gnomad_af,
                    "clinvar": v.clinvar_significance,
                    "zygosity": v.zygosity,
                    "rank_score": v.rank_score,
                    "rank_details": v.rank_details,
                }
                for v in sorted(variants, key=lambda x: x.rank_position or 999)
            ]
        }

    async def _tool_draft_report(
        self, job_id: str, variant_ids: list, style: str = "clinical"
    ) -> dict:
        result = await self.db.execute(
            select(Variant).where(Variant.id.in_(variant_ids), Variant.job_id == job_id)
        )
        variants = result.scalars().all()

        sections = []
        for v in sorted(variants, key=lambda x: x.rank_position or 999):
            section = {
                "variant_header": f"{v.gene or 'Unknown'}: {v.hgvs_p or v.hgvs_c or f'{v.chrom}:{v.pos}{v.ref}>{v.alt}'}",
                "genomic_position": f"{v.chrom}:{v.pos} {v.ref}>{v.alt}",
                "consequence": v.consequence,
                "impact": v.impact,
                "zygosity": v.zygosity,
                "population_frequency": f"gnomAD AF: {v.gnomad_af:.2e}" if v.gnomad_af else "Not in gnomAD",
                "clinical_evidence": v.clinvar_significance or "No ClinVar record",
                "panel_membership": ", ".join(v.panelapp_panels) if v.panelapp_panels else "Not on known panels",
                "priority_score": f"{v.rank_score:.3f} (rank #{v.rank_position})",
            }
            sections.append(section)

        return {
            "style": style,
            "sections": sections,
            "disclaimer": "This output is generated for decision-support purposes only and requires expert clinical review before use.",
        }

    async def _tool_lookup_omim(self, gene_symbol: str) -> dict:
        """Look up gene in OMIM via E-utilities."""
        import httpx
        async with httpx.AsyncClient() as client:
            result = await lookup_omim_gene(gene_symbol, client)
        if not result:
            return {"gene": gene_symbol, "error": "OMIM lookup failed or no results"}
        return result

    async def _tool_get_clinvar(self, clinvar_id: str = None, gene: str = None) -> dict:
        """Fetch ClinVar data via E-utilities."""
        import httpx
        if not clinvar_id and not gene:
            return {"error": "Provide clinvar_id or gene"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if clinvar_id:
                    r = await client.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                        params={"db": "clinvar", "id": clinvar_id, "retmode": "json"}
                    )
                    if r.status_code == 200:
                        data = r.json()
                        result_data = data.get("result", {})
                        uid = result_data.get("uids", [clinvar_id])[0]
                        record = result_data.get(str(uid), {})
                        return {
                            "clinvar_id": clinvar_id,
                            "title": record.get("title", ""),
                            "clinical_significance": record.get("clinical_significance", {}),
                            "genes": record.get("genes", []),
                        }
        except Exception as e:
            return {"error": str(e)}
        return {"message": "No ClinVar record found"}

    def _extract_sources(self, tool_name: str, result: dict) -> list:
        """Extract evidence source citations from tool results."""
        sources = []
        if tool_name == "search_pubmed":
            for r in result.get("results", []):
                sources.append({
                    "type": "PubMed",
                    "id": r.get("pmid"),
                    "url": r.get("url"),
                    "title": r.get("title"),
                })
        elif tool_name in ("get_variant_detail", "explain_ranking"):
            if result.get("clinvar_id"):
                sources.append({
                    "type": "ClinVar",
                    "id": result.get("clinvar_id"),
                    "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{result.get('clinvar_id')}/",
                })
            if result.get("gnomad_af") is not None:
                chrom_pos = result.get("variant", "")
                sources.append({"type": "gnomAD", "variant": chrom_pos})
        return sources
