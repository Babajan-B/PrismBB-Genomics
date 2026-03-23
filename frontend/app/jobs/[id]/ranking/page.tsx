"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getVariants } from "@/lib/api";
import { Crown, Loader2, Medal, Trophy, TrendingUp, Dna, ChevronRight, Award } from "lucide-react";

interface RankingVariant {
  id?: string;
  rank?: number;
  gene?: string;
  impact?: string;
  hgvs_p?: string;
  hgvs_c?: string;
  chrom?: string;
  pos?: number;
  zygosity?: string;
  consequence?: string;
  rank_score?: number;
  rank_details?: {
    rarity_score?: number;
    impact_score?: number;
    clinvar_score?: number;
    phenotype_score?: number;
    inheritance_score?: number;
    panel_score?: number;
  };
  clinvar_significance?: string;
  gnomad_af?: number;
  acmg_class?: string;
  validation_status?: string;
  compound_het?: boolean;
  omim_disease?: string;
}

/* ── Score factor config ──────────────────────────────────── */
const SCORE_FACTORS = [
  { key: "rarity_score",     label: "Rarity",      color: "#12B76A", weight: "25%" },
  { key: "impact_score",     label: "Impact",       color: "#F79009", weight: "25%" },
  { key: "clinvar_score",    label: "ClinVar",      color: "#F04438", weight: "20%" },
  { key: "phenotype_score",  label: "Phenotype",    color: "#2E90FA", weight: "15%" },
  { key: "inheritance_score",label: "Inheritance",  color: "#7F56D9", weight: "10%" },
  { key: "panel_score",      label: "Panel",        color: "#06B6D4", weight: "5%"  },
] as const;

/* ── ACMG badge helper ──────────────────────────────────── */
function AcmgChip({ acmg }: { acmg?: string }) {
  if (!acmg) return null;
  const c = acmg.toLowerCase();
  let cls = "badge badge-vus";
  if (c === "pathogenic") cls = "badge badge-path";
  else if (c.includes("likely pathogenic") || c.includes("likely_pathogenic")) cls = "badge badge-lpath";
  else if (c.includes("likely benign") || c.includes("likely_benign")) cls = "badge badge-lbenign";
  else if (c.includes("benign")) cls = "badge badge-benign";
  return <span className={cls}>{acmg}</span>;
}

/* ── Rank medal ────────────────────────────────────────── */
function RankMedal({ index }: { index: number }) {
  if (index === 0) return (
    <div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #F59E0B, #B45309)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <Crown size={22} color="white" />
    </div>
  );
  if (index === 1) return (
    <div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #94A3B8, #475569)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <Medal size={22} color="white" />
    </div>
  );
  if (index === 2) return (
    <div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #F97316, #C2410C)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <Trophy size={22} color="white" />
    </div>
  );
  return (
    <div style={{
      width: 48, height: 48, borderRadius: 12,
      background: "var(--surface-2)", border: "1px solid var(--border)",
      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
      fontSize: 18, fontWeight: 800, color: "var(--text-2)",
    }}>
      {index + 1}
    </div>
  );
}

/* ── Factor radar bars (horizontal) ─────────────────────── */
function FactorBars({ details }: { details: Record<string, number> }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 20px" }}>
      {SCORE_FACTORS.map(f => {
        const score = details[f.key] || 0;
        const pct = Math.min(Math.round(score * 100), 100);
        return (
          <div key={f.key}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: f.color, flexShrink: 0 }} />
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-2)" }}>{f.label}</span>
                <span style={{ fontSize: 10, color: "var(--text-3)" }}>·{f.weight}</span>
              </div>
              <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, color: f.color }}>{score.toFixed(2)}</span>
            </div>
            <div style={{ height: 5, background: "var(--bg-alt)", borderRadius: 99, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${pct}%`, background: f.color, borderRadius: 99, transition: "width 0.8s ease" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Classification spectrum bar (Franklin signature) ──── */
function ClassificationSpectrum({ score }: { score: number }) {
  const pct = Math.min((score || 0) * 100, 100);
  const label = pct > 75 ? "Likely Pathogenic" : pct > 50 ? "VUS" : pct > 25 ? "Likely Benign" : "Benign";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 10, color: "var(--text-3)", fontWeight: 600 }}>
        <span>Benign</span>
        <span style={{ color: "var(--text-2)", fontWeight: 700 }}>{label}</span>
        <span>Pathogenic</span>
      </div>
      <div className="classification-bar">
        <div className="classification-pointer" style={{ left: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RankingPage() {
  const { id } = useParams<{ id: string }>();
  const [variants, setVariants] = useState<RankingVariant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const data = (await getVariants(id, { limit: 20 })) as { variants?: RankingVariant[] };
      if (!mounted) return;
      setVariants(data.variants || []);
      setLoading(false);
    }
    void load();
    return () => { mounted = false; };
  }, [id]);

  /* ── Summary stats ── */
  const topScore = variants[0]?.rank_score || 0;
  const avgScore = useMemo(() => {
    if (!variants.length) return 0;
    return variants.reduce((acc, v) => acc + (v.rank_score || 0), 0) / variants.length;
  }, [variants]);

  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "50vh", gap: 12 }} className="animate-fade-in">
      <Loader2 size={24} className="animate-spin" style={{ color: "var(--blue)" }} />
      <p style={{ fontSize: 12, color: "var(--text-2)", letterSpacing: "0.05em" }}>Loading priority rankings…</p>
    </div>
  );

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: 22 }}>

      {/* ── Page header ─────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <p className="section-label"><TrendingUp size={11} style={{ display: "inline", marginRight: 5 }} />Priority Ranking</p>
          <h1 className="section-title" style={{ marginTop: 4 }}>Top Prioritized Variants</h1>
          <p className="section-sub">Candidates ranked by composite 6-factor biological scoring model.</p>
        </div>
      </div>

      {/* ── Summary stats row ──────────────────────────────────── */}
      {variants.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            { label: "Candidates",    value: variants.length,      unit: "ranked",       color: "var(--text)",   icon: <Award size={15} /> },
            { label: "Top Score",     value: topScore.toFixed(3),  unit: "composite",    color: "var(--red)",    icon: <Crown size={15} /> },
            { label: "Avg Score",     value: avgScore.toFixed(3),  unit: "all variants", color: "var(--amber)",  icon: <TrendingUp size={15} /> },
            { label: "High Impact",   value: variants.filter(v => v.impact === "HIGH").length, unit: "variants", color: "var(--purple)", icon: <Dna size={15} /> },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <p className="stat-label">{s.label}</p>
                <div style={{ color: s.color, opacity: 0.7 }}>{s.icon}</div>
              </div>
              <p style={{ fontSize: 26, fontWeight: 800, color: s.color, margin: 0, letterSpacing: "-0.03em", lineHeight: 1 }}>{s.value}</p>
              <p style={{ fontSize: 11, color: "var(--text-3)", marginTop: 3 }}>{s.unit}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Ranking cards ──────────────────────────────────────── */}
      {variants.length === 0 ? (
        <div className="clinical-card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "64px 24px", gap: 14, textAlign: "center" }}>
          <div className="icon-box icon-box-amber" style={{ width: 48, height: 48 }}><Trophy size={22} /></div>
          <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", margin: 0 }}>No ranked variants yet</p>
          <p style={{ fontSize: 13, color: "var(--text-2)", margin: 0 }}>Rankings appear once annotation and scoring complete.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {variants.map((variant, index) => {
            const details = (variant.rank_details as Record<string, number>) || {};
            const isTop = index < 3;
            const score = variant.rank_score || 0;
            const scorePct = Math.min(Math.round(score * 100), 100);
            const topBorderColor = index === 0 ? "#F59E0B" : index === 1 ? "#94A3B8" : "#F97316";

            return (
              <div
                key={variant.id || index}
                className="clinical-card"
                style={{
                  borderColor: isTop ? topBorderColor : "var(--border)",
                  borderWidth: isTop ? 1 : 1,
                  overflow: "visible",
                  boxShadow: isTop ? `0 4px 16px rgba(0,0,0,0.07)` : "var(--shadow-xs)",
                }}
              >
                {/* Card header */}
                <div className="clinical-card-header">
                  <RankMedal index={index} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <Link
                        href={`/jobs/${id}/variants/${variant.id}`}
                        style={{ fontSize: 18, fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}
                        onMouseEnter={e => (e.currentTarget.style.color = "var(--blue)")}
                        onMouseLeave={e => (e.currentTarget.style.color = "var(--text)")}
                      >
                        {variant.gene || "Unknown"}
                      </Link>
                      {variant.impact && (
                        <span className={`badge badge-${variant.impact}`}>{variant.impact}</span>
                      )}
                      {variant.acmg_class && <AcmgChip acmg={variant.acmg_class} />}
                      {variant.compound_het && (
                        <span style={{ fontSize: 10, fontWeight: 700, color: "var(--purple)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Comp.Het</span>
                      )}
                    </div>
                    <p style={{ fontSize: 12, fontFamily: "monospace", color: "var(--blue)", fontWeight: 600, margin: "4px 0 0", background: "var(--blue-dim)", display: "inline-block", padding: "2px 8px", borderRadius: 5 }}>
                      {variant.hgvs_p || variant.hgvs_c || `${variant.chrom}:${variant.pos}`}
                    </p>
                  </div>

                  {/* Total score display */}
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-3)", margin: 0 }}>Composite Score</p>
                    <p style={{ fontSize: 28, fontWeight: 800, color: isTop ? "var(--blue)" : "var(--text)", margin: "2px 0 0", letterSpacing: "-0.04em", lineHeight: 1 }}>
                      {score.toFixed(3)}
                    </p>
                    {/* Mini score bar */}
                    <div style={{ width: 100, height: 4, background: "var(--bg-alt)", borderRadius: 99, overflow: "hidden", marginTop: 6, marginLeft: "auto" }}>
                      <div style={{ height: "100%", width: `${scorePct}%`, background: "var(--blue)", borderRadius: 99 }} />
                    </div>
                  </div>
                </div>

                {/* Card body: factor bars + meta */}
                <div className="clinical-card-body" style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 24, alignItems: "start" }}>
                  {/* Factor contribution bars */}
                  <div>
                    <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-3)", marginBottom: 12 }}>Factor Contributions</p>
                    <FactorBars details={details} />
                  </div>

                  {/* Right: metadata + spectrum */}
                  <div style={{ minWidth: 200 }}>
                    {/* Classification spectrum */}
                    <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-3)", marginBottom: 10 }}>Classification Spectrum</p>
                    <ClassificationSpectrum score={score} />

                    {/* Meta pills */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
                      {variant.zygosity && (
                        <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text-2)", fontWeight: 600 }}>
                          {variant.zygosity}
                        </span>
                      )}
                      {variant.consequence && (
                        <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text-2)", fontWeight: 600 }}>
                          {variant.consequence}
                        </span>
                      )}
                      {variant.gnomad_af != null && (
                        <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, background: "var(--blue-dim)", border: "1px solid var(--blue-border)", color: "var(--blue)", fontWeight: 600 }}>
                          gnomAD: {Number(variant.gnomad_af).toExponential(2)}
                        </span>
                      )}
                    </div>

                    {variant.omim_disease && (
                      <p style={{ marginTop: 10, fontSize: 11, color: "var(--text-3)" }}>
                        <span style={{ fontWeight: 700 }}>OMIM:</span> {variant.omim_disease}
                      </p>
                    )}

                    <Link
                      href={`/jobs/${id}/variants/${variant.id}`}
                      className="btn-primary"
                      style={{ marginTop: 14, fontSize: 12, gap: 5 }}
                    >
                      View Evidence <ChevronRight size={12} />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
