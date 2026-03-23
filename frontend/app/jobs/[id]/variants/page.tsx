"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getVariants } from "@/lib/api";
import { AlertCircle, Filter, Loader2, Search, Layers, TrendingUp, Activity, ChevronRight } from "lucide-react";

interface VariantSummary {
  id: string;
  rank: number;
  gene?: string;
  chrom?: string;
  pos?: number;
  ref?: string;
  alt?: string;
  impact?: string;
  gnomad_af?: number | null;
  clinvar_significance?: string;
  acmg_class?: string | null;
  alphamissense_class?: string | null;
  compound_het?: boolean | null;
  validation_status?: string | null;
  rank_score?: number;
}

/* ── Classification helpers ─────────────────────────────────── */
function getImpactBadgeClass(impact?: string) {
  if (!impact) return "";
  const map: Record<string, string> = {
    HIGH:     "badge badge-HIGH",
    MODERATE: "badge badge-MODERATE",
    LOW:      "badge badge-LOW",
    MODIFIER: "badge badge-MODIFIER",
  };
  return map[impact] || "badge badge-MODIFIER";
}

function getAcmgBadgeClass(acmg?: string | null) {
  if (!acmg) return "";
  const c = acmg.toLowerCase();
  if (c === "pathogenic") return "badge badge-path";
  if (c.includes("likely pathogenic") || c.includes("likely_pathogenic")) return "badge badge-lpath";
  if (c.includes("vus") || c.includes("uncertain")) return "badge badge-vus";
  if (c.includes("likely benign") || c.includes("likely_benign")) return "badge badge-lbenign";
  if (c.includes("benign")) return "badge badge-benign";
  return "badge badge-vus";
}

function getClinVarBadgeClass(sig?: string) {
  if (!sig) return "";
  const c = sig.toLowerCase();
  if (c.includes("pathogenic") && !c.includes("likely_benign")) return "badge badge-path";
  if (c.includes("benign")) return "badge badge-benign";
  return "badge badge-lpath";
}

/* ── Mini bar chart strip ────────────────────────────────────── */
function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(Math.round((score || 0) * 100), 100);
  const color = pct > 70 ? "var(--red)" : pct > 40 ? "var(--amber)" : "var(--blue)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
      <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color, minWidth: 40 }}>
        {(score || 0).toFixed(3)}
      </span>
      <div style={{ flex: 1, height: 5, background: "var(--bg-alt)", borderRadius: 99, overflow: "hidden", minWidth: 60 }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 99, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

export default function VariantsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [variants, setVariants] = useState<VariantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [impact, setImpact] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      const data = (await getVariants(id, { limit: 100, min_impact: impact || undefined, gene: appliedSearch || undefined })) as { variants?: VariantSummary[] };
      if (!mounted) return;
      setVariants(data.variants || []);
      setLoading(false);
    }
    void load();
    return () => { mounted = false; };
  }, [appliedSearch, id, impact]);

  /* ── Computed stats for infographic header ─────────── */
  const stats = useMemo(() => {
    const high = variants.filter(v => v.impact === "HIGH").length;
    const moderate = variants.filter(v => v.impact === "MODERATE").length;
    const path = variants.filter(v => (v.acmg_class || "").toLowerCase().includes("pathogenic")).length;
    const novel = variants.filter(v => v.gnomad_af == null || v.gnomad_af === 0).length;
    return { high, moderate, path, novel };
  }, [variants]);

  /* ── Impact distribution for mini donut ─────────────── */
  const impactDist = useMemo(() => {
    const total = variants.length || 1;
    return [
      { label: "HIGH",     count: variants.filter(v => v.impact === "HIGH").length,     color: "var(--red)" },
      { label: "MOD",      count: variants.filter(v => v.impact === "MODERATE").length,  color: "var(--amber)" },
      { label: "LOW",      count: variants.filter(v => v.impact === "LOW").length,       color: "var(--blue)" },
      { label: "MODIFIER", count: variants.filter(v => v.impact === "MODIFIER" || !v.impact).length, color: "var(--text-3)" },
    ].map(d => ({ ...d, pct: Math.round((d.count / total) * 100) }));
  }, [variants]);

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Page header ─────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <p className="section-label">Variant Explorer</p>
          <h1 className="section-title" style={{ marginTop: 4 }}>All Variants</h1>
          <p className="section-sub">Filter, search, and click any row to open the full evidence card.</p>
        </div>
      </div>

      {/* ── Infographic stats row ─────────────────────── */}
      {!loading && variants.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr) 1fr", gap: 12, alignItems: "stretch" }}>
          {[
            { label: "Total Variants", value: variants.length, color: "var(--text)", sub: "loaded" },
            { label: "High Impact",    value: stats.high,      color: "var(--red)",   sub: "variants" },
            { label: "Moderate",       value: stats.moderate,  color: "var(--amber)", sub: "variants" },
            { label: "Pathogenic",     value: stats.path,      color: "var(--red)",   sub: "ACMG class" },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <p className="stat-label">{s.label}</p>
              <p className="stat-value" style={{ color: s.color, fontSize: 28 }}>{s.value}</p>
              <p style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{s.sub}</p>
            </div>
          ))}

          {/* Mini horizontal impact distribution bar */}
          <div className="stat-card" style={{ gridColumn: "5" }}>
            <p className="stat-label" style={{ marginBottom: 10 }}>Impact Distribution</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {impactDist.map(d => (
                <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: d.color, width: 44, flexShrink: 0 }}>{d.label}</span>
                  <div style={{ flex: 1, height: 5, background: "var(--bg-alt)", borderRadius: 99, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${d.pct}%`, background: d.color, borderRadius: 99 }} />
                  </div>
                  <span style={{ fontSize: 10, color: "var(--text-3)", width: 26, textAlign: "right" }}>{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Search & filter bar ───────────────────────── */}
      <div className="clinical-card">
        <div style={{ padding: "14px 18px", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && setAppliedSearch(search.trim())}
              placeholder="Search by gene symbol (e.g. BRCA1)…"
              className="input-field"
              style={{ paddingLeft: 32, fontSize: 13 }}
            />
          </div>
          <div style={{ position: "relative" }}>
            <Filter size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)", pointerEvents: "none" }} />
            <select value={impact} onChange={e => setImpact(e.target.value)} className="input-field" style={{ paddingLeft: 28, fontSize: 13, minWidth: 180, appearance: "none" as const }}>
              <option value="">All Impacts</option>
              <option value="HIGH">High Impact Only</option>
              <option value="MODERATE">Moderate & Above</option>
            </select>
          </div>
          <button onClick={() => setAppliedSearch(search.trim())} className="btn-primary" style={{ fontSize: 13, height: 38 }}>
            Apply
          </button>
          {(appliedSearch || impact) && (
            <button onClick={() => { setSearch(""); setImpact(""); setAppliedSearch(""); }} className="btn-secondary" style={{ fontSize: 12 }}>
              Clear
            </button>
          )}
          {!loading && (
            <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-3)", flexShrink: 0 }}>
              {variants.length} result{variants.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* ── Table ────────────────────────────────────── */}
      <div className="clinical-card" style={{ overflow: "hidden" }}>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "64px 24px", gap: 12 }}>
            <Loader2 size={24} className="animate-spin" style={{ color: "var(--blue)" }} />
            <p style={{ fontSize: 12, color: "var(--text-2)", letterSpacing: "0.05em" }}>Loading variants…</p>
          </div>
        ) : variants.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "64px 24px", gap: 14, textAlign: "center" }}>
            <div className="icon-box icon-box-error" style={{ width: 48, height: 48 }}><AlertCircle size={22} /></div>
            <div>
              <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", margin: 0 }}>No variants matched</p>
              <p style={{ fontSize: 13, color: "var(--text-2)", margin: "5px 0 0" }}>Adjust the filters or clear search to see all results.</p>
            </div>
            <button onClick={() => { setSearch(""); setImpact(""); setAppliedSearch(""); }} className="btn-secondary" style={{ fontSize: 12 }}>
              Clear Filters
            </button>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  {["Rank", "Gene", "Location", "Change", "Impact", "gnomAD AF", "ClinVar", "ACMG", "Score"].map(h => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {variants.map((v) => (
                  <tr
                    key={v.id}
                    onClick={() => router.push(`/jobs/${id}/variants/${v.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <div style={{
                        width: 28, height: 28, borderRadius: 7,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, fontWeight: 700, flexShrink: 0,
                        background: v.rank <= 3 ? "var(--blue)" : "var(--bg-alt)",
                        color: v.rank <= 3 ? "white" : "var(--text-2)",
                        border: v.rank <= 3 ? "none" : "1px solid var(--border)",
                      }}>
                        {v.rank}
                      </div>
                    </td>
                    <td style={{ fontWeight: 700, color: "var(--blue)" }}>{v.gene || "—"}</td>
                    <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-2)" }}>{v.chrom}:{v.pos?.toLocaleString()}</td>
                    <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                      <span style={{ color: "var(--text-2)" }}>{v.ref}</span>
                      <span style={{ color: "var(--text-3)", margin: "0 4px" }}>→</span>
                      <span style={{ color: "var(--text)" }}>{v.alt}</span>
                    </td>
                    <td>{v.impact ? <span className={getImpactBadgeClass(v.impact)}>{v.impact}</span> : <span style={{ color: "var(--text-3)" }}>—</span>}</td>
                    <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-2)" }}>
                      {v.gnomad_af != null ? Number(v.gnomad_af).toExponential(2) : <span style={{ color: "var(--text-3)" }}>Novel</span>}
                    </td>
                    <td>{v.clinvar_significance ? <span className={getClinVarBadgeClass(v.clinvar_significance)}>{v.clinvar_significance}</span> : <span style={{ color: "var(--text-3)" }}>—</span>}</td>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {v.acmg_class ? <span className={getAcmgBadgeClass(v.acmg_class)}>{v.acmg_class}</span> : <span style={{ color: "var(--text-3)" }}>—</span>}
                        {v.compound_het && <span style={{ fontSize: 10, color: "var(--purple)", fontWeight: 700 }}>Comp.Het</span>}
                      </div>
                    </td>
                    <td style={{ minWidth: 120 }}><ScoreBar score={v.rank_score || 0} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
