"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getJobs } from "@/lib/api";
import {
  Activity,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Dna,
  FileText,
  Loader2,
  XCircle,
  BarChart3,
  Cpu,
  Plus,
} from "lucide-react";

interface JobSummary {
  id: string;
  status: string;
  filename: string;
  genome_build: string;
  variant_count: number;
  sample_count: number;
  created_at: string;
  hpo_terms?: string[];
}

const FILTERS = [
  { id: "all",       label: "All Runs" },
  { id: "completed", label: "Completed" },
  { id: "processing",label: "Running" },
  { id: "failed",    label: "Failed" },
];

function getStatusConfig(status: string) {
  if (status === "completed")
    return { color: "var(--green)", bar: "var(--green)", label: "Completed", icon: <CheckCircle2 style={{ width: 12, height: 12 }} /> };
  if (status === "failed")
    return { color: "var(--red)", bar: "var(--red)", label: "Failed", icon: <XCircle style={{ width: 12, height: 12 }} /> };
  return { color: "var(--blue)", bar: "var(--blue)", label: "Running", icon: <Loader2 style={{ width: 12, height: 12, animation: "spin 0.8s linear infinite" }} /> };
}

export default function HistoryPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let mounted = true;
    async function loadJobs() {
      const data = (await getJobs()) as { jobs?: JobSummary[] };
      if (!mounted) return;
      setJobs(data.jobs || []);
      setLoading(false);
    }
    void loadJobs();
    return () => { mounted = false; };
  }, []);

  const filteredJobs = jobs.filter((job) => {
    if (filter === "all") return true;
    if (filter === "processing") return !["completed", "failed"].includes(job.status);
    return job.status === filter;
  });

  const completed   = jobs.filter(j => j.status === "completed").length;
  const failed      = jobs.filter(j => j.status === "failed").length;
  const processing  = jobs.filter(j => !["completed", "failed"].includes(j.status)).length;

  if (loading) {
    return (
      <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: 14 }}>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", inset: -8, borderRadius: "50%", background: "var(--blue-dim)", filter: "blur(12px)" }} />
          <Loader2 style={{ width: 28, height: 28, color: "var(--blue)", position: "relative" }} className="animate-spin" />
        </div>
        <p style={{ fontSize: 12, color: "var(--text-3)", letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600 }}>Loading run history…</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: 28 }}>

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p className="section-label">Analysis Workspace</p>
          <h1 className="section-title" style={{ fontSize: 26, marginTop: 4 }}>Run History</h1>
          <p className="section-sub" style={{ marginTop: 4 }}>Review uploads, track progress, and open any workspace.</p>
        </div>
        <Link href="/" className="btn-primary" style={{ marginTop: 4, gap: 8, fontSize: 13 }}>
          <Plus style={{ width: 14, height: 14 }} />
          New Analysis
        </Link>
      </div>

      {/* ── Stats row ──────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard label="Total Runs"   value={jobs.length}  color="var(--text)"  icon={<BarChart3 style={{ width: 16, height: 16 }} />} />
        <StatCard label="Completed"    value={completed}    color="var(--green)" icon={<CheckCircle2 style={{ width: 16, height: 16 }} />} />
        <StatCard label="Processing"   value={processing}   color="var(--blue)"  icon={<Cpu style={{ width: 16, height: 16 }} />} />
        <StatCard label="Failed"       value={failed}       color="var(--red)"   icon={<XCircle style={{ width: 16, height: 16 }} />} />
      </div>

      {/* ── Filter tabs ────────────────────────────────────────────── */}
      <div className="filter-tabs">
        {FILTERS.map(item => (
          <button
            key={item.id}
            onClick={() => setFilter(item.id)}
            className={`filter-tab ${filter === item.id ? "active" : ""}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* ── Job list ───────────────────────────────────────────────── */}
      <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden", background: "var(--surface)" }}>
        {filteredJobs.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "64px 24px", gap: 14, textAlign: "center" }}>
            <div style={{ width: 56, height: 56, borderRadius: 14, background: "var(--surface-2)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Dna style={{ width: 24, height: 24, color: "var(--text-3)" }} />
            </div>
            <div>
              <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", margin: 0 }}>No runs match this filter</p>
              <p style={{ fontSize: 13, color: "var(--text-2)", margin: "6px 0 0" }}>
                {filter === "all"
                  ? "Start a new upload to populate the workspace."
                  : `No ${filter} jobs in the current view.`}
              </p>
            </div>
            <Link href="/" className="btn-primary" style={{ marginTop: 4, fontSize: 13 }}>
              <Plus style={{ width: 14, height: 14 }} />
              Start New Analysis
            </Link>
          </div>
        ) : (
          <div>
            {filteredJobs.map((job, idx) => {
              const cfg = getStatusConfig(job.status);
              const createdAt = new Date(job.created_at);
              const isProcessing = !["completed", "failed"].includes(job.status);

              return (
                <Link
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="job-card"
                  style={{ color: "inherit" }}
                >
                  {/* Colored left bar */}
                  <div className="job-card-status-bar" style={{ background: cfg.bar }} />

                  {/* Icon box */}
                  <div style={{
                    width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                    background: job.status === "completed" ? "var(--green-dim)" : job.status === "failed" ? "var(--red-dim)" : "var(--blue-dim)",
                    border: `1px solid ${job.status === "completed" ? "var(--green-border)" : job.status === "failed" ? "var(--red-border)" : "var(--blue-border)"}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: cfg.color,
                  }}>
                    <FileText style={{ width: 17, height: 17 }} />
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {job.filename || "Unnamed analysis"}
                    </p>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4, flexWrap: "wrap" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-3)" }}>
                        <Calendar style={{ width: 10, height: 10 }} />
                        {createdAt.toLocaleDateString()} {createdAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "monospace", letterSpacing: "0.03em" }}>
                        {job.id.slice(0, 8)}
                      </span>
                      <span style={{
                        fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em",
                        padding: "1px 6px", borderRadius: 4,
                        background: "var(--surface-2)", color: "var(--text-2)", border: "1px solid var(--border)"
                      }}>
                        {job.genome_build}
                      </span>
                    </div>
                    {job.hpo_terms && job.hpo_terms.length > 0 && (
                      <p style={{ marginTop: 3, fontSize: 11, color: "var(--text-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        HPO: {job.hpo_terms.join(", ")}
                      </p>
                    )}
                  </div>

                  {/* Right: stats + status */}
                  <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
                    <div style={{ textAlign: "right" }}>
                      <p style={{ fontSize: 10, color: "var(--text-3)", margin: 0, textTransform: "uppercase", letterSpacing: "0.06em" }}>Variants</p>
                      <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", margin: "2px 0 0" }}>
                        {job.variant_count != null ? job.variant_count.toLocaleString() : "—"}
                      </p>
                    </div>
                    <div style={{
                      display: "inline-flex", alignItems: "center", gap: 5,
                      padding: "4px 10px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                      letterSpacing: "0.05em",
                      background: job.status === "completed" ? "var(--green-dim)" : job.status === "failed" ? "var(--red-dim)" : "var(--blue-dim)",
                      border: `1px solid ${job.status === "completed" ? "var(--green-border)" : job.status === "failed" ? "var(--red-border)" : "var(--blue-border)"}`,
                      color: cfg.color,
                    }}>
                      {cfg.icon}
                      {cfg.label}
                    </div>
                    <ChevronRight style={{ width: 14, height: 14, color: "var(--text-3)" }} />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color, icon }: { label: string; value: number; color: string; icon: React.ReactNode }) {
  return (
    <div className="stat-card">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <p className="stat-label">{label}</p>
        <div style={{ color: color === "var(--text)" ? "var(--text-3)" : color, opacity: 0.7 }}>{icon}</div>
      </div>
      <p className="stat-value" style={{ color }}>{value}</p>
    </div>
  );
}
