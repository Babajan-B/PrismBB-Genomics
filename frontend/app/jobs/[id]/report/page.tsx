"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { getReportUrl } from "@/lib/api";
import {
  FileSpreadsheet,
  FileJson,
  FileText,
  ChevronLeft,
  Download,
  CheckCircle2,
  Lock,
  FileDown,
} from "lucide-react";

const FORMATS = [
  {
    id: "csv",
    label: "Clinical CSV",
    icon: FileSpreadsheet,
    desc: "Flat comma-separated table with top 100 variants for quick downstream processing.",
    color: "var(--green)",
    dim: "var(--green-dim)",
    border: "var(--green-border)",
  },
  {
    id: "excel",
    label: "Excel Workbook",
    icon: FileText,
    desc: "Multi-sheet structured workbook with QC data, variants, and job metadata.",
    color: "var(--blue)",
    dim: "var(--blue-dim)",
    border: "var(--blue-border)",
  },
  {
    id: "json",
    label: "JSON Export",
    icon: FileJson,
    desc: "Complete raw JSON dataset with all nested annotations for API or programmatic integration.",
    color: "var(--amber)",
    dim: "var(--amber-dim)",
    border: "rgba(245,158,11,0.22)",
  },
];

const INCLUSIONS = [
  "Ranked variant list with scores",
  "ClinVar annotations & significance",
  "gnomAD population frequencies",
  "VEP consequence predictions",
  "PanelApp disease associations",
  "HPO phenotype matching results",
  "Quality control ingestion metrics",
  "Pipeline deterministic audit trail",
];

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="animate-fade-in" style={{ maxWidth: 900, display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p className="section-label">Analysis Workspace</p>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
            <div className="icon-box icon-box-primary">
              <FileDown style={{ width: 16, height: 16 }} />
            </div>
            <h1 className="section-title" style={{ fontSize: 22 }}>Export Reports</h1>
          </div>
          <p className="section-sub" style={{ marginTop: 6 }}>
            Download precision analysis results in standardized formats for clinical review.
          </p>
        </div>
        <Link href={`/jobs/${id}`} className="btn-secondary" style={{ marginTop: 4 }}>
          <ChevronLeft style={{ width: 14, height: 14 }} />
          Back to Overview
        </Link>
      </div>

      {/* Format Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        {FORMATS.map((f) => {
          const Icon = f.icon;
          return (
            <a
              key={f.id}
              href={getReportUrl(id, f.id as "json" | "csv" | "excel")}
              download
              className="clinical-card"
              style={{ textDecoration: "none", display: "flex", flexDirection: "column", overflow: "hidden", transition: "border-color 0.2s" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = f.border; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; }}
            >
              <div className="clinical-card-header" style={{ gap: 10 }}>
                <div className="icon-box" style={{ background: f.dim, color: f.color, border: `1px solid ${f.border}` }}>
                  <Icon style={{ width: 15, height: 15 }} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>{f.label}</span>
              </div>
              <div className="clinical-card-body" style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
                <p style={{ fontSize: 12, color: "var(--text-2)", margin: 0, lineHeight: 1.55 }}>{f.desc}</p>
                <div style={{
                  display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 7,
                  padding: "8px 14px", borderRadius: 7, marginTop: "auto",
                  background: f.dim, border: `1px solid ${f.border}`,
                  color: f.color, fontSize: 12, fontWeight: 700, letterSpacing: "0.04em",
                  textTransform: "uppercase",
                }}>
                  <Download style={{ width: 13, height: 13 }} />
                  Download
                </div>
              </div>
            </a>
          );
        })}
      </div>

      {/* Lower section */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 14 }}>

        {/* Security note */}
        <div className="clinical-card" style={{ overflow: "hidden" }}>
          <div className="clinical-card-header">
            <div className="icon-box icon-box-primary">
              <Lock style={{ width: 14, height: 14 }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>Secure Export</span>
          </div>
          <div className="clinical-card-body">
            <p style={{ fontSize: 12, color: "var(--text-2)", margin: 0, lineHeight: 1.6 }}>
              Reports are generated on-demand from the PostgreSQL datastore. Data remains local — download streams are processed directly within this environment.
            </p>
          </div>
        </div>

        {/* Inclusions */}
        <div className="clinical-card">
          <div className="clinical-card-header">
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>Standard Output Inclusions</span>
          </div>
          <div className="clinical-card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 24px" }}>
              {INCLUSIONS.map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <CheckCircle2 style={{ width: 12, height: 12, color: "var(--green)", flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: "var(--text-2)", fontWeight: 500 }}>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
