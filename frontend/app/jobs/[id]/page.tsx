"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getJobStatus } from "@/lib/api";
import {
  AlertCircle, ArrowLeft, CheckCircle2, ChevronRight,
  Database, FileDown, Layers, Loader2, MessageSquare,
  RefreshCw, ShieldCheck, Trophy, Dna, Calendar, Cpu, FlaskConical,
} from "lucide-react";

interface JobDetail {
  id: string; status: string; filename: string; genome_build: string;
  sample_count: number; variant_count: number; hpo_terms?: string[];
  qc_summary?: Record<string, unknown>; error_message?: string | null;
  pipeline_version?: string; created_at?: string; updated_at?: string;
}

const STEPS = [
  { key: "ingesting",     label: "Validate" },
  { key: "preprocessing", label: "Normalize" },
  { key: "annotating",    label: "Annotate" },
  { key: "ranking",       label: "Rank" },
  { key: "completed",     label: "Done" },
];

function getStepState(status: string, stepKey: string) {
  if (status === "failed") return "pending";
  const activeIdx = STEPS.findIndex(s => s.key === status);
  const stepIdx   = STEPS.findIndex(s => s.key === stepKey);
  if (activeIdx === -1) return stepIdx === 0 ? "active" : "pending";
  if (stepIdx < activeIdx) return "done";
  if (stepIdx === activeIdx) return status === "completed" ? "done" : "active";
  return "pending";
}

const WORKSPACE = [
  { href: "variants", label: "Variant Explorer",  sub: "Browse and filter all annotated candidates", icon: <Layers size={18} />, color: "#3b82f6", dim: "rgba(59,130,246,0.08)", border: "rgba(59,130,246,0.20)", primary: true },
  { href: "ranking",  label: "Priority Ranking",  sub: "Top-scored candidates with factor breakdown",icon: <Trophy size={18} />, color: "#f59e0b", dim: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.20)", primary: true },
  { href: "chat",     label: "Gemini Chat",        sub: "Ask grounded questions about this run",      icon: <MessageSquare size={18} />, color: "#8b5cf6", dim: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.20)", primary: true },
  { href: "report",   label: "Export Reports",     sub: "CSV · Excel · JSON downloads",               icon: <FileDown size={18} />, color: "#10b981", dim: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.18)", primary: false },
  { href: "audit",    label: "Audit Trail",        sub: "Processing history & tool versions",          icon: <ShieldCheck size={18} />, color: "#6b7280", dim: "rgba(107,114,128,0.06)", border: "rgba(107,114,128,0.16)", primary: false },
];

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false; let tid: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const data = (await getJobStatus(id)) as JobDetail | null;
        if (cancelled) return;
        setJob(data); setLoading(false);
        if (data && !["completed", "failed"].includes(data.status)) tid = setTimeout(poll, 3000);
      } catch { if (!cancelled) setLoading(false); }
    }
    void poll();
    return () => { cancelled = true; if (tid) clearTimeout(tid); };
  }, [id]);

  const qc = useMemo(() => job?.qc_summary || {}, [job?.qc_summary]);

  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "50vh", gap: 12 }} className="animate-fade-in">
      <Loader2 style={{ width: 24, height: 24, color: "var(--blue)" }} className="animate-spin" />
      <p style={{ fontSize: 12, color: "var(--text-2)", letterSpacing: "0.05em" }}>Loading workspace…</p>
    </div>
  );

  if (!job) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "50vh", gap: 16, textAlign: "center" }} className="animate-fade-in">
      <div className="icon-box icon-box-error" style={{ width: 44, height: 44 }}>
        <AlertCircle size={20} />
      </div>
      <div>
        <p style={{ fontSize: 16, fontWeight: 700, color: "var(--text)", margin: 0 }}>Analysis not found</p>
        <p style={{ fontSize: 13, color: "var(--text-2)", marginTop: 4 }}>This job may have been removed or the ID is invalid.</p>
      </div>
      <Link href="/history" className="btn-secondary">
        <ArrowLeft size={13} /> Return to History
      </Link>
    </div>
  );

  const isComplete = job.status === "completed";
  const isFailed   = job.status === "failed";
  const isRunning  = !isComplete && !isFailed;
  const createdAt  = job.created_at ? new Date(job.created_at) : null;
  const primary    = WORKSPACE.filter(w => w.primary);
  const secondary  = WORKSPACE.filter(w => !w.primary);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 960 }} className="animate-fade-in">

      {/* ── Job header ──────────────────────────────── */}
      <div className="clinical-card">
        <div className="clinical-card-header">
          <div className="icon-box icon-box-primary">
            <Dna size={15} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: 10, fontFamily: "monospace", color: "var(--text-2)", margin: 0, letterSpacing: "0.04em" }}>{id.slice(0,8)}…</p>
            <h1 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {job.filename}
            </h1>
          </div>
          {/* Status pill */}
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "5px 12px", borderRadius: 99, fontSize: 11, fontWeight: 700,
            letterSpacing: "0.05em", textTransform: "uppercase", flexShrink: 0,
            background: isComplete ? "var(--green-dim)" : isFailed ? "var(--red-dim)" : "var(--blue-dim)",
            border: `1px solid ${isComplete ? "var(--green-border)" : isFailed ? "var(--red-border)" : "var(--blue-border)"}`,
            color: isComplete ? "var(--green)" : isFailed ? "var(--red)" : "var(--blue)",
          }}>
            {isComplete ? <CheckCircle2 size={12} /> : isFailed ? <AlertCircle size={12} /> : <Loader2 size={12} className="animate-spin" />}
            {isComplete ? "Completed" : isFailed ? "Failed" : "Processing"}
          </div>
        </div>

        <div className="clinical-card-body" style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
          {[
            { label: "Genome Build", value: job.genome_build },
            { label: "Samples",      value: String(job.sample_count || "—") },
            { label: "Variants",     value: job.variant_count != null ? job.variant_count.toLocaleString() : "—" },
            { label: "Pipeline",     value: job.pipeline_version || "1.0.0" },
            ...(createdAt ? [{ label: "Submitted", value: createdAt.toLocaleDateString() + " " + createdAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }] : []),
          ].map(m => (
            <div key={m.label}>
              <p style={{ fontSize: 10, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 2px", fontWeight: 700 }}>{m.label}</p>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: 0 }}>{m.value}</p>
            </div>
          ))}
          {job.hpo_terms && job.hpo_terms.length > 0 && (
            <div>
              <p style={{ fontSize: 10, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 2px", fontWeight: 700 }}>HPO Terms</p>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--blue)", margin: 0 }}>{job.hpo_terms.join(", ")}</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Pipeline progress ───────────────────────── */}
      <div className="clinical-card">
        <div className="clinical-card-header">
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.07em", margin: 0 }}>Pipeline Progress</p>
        </div>
        <div className="clinical-card-body">
          <div style={{ display: "flex", alignItems: "center" }}>
            {STEPS.map((step, i) => {
              const state    = getStepState(job.status, step.key);
              const isDone   = state === "done";
              const isActive = state === "active";
              return (
                <div key={step.key} style={{ display: "flex", alignItems: "center", flex: i < STEPS.length - 1 ? "1" : undefined }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                    <div style={{
                      width: 30, height: 30, borderRadius: 99,
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                      background: isDone ? "var(--green-dim)" : isActive ? "var(--blue-dim)" : "var(--surface-2)",
                      border: `1px solid ${isDone ? "var(--green-border)" : isActive ? "var(--blue-border)" : "var(--border)"}`,
                      color: isDone ? "var(--green)" : isActive ? "var(--blue)" : "var(--text-2)",
                    }}>
                      {isDone ? <CheckCircle2 size={14} /> : isActive ? <Loader2 size={14} className="animate-spin" /> : <span style={{ fontSize: 10, fontWeight: 700 }}>{i + 1}</span>}
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 600, color: isDone ? "var(--text)" : isActive ? "var(--blue)" : "var(--text-2)", whiteSpace: "nowrap" }}>{step.label}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className="pipeline-connector" style={{ background: isDone ? "var(--green-border)" : "var(--border)" }} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── COMPLETED workspace ─────────────────────── */}
      {isComplete && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)" }} />
            <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", margin: 0 }}>Interpretation Workspace</p>
            <span style={{ fontSize: 11, color: "var(--text-2)" }}>— all tools ready</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, marginBottom: 10 }}>
            {primary.map(tile => (
              <Link key={tile.href} href={`/jobs/${id}/${tile.href}`} className="workspace-tile"
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = tile.border; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; }}>
                <div style={{ width: 36, height: 36, borderRadius: 9, background: tile.dim, border: `1px solid ${tile.border}`, display: "flex", alignItems: "center", justifyContent: "center", color: tile.color }}>
                  {tile.icon}
                </div>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", margin: 0 }}>{tile.label}</p>
                  <p style={{ fontSize: 11, color: "var(--text-2)", margin: "3px 0 0", lineHeight: 1.4 }}>{tile.sub}</p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: tile.color, marginTop: "auto" }}>
                  Open <ChevronRight size={11} />
                </div>
              </Link>
            ))}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
            {secondary.map(tile => (
              <Link key={tile.href} href={`/jobs/${id}/${tile.href}`}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 9, background: "var(--surface)", border: "1px solid var(--border)", textDecoration: "none", transition: "all 0.12s" }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = tile.border; (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.background = "var(--surface)"; }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: tile.dim, border: `1px solid ${tile.border}`, display: "flex", alignItems: "center", justifyContent: "center", color: tile.color, flexShrink: 0 }}>{tile.icon}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", margin: 0 }}>{tile.label}</p>
                  <p style={{ fontSize: 11, color: "var(--text-2)", margin: "1px 0 0" }}>{tile.sub}</p>
                </div>
                <ChevronRight size={13} style={{ color: "var(--text-2)", flexShrink: 0 }} />
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── RUNNING ──────────────────────────────────── */}
      {isRunning && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--blue-border)", borderRadius: 10, padding: "32px 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: 10, textAlign: "center" }}>
          <Loader2 style={{ width: 22, height: 22, color: "var(--blue)" }} className="animate-spin" />
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: 0 }}>Pipeline running…</p>
          <p style={{ fontSize: 13, color: "var(--text-2)", margin: 0, maxWidth: 380, lineHeight: 1.6 }}>The workspace unlocks automatically when annotation and ranking complete. Polling every 3 s.</p>
        </div>
      )}

      {/* ── FAILED ───────────────────────────────────── */}
      {isFailed && (
        <div style={{ background: "var(--red-dim)", border: "1px solid var(--red-border)", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", gap: 12 }}>
            <div className="icon-box icon-box-error" style={{ marginTop: 1 }}><AlertCircle size={15} /></div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", margin: 0 }}>Pipeline failed</p>
              <p style={{ fontSize: 13, color: "var(--text-2)", margin: "5px 0 12px", lineHeight: 1.6 }}>{job.error_message || "The pipeline reported an error without additional context."}</p>
              <button onClick={() => window.location.reload()} className="btn-secondary" style={{ fontSize: 12, gap: 5 }}>
                <RefreshCw size={12} /> Refresh
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Details collapsible ──────────────────────── */}
      <details style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10 }}>
        <summary style={{ padding: "12px 18px", fontSize: 12, fontWeight: 600, color: "var(--text-2)", cursor: "pointer", listStyle: "none", display: "flex", alignItems: "center", gap: 7, userSelect: "none" }}>
          <Database size={12} /> Run details &amp; QC
          <ChevronRight size={11} style={{ marginLeft: "auto" }} />
        </summary>
        <div style={{ borderTop: "1px solid var(--border)", padding: "16px 18px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 8 }}>
          {[
            { label: "Job ID", value: job.id }, { label: "Genome", value: job.genome_build },
            { label: "Samples", value: String(job.sample_count || "—") }, { label: "Variants", value: job.variant_count?.toLocaleString() || "—" },
            { label: "Pipeline", value: job.pipeline_version || "1.0.0" }, { label: "Error", value: job.error_message || "None" },
          ].map(row => (
            <div key={row.label} style={{ padding: "9px 12px", background: "var(--surface-2)", borderRadius: 7, border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 9, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 2px", fontWeight: 700 }}>{row.label}</p>
              <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", margin: 0, fontFamily: ["Job ID","Pipeline"].includes(row.label) ? "monospace" : undefined, wordBreak: "break-all" }}>{row.value}</p>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
