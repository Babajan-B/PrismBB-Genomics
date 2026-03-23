"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadVCF } from "@/lib/api";
import {
  UploadCloud, CheckCircle2, AlertCircle, Loader2,
  Database, ChevronRight, Search, FileText, Layers, Dna
} from "lucide-react";

const EXAMPLES = [
  { label: "Hereditary Breast Cancer", sub: "VCF · BRCA1/2 panel", gene: "BRCA1", hpo: "HP:0003002" },
  { label: "Epileptic Encephalopathy", sub: "VCF · SCN1A", gene: "SCN1A", hpo: "HP:0001250" },
  { label: "Cardiomyopathy Panel",     sub: "VCF · Multi-gene", gene: "MYBPC3", hpo: "HP:0001638" },
];

export default function HomePage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [genomeBuild, setGenomeBuild] = useState("GRCh38");
  const [hpoTerms, setHpoTerms] = useState("");
  const [geneList, setGeneList] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragOver(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) { setError("Please select a VCF file."); return; }
    setUploading(true); setError(null);
    try {
      const formData = new FormData();
      formData.append("vcf_file", file);
      formData.append("genome_build", genomeBuild);
      formData.append("hpo_terms", hpoTerms);
      formData.append("gene_list", geneList);
      const result = (await uploadVCF(formData)) as { job_id?: string; detail?: string };
      if (!result.job_id) { setError(result.detail || "Upload failed."); return; }
      router.push(`/jobs/${result.job_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div style={{ minHeight: "calc(100vh - 56px)", background: "var(--bg)" }}>
      
      {/* ── Franklin-style dark hero banner ─────────────────────── */}
      <div style={{
        background: "linear-gradient(160deg, #0D1B2A 0%, #101828 60%, #0E2340 100%)",
        padding: "56px 24px 80px",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Background subtle circles like Franklin */}
        <div style={{ position: "absolute", top: "-80px", right: "-80px", width: 400, height: 400, borderRadius: "50%", background: "rgba(46,144,250,0.06)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-40px", left: "10%", width: 300, height: 300, borderRadius: "50%", background: "rgba(127,86,217,0.05)", pointerEvents: "none" }} />

        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ maxWidth: 640 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "rgba(46,144,250,0.12)", border: "1px solid rgba(46,144,250,0.25)", borderRadius: 99, padding: "5px 12px", marginBottom: 20 }}>
              <Dna style={{ width: 13, height: 13, color: "#2E90FA" }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: "#2E90FA", letterSpacing: "0.06em" }}>NOW WITH ALPHAGENOME AI</span>
            </div>
            <h1 style={{ fontSize: 46, fontWeight: 800, color: "white", margin: 0, lineHeight: 1.1, letterSpacing: "-0.03em" }}>
              The Future of<br />
              <span style={{ color: "#2E90FA" }}>Genomic Medicine</span>
            </h1>
            <p style={{ fontSize: 16, color: "rgba(255,255,255,0.55)", marginTop: 16, maxWidth: 480, lineHeight: 1.65 }}>
              Interpret VCF files with deterministic clinical annotations from VEP, ClinVar, and gnomAD — grounded in evidence, powered by Gemini AI.
            </p>
          </div>

          {/* ── Example quick launch ── */}
          <div style={{ marginTop: 32, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", fontWeight: 500 }}>Try example:</span>
            {EXAMPLES.map(ex => (
              <button
                key={ex.label}
                onClick={() => { setGeneList(ex.gene); setHpoTerms(ex.hpo); }}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8, padding: "6px 12px", cursor: "pointer",
                  color: "rgba(255,255,255,0.75)", fontSize: 12, fontWeight: 600,
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.1)"; (e.currentTarget as HTMLElement).style.borderColor = "rgba(46,144,250,0.4)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.06)"; (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.1)"; }}
              >
                <FileText style={{ width: 11, height: 11 }} />
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Upload card overlapping hero ──────────────────────────── */}
      <div style={{ maxWidth: 1200, margin: "-32px auto 0", padding: "0 24px 48px", position: "relative", zIndex: 10 }}>
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          boxShadow: "0 4px 24px rgba(0,0,0,0.10)",
          overflow: "hidden",
        }}>
          {/* Card header */}
          <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border)", background: "#FCFCFD", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div className="icon-box icon-box-primary">
                <UploadCloud size={15} />
              </div>
              <div>
                <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", margin: 0 }}>Create New Case from VCF</h2>
                <p style={{ fontSize: 12, color: "var(--text-3)", margin: "2px 0 0" }}>Secure local analysis — no cloud file storage</p>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-3)" }}>REFERENCE</span>
                <div style={{ position: "relative" }}>
                  <select
                    value={genomeBuild}
                    onChange={e => setGenomeBuild(e.target.value)}
                    style={{
                      background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 7,
                      padding: "6px 28px 6px 10px", fontSize: 13, fontWeight: 600, color: "var(--text)",
                      cursor: "pointer", appearance: "none", outline: "none",
                    }}
                  >
                    <option value="GRCh38">hg38</option>
                    <option value="GRCh37">hg19</option>
                  </select>
                  <ChevronRight size={12} style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%) rotate(90deg)", pointerEvents: "none", color: "var(--text-3)" }} />
                </div>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", minHeight: 220 }}>
              
              {/* Left: drag & drop */}
              <div style={{ borderRight: "1px solid var(--border)", padding: 24 }}>
                <div
                  onDrop={handleDrop}
                  onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onClick={() => inputRef.current?.click()}
                  style={{
                    border: `2px dashed ${dragOver ? "var(--blue)" : "var(--border-strong)"}`,
                    borderRadius: 10,
                    background: dragOver ? "var(--blue-dim)" : "var(--surface-2)",
                    padding: "32px 24px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    transition: "all 0.15s",
                    textAlign: "center",
                    minHeight: 160,
                  }}
                >
                  <input ref={inputRef} type="file" accept=".vcf,.vcf.gz" style={{ display: "none" }} onChange={e => setFile(e.target.files?.[0] || null)} />
                  {file ? (
                    <>
                      <div className="icon-box icon-box-success" style={{ width: 48, height: 48, marginBottom: 12 }}>
                        <CheckCircle2 size={22} />
                      </div>
                      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", margin: 0 }}>{file.name}</p>
                      <p style={{ fontSize: 12, color: "var(--green)", margin: "5px 0 0", fontWeight: 600 }}>
                        {(file.size / 1024 / 1024).toFixed(2)} MB · Ready
                      </p>
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); setFile(null); }}
                        style={{ marginTop: 12, fontSize: 11, color: "var(--text-3)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
                      >
                        Change file
                      </button>
                    </>
                  ) : (
                    <>
                      <div style={{ width: 48, height: 48, borderRadius: 10, background: "var(--surface)", border: "1px solid var(--border-strong)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-3)", marginBottom: 12 }}>
                        <UploadCloud size={20} />
                      </div>
                      <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: 0 }}>Drop VCF file here</p>
                      <p style={{ fontSize: 12, color: "var(--text-3)", margin: "4px 0 12px" }}>or click to browse — .vcf, .vcf.gz</p>
                      <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 6, background: "var(--surface)", border: "1px solid var(--border-strong)", color: "var(--text-2)", fontWeight: 600, cursor: "pointer" }}>
                        Browse files
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Right: params */}
              <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em", display: "block", marginBottom: 6 }}>
                    Target Genes <span style={{ opacity: 0.5, fontWeight: 400 }}>(optional)</span>
                  </label>
                  <input
                    type="text" value={geneList} onChange={e => setGeneList(e.target.value)}
                    placeholder="e.g. BRCA1, TP53, MLL"
                    className="input-field"
                    style={{ fontSize: 13 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em", display: "block", marginBottom: 6 }}>
                    HPO Phenotypes <span style={{ opacity: 0.5, fontWeight: 400 }}>(optional)</span>
                  </label>
                  <input
                    type="text" value={hpoTerms} onChange={e => setHpoTerms(e.target.value)}
                    placeholder="e.g. HP:0001250"
                    className="input-field"
                    style={{ fontSize: 13 }}
                  />
                </div>

                {error && (
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--red-dim)", border: "1px solid var(--red-border)", borderRadius: 8, padding: "10px 12px" }}>
                    <AlertCircle size={14} style={{ color: "var(--red)", flexShrink: 0, marginTop: 1 }} />
                    <span style={{ fontSize: 12, color: "var(--red)", lineHeight: 1.5 }}>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!file || uploading}
                  className="btn-primary"
                  style={{ marginTop: "auto", justifyContent: "center", height: 40, fontSize: 13 }}
                >
                  {uploading ? (
                    <><Loader2 size={15} className="animate-spin" /> Analyzing…</>
                  ) : (
                    <><Search size={14} /> Interpret VCF</>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* ── Feature highlights (Franklin-style bottom row) ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginTop: 20 }}>
          {[
            { icon: <Database size={16} />, title: "Immutable Evidence", desc: "VEP · ClinVar · gnomAD · PanelApp — clinical-grade, deterministic annotations", color: "var(--blue)", dim: "var(--blue-dim)", border: "var(--blue-border)" },
            { icon: <Layers size={16} />, title: "6-Factor Ranking", desc: "Variants instantly prioritized by rarity, impact, phenotype match & clinical evidence", color: "var(--purple)", dim: "var(--purple-dim)", border: "var(--purple-border)" },
            { icon: <Search size={16} />, title: "AlphaGenome AI", desc: "DeepMind regulatory prediction for non-coding and splicing variant assessment", color: "var(--green)", dim: "var(--green-dim)", border: "var(--green-border)" },
          ].map(f => (
            <div key={f.title} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: "16px 18px", boxShadow: "0 1px 3px rgba(0,0,0,0.04)", display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{ width: 34, height: 34, borderRadius: 8, background: f.dim, border: `1px solid ${f.border}`, display: "flex", alignItems: "center", justifyContent: "center", color: f.color, flexShrink: 0 }}>{f.icon}</div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", margin: 0 }}>{f.title}</p>
                <p style={{ fontSize: 12, color: "var(--text-2)", margin: "4px 0 0", lineHeight: 1.55 }}>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
