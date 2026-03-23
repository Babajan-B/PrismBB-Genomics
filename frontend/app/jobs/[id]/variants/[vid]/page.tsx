"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getVariantDetail } from "@/lib/api";
import { 
  Loader2, 
  ExternalLink, 
  Dna, 
  Activity, 
  Stethoscope, 
  Microscope, 
  AlertCircle,
  ChevronRight,
  Target
} from "lucide-react";

function Field({ label, value, mono = false }: { label: string; value: unknown; mono?: boolean }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="py-4 border-b border-[var(--line)] last:border-0 group">
      <dt className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.2em] mb-1 group-hover:text-[var(--text-secondary)] transition-colors">{label}</dt>
      <dd className={`text-sm text-white ${mono ? "font-mono" : "font-semibold"} tracking-wide`}>
        {String(value)}
      </dd>
    </div>
  );
}

export default function VariantDetailPage() {
  const { id, vid } = useParams<{ id: string; vid: string }>();
  interface VariantDetail {
    id?: string;
    gene?: string;
    impact?: string;
    hgvs_p?: string;
    hgvs_c?: string;
    chrom?: string;
    pos?: number;
    ref?: string;
    alt?: string;
    clinvar_significance?: string;
    clinvar_review_status?: string;
    clinvar_id?: string;
    gnomad_af?: number;
    gnomad_af_popmax?: number;
    zygosity?: string;
    genotype?: string;
    transcript?: string;
    consequence?: string;
    panelapp_panels?: string[];
    alphamissense_score?: number | null;
    alphamissense_class?: string | null;
    acmg_score?: number | null;
    acmg_class?: string | null;
    acmg_rules?: string[];
    compound_het?: boolean | null;
    validation_status?: string | null;  // confirmed / conflict / unconfirmed / no_omim_entry
    omim_disease?: string | null;
    omim_inheritance?: string | null;
    rank_score?: number;
    rank_position?: number;
    rank_details?: {
      reasoning?: Record<string, { score?: number; weight?: number; note?: string }>;
    };
    detail?: string;
  }
  const [variant, setVariant] = useState<VariantDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getVariantDetail(id, vid).then((d) => { 
      setVariant(d as VariantDetail); 
      setLoading(false); 
    });
  }, [id, vid]);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
      <div className="relative mb-6">
        <div className="absolute inset-0 rounded-full bg-[var(--accent)] blur-[50px] opacity-20" />
        <Loader2 className="relative z-10 w-16 h-16 animate-spin text-[var(--accent)] drop-shadow-[0_0_15px_rgba(56,189,248,0.5)]" />
      </div>
      <p className="text-sm font-semibold tracking-widest text-[var(--accent)] uppercase">Loading Variant Data...</p>
    </div>
  );

  if (!variant || variant.detail) return (
    <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in-up">
      <div className="w-24 h-24 rounded-3xl bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(239,68,68,0.15)]">
        <AlertCircle className="w-12 h-12 text-[var(--error)]" />
      </div>
      <h2 className="text-4xl font-extrabold text-white mb-4 tracking-tight">Variant Not Found</h2>
      <p className="text-[var(--text-secondary)] mb-8 max-w-md text-center leading-relaxed text-base">The requested variant could not be found or has been removed from the current analysis run.</p>
      <Link href={`/jobs/${id}/variants`} className="btn-secondary px-6 py-3">
        Back to Variants
      </Link>
    </div>
  );

  const rd = (variant.rank_details as Record<string, unknown>) || {};
  const reasoning = (rd.reasoning as Record<string, Record<string, unknown>>) || {};

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
        <Link href={`/jobs/${id}`} style={{ color: "var(--text-2)", transition: "color 0.1s" }}
          onMouseEnter={e => (e.currentTarget.style.color = "var(--text)")}
          onMouseLeave={e => (e.currentTarget.style.color = "var(--text-2)")}>
          Analysis
        </Link>
        <ChevronRight className="w-3 h-3 opacity-40" />
        <Link href={`/jobs/${id}/variants`} style={{ color: "var(--text-2)", transition: "color 0.1s" }}
          onMouseEnter={e => (e.currentTarget.style.color = "var(--text)")}
          onMouseLeave={e => (e.currentTarget.style.color = "var(--text-2)")}>
          Variants
        </Link>
        <ChevronRight className="w-3 h-3 opacity-40" />
        <span style={{ color: "var(--text)", fontWeight: 600 }}>{(variant.gene as string) || "Variant"}</span>
      </div>

      {/* Clinical header card */}
      <div className="clinical-card">
        <div className="clinical-card-header" style={{ justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text)", margin: 0, letterSpacing: "-0.02em" }}>
              {(variant.gene as string) || "Unknown"}
            </h1>
            {variant.impact && (
              <span className={`badge badge-${String(variant.impact)}`}>
                {String(variant.impact)}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 9, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em", margin: 0 }}>Rank</p>
              <p style={{ fontSize: 11, color: "var(--text-2)", margin: "2px 0 0", fontWeight: 600 }}>#{variant.rank_position as number}</p>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 9, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em", margin: 0 }}>Score</p>
              <p style={{ fontSize: 22, fontWeight: 800, color: "var(--blue)", margin: "1px 0 0", letterSpacing: "-0.02em" }}>
                {((variant.rank_score as number) || 0).toFixed(3)}
              </p>
            </div>
          </div>
        </div>
        <div className="clinical-card-body" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <code style={{
            fontSize: 13, fontFamily: "monospace", fontWeight: 700,
            color: "var(--blue)", background: "var(--blue-dim)",
            border: "1px solid var(--blue-border)", padding: "3px 10px", borderRadius: 5,
          }}>
            {(variant.hgvs_p as string) || (variant.hgvs_c as string) || "No HGVS"}
          </code>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>·</span>
          <code style={{ fontSize: 12, fontFamily: "monospace", color: "var(--text-2)" }}>
            {variant.chrom as string}:{variant.pos as number}
          </code>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>·</span>
          <code style={{ fontSize: 12, fontFamily: "monospace", color: "var(--text-2)" }}>
            {variant.ref as string} → {variant.alt as string}
          </code>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="elevated-card p-6 sm:p-8 hover:border-[rgba(239,68,68,0.3)] transition-colors group">
            <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--line)]">
              <div className="icon-box icon-box-error group-hover:scale-110 shadow-inner">
                <Stethoscope className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-white tracking-wide">Clinical Evidence</h3>
            </div>
            
            <dl className="grid md:grid-cols-2 gap-x-8 gap-y-2">
              <Field label="ClinVar Significance" value={variant.clinvar_significance} />
              <Field label="Review Status" value={variant.clinvar_review_status} />
              {variant.clinvar_id && (
                <div className="md:col-span-2 pt-4">
                  <dt className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.2em] mb-2">
                    ClinVar Record
                  </dt>
                  <a 
                    href={`https://www.ncbi.nlm.nih.gov/clinvar/variation/${String(variant.clinvar_id)}/`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-[var(--surface-solid)] border border-[var(--line)] hover:border-[var(--accent-soft)] hover:bg-[var(--surface-muted)] text-[var(--accent)] rounded-xl text-sm font-bold tracking-wide transition-all shadow-[0_4px_10px_rgba(0,0,0,0.5)]"
                  >
                    View ID {variant.clinvar_id as string}
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              )}
            </dl>
          </div>

          {/* ACMG Classification */}
          {variant.acmg_class && (
            <div className="elevated-card p-6 sm:p-8 hover:border-[rgba(129,140,248,0.3)] transition-colors group">
              <div className="flex items-center gap-4 mb-6 pb-4 border-b border-[var(--line)]">
                <div className="icon-box bg-[rgba(129,140,248,0.1)] text-[#818CF8] border-[rgba(129,140,248,0.2)] group-hover:scale-110 shadow-inner">
                  <Microscope className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-white tracking-wide">ACMG Classification</h3>
              </div>
              <div className="flex flex-wrap gap-4 items-center mb-4">
                <span className={[
                  "px-4 py-2 rounded-xl text-sm font-bold border shadow-inner uppercase tracking-wider",
                  variant.acmg_class === "Pathogenic" ? "bg-[rgba(239,68,68,0.12)] text-[var(--error)] border-[rgba(239,68,68,0.3)]" :
                  variant.acmg_class === "Likely Pathogenic" ? "bg-[rgba(245,158,11,0.12)] text-[var(--warning)] border-[rgba(245,158,11,0.3)]" :
                  variant.acmg_class === "VUS" ? "bg-[rgba(56,189,248,0.1)] text-[var(--accent)] border-[rgba(56,189,248,0.2)]" :
                  "bg-[rgba(16,185,129,0.1)] text-[var(--success)] border-[rgba(16,185,129,0.3)]"
                ].join(" ")}>
                  {variant.acmg_class}
                </span>
                {variant.acmg_score != null && (
                  <span className="text-sm text-[var(--text-secondary)] font-mono bg-[var(--surface-solid)] px-3 py-1.5 rounded-lg border border-[var(--line)]">
                    Score: {variant.acmg_score}
                  </span>
                )}
                {variant.compound_het && (
                  <span className="px-3 py-1.5 rounded-xl text-xs font-bold bg-[rgba(245,158,11,0.1)] text-[var(--warning)] border border-[rgba(245,158,11,0.2)] uppercase tracking-wider">
                    Compound Het
                  </span>
                )}
              </div>
              {variant.acmg_rules && variant.acmg_rules.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {variant.acmg_rules.map((rule) => (
                    <span key={rule} className="px-3 py-1 rounded-lg text-xs font-mono font-bold bg-[var(--surface-solid)] text-[#818CF8] border border-[rgba(129,140,248,0.2)]">
                      {rule}
                    </span>
                  ))}
                </div>
              )}
              {/* Check Agent OMIM Validation */}
              {variant.validation_status && (
                <div className="mt-5 pt-5 border-t border-[var(--line)]">
                  <p className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.2em] mb-2">Check Agent — OMIM Validation</p>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={[
                      "px-3 py-1.5 rounded-lg text-xs font-bold border uppercase tracking-wider",
                      variant.validation_status === "confirmed" ? "bg-[rgba(16,185,129,0.1)] text-[var(--success)] border-[rgba(16,185,129,0.3)]" :
                      variant.validation_status === "conflict" ? "bg-[rgba(239,68,68,0.1)] text-[var(--error)] border-[rgba(239,68,68,0.3)]" :
                      variant.validation_status === "no_omim_entry" ? "bg-[rgba(100,116,139,0.1)] text-[var(--text-muted)] border-[rgba(100,116,139,0.2)]" :
                      "bg-[rgba(245,158,11,0.1)] text-[var(--warning)] border-[rgba(245,158,11,0.3)]"
                    ].join(" ")}>
                      {(variant.validation_status ?? "").replace(/_/g, " ")}
                    </span>
                    {variant.omim_inheritance && (
                      <span className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[var(--surface-solid)] text-[var(--text-secondary)] border border-[var(--line)]">
                        {variant.omim_inheritance}
                      </span>
                    )}
                  </div>
                  {variant.omim_disease && (
                    <p className="mt-2 text-sm text-white font-semibold">{variant.omim_disease}</p>
                  )}
                </div>
              )}

              {/* AlphaMissense */}
              {variant.alphamissense_score != null && (
                <div className="mt-5 pt-5 border-t border-[var(--line)]">
                  <p className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.2em] mb-2">AlphaMissense (DeepMind AI)</p>
                  <div className="flex items-center gap-4">
                    <span className={[
                      "px-3 py-1.5 rounded-lg text-xs font-bold border uppercase tracking-wider",
                      variant.alphamissense_class === "likely_pathogenic" ? "bg-[rgba(239,68,68,0.1)] text-[var(--error)] border-[rgba(239,68,68,0.3)]" :
                      variant.alphamissense_class === "likely_benign" ? "bg-[rgba(16,185,129,0.1)] text-[var(--success)] border-[rgba(16,185,129,0.3)]" :
                      "bg-[rgba(56,189,248,0.1)] text-[var(--accent)] border-[rgba(56,189,248,0.2)]"
                    ].join(" ")}>
                      {(variant.alphamissense_class ?? "").replace(/_/g, " ")}
                    </span>
                    <span className="font-mono text-sm font-bold text-[var(--text-secondary)]">
                      {variant.alphamissense_score.toFixed(4)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="elevated-card p-6 sm:p-8 hover:border-[rgba(16,185,129,0.3)] transition-colors group">
            <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--line)]">
              <div className="icon-box icon-box-success group-hover:scale-110 shadow-inner">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-white tracking-wide">Population Frequency</h3>
            </div>
            
            <dl className="grid md:grid-cols-2 gap-x-8 gap-y-2">
              <Field 
                label="gnomAD Allele Frequency" 
                value={variant.gnomad_af != null ? Number(variant.gnomad_af).toExponential(3) : "Not in gnomAD"} 
                mono
              />
              <Field 
                label="gnomAD PopMax" 
                value={variant.gnomad_af_popmax != null ? Number(variant.gnomad_af_popmax).toExponential(3) : "—"} 
                mono
              />
              <Field label="Zygosity" value={variant.zygosity} />
              <Field label="Genotype" value={variant.genotype} mono />
            </dl>
          </div>

          <div className="elevated-card p-6 sm:p-8 hover:border-[rgba(245,158,11,0.3)] transition-colors group">
            <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--line)]">
              <div className="icon-box icon-box-warning group-hover:scale-110 shadow-inner">
                <Dna className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-white tracking-wide">Transcript & Consequence</h3>
            </div>
            
            <dl className="grid md:grid-cols-2 gap-x-8 gap-y-2">
              <Field label="Canonical Transcript" value={variant.transcript} mono />
              <Field label="HGVS c." value={variant.hgvs_c} mono />
              <Field label="HGVS p." value={variant.hgvs_p} mono />
              <Field 
                label="Consequence" 
                value={(variant.consequence as string)?.replace(/_/g, " ")} 
              />
            </dl>
          </div>

          <div className="elevated-card p-6 sm:p-8 hover:border-[rgba(129,140,248,0.3)] transition-colors group">
            <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--line)]">
              <div className="icon-box bg-[rgba(129,140,248,0.1)] text-[#818CF8] border-[rgba(129,140,248,0.2)] group-hover:scale-110 shadow-inner">
                <Microscope className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-white tracking-wide">Disease Panels</h3>
            </div>
            
            {(variant.panelapp_panels as string[])?.length ? (
              <div className="flex flex-wrap gap-3">
                {(variant.panelapp_panels as string[]).map((p) => (
                  <span 
                    key={p} 
                    className="px-4 py-2 bg-[rgba(129,140,248,0.1)] text-[#818CF8] rounded-xl text-sm font-bold border border-[rgba(129,140,248,0.25)] shadow-inner"
                  >
                    {p}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-[var(--text-secondary)] italic text-sm">Not associated with any known disease panels.</p>
            )}
          </div>
        </div>

        <div className="lg:col-span-1">
          <div className="glass-card p-6 sm:p-8 sticky top-32 card-glow">
            <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--line)]">
              <div className="icon-box icon-box-primary shadow-inner">
                <Target className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-white tracking-wide">Score Breakdown</h3>
            </div>

            <div className="space-y-6">
              {Object.entries(reasoning).map(([key, val]) => {
                const r = val as { score?: number; weight?: number; note?: string } | undefined;
                const score = r?.score || 0;
                const weight = r?.weight || 0;
                
                return (
                  <div key={key} className="group">
                    <div className="flex items-end justify-between mb-2">
                      <span className="text-xs font-bold text-white uppercase tracking-wider">{key}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[var(--text-muted)] bg-[var(--surface-solid)] px-2 py-0.5 rounded border border-[var(--line)] font-mono">w={weight}</span>
                        <span className="font-mono text-sm font-bold text-[var(--accent)]">{score.toFixed(3)}</span>
                      </div>
                    </div>
                    <div className="h-2.5 bg-[var(--surface-solid)] border border-[var(--line)] rounded-full overflow-hidden shadow-inner">
                      <div 
                        className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-alt)] rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(56,189,248,0.5)]"
                        style={{ width: `${score * 100}%` }}
                      />
                    </div>
                    {r?.note && (
                      <p className="text-[11px] text-[var(--text-secondary)] mt-2 leading-relaxed opacity-80 group-hover:opacity-100 transition-opacity">{r.note}</p>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-8 pt-6 border-t border-[var(--line)] bg-[var(--surface-solid)] -mx-6 sm:-mx-8 -mb-6 sm:-mb-8 p-6 sm:p-8 rounded-b-20 border-x-0 border-b-0 shadow-inner">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider">Total Output</span>
                <span className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-[var(--accent)] drop-shadow-[0_0_10px_rgba(56,189,248,0.3)]">
                  {((variant.rank_score as number) || 0).toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
