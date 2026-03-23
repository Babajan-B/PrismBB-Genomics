"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getAuditLog } from "@/lib/api";
import {
  Loader2,
  CheckCircle2,
  ChevronLeft,
  ShieldCheck,
  Terminal,
  AlertCircle,
  ChevronRight,
  Activity,
  Clock,
} from "lucide-react";

interface AuditLog {
  id?: string;
  step?: string;
  level?: string;
  message?: string;
  details?: string;
  timestamp?: string;
  tool_version?: string;
}

export default function AuditPage() {
  const { id } = useParams<{ id: string }>();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAuditLog(id).then((d) => {
      setLogs((d as AuditLog[]) || []);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: 14 }}>
        <Loader2 style={{ width: 24, height: 24, color: "var(--text-2)" }} className="animate-spin" />
        <p style={{ fontSize: 11, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600 }}>Loading Audit Trail…</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 860, display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p className="section-label">Analysis Workspace</p>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
            <div className="icon-box icon-box-primary">
              <ShieldCheck style={{ width: 16, height: 16 }} />
            </div>
            <h1 className="section-title" style={{ fontSize: 22 }}>Audit Trail</h1>
          </div>
          <p className="section-sub" style={{ marginTop: 6 }}>Deterministic processing history and pipeline step assertions.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginTop: 4 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 6, background: "var(--green-dim)", border: "1px solid var(--green-border)" }}>
            <CheckCircle2 style={{ width: 13, height: 13, color: "var(--green)" }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--green)", letterSpacing: "0.05em", textTransform: "uppercase" }}>Verified Chain</span>
          </div>
          <Link href={`/jobs/${id}`} className="btn-secondary">
            <ChevronLeft style={{ width: 14, height: 14 }} />
            Back
          </Link>
        </div>
      </div>

      {/* Timeline */}
      <div className="clinical-card">
        <div className="clinical-card-header">
          <Activity style={{ width: 14, height: 14, color: "var(--blue)" }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", letterSpacing: "0.02em" }}>Pipeline Steps</span>
          <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-2)" }}>{logs.length} entries</span>
        </div>
        <div className="clinical-card-body" style={{ padding: "0" }}>
          {logs.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "48px 24px", gap: 12, textAlign: "center" }}>
              <div className="icon-box" style={{ width: 48, height: 48, borderRadius: 12 }}>
                <Activity style={{ width: 20, height: 20, color: "var(--text-3)" }} />
              </div>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: 0 }}>No Audit Logs</p>
              <p style={{ fontSize: 12, color: "var(--text-2)", margin: 0 }}>No processing logs available for this run.</p>
            </div>
          ) : (
            <div>
              {logs.map((log, idx) => {
                const isError = log.level === "ERROR";
                const date = log.timestamp ? new Date(log.timestamp) : null;

                return (
                  <div
                    key={log.id || idx}
                    style={{
                      display: "flex",
                      gap: 16,
                      padding: "16px 20px",
                      borderBottom: idx < logs.length - 1 ? "1px solid var(--border)" : "none",
                      background: isError ? "rgba(239,68,68,0.03)" : "transparent",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={e => { if (!isError) (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = isError ? "rgba(239,68,68,0.03)" : "transparent"; }}
                  >
                    {/* Step icon */}
                    <div
                      className={`icon-box ${isError ? "icon-box-error" : "icon-box-primary"}`}
                      style={{ marginTop: 2, flexShrink: 0 }}
                    >
                      {isError
                        ? <AlertCircle style={{ width: 14, height: 14 }} />
                        : <Activity style={{ width: 14, height: 14 }} />
                      }
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                        {log.step && (
                          <span style={{
                            fontSize: 10, fontWeight: 700, textTransform: "uppercase",
                            letterSpacing: "0.07em", padding: "1px 8px", borderRadius: 4,
                            background: isError ? "var(--red-dim)" : "var(--surface-2)",
                            color: isError ? "var(--red)" : "var(--text-2)",
                            border: `1px solid ${isError ? "var(--red-border)" : "var(--border)"}`,
                          }}>
                            {log.step}
                          </span>
                        )}
                        {date && (
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-3)" }}>
                            <Clock style={{ width: 10, height: 10 }} />
                            {date.toLocaleString()}
                          </span>
                        )}
                      </div>

                      <p style={{ fontSize: 13, color: isError ? "var(--red)" : "var(--text)", margin: 0, lineHeight: 1.5, fontWeight: 500 }}>
                        {log.message}
                      </p>

                      {log.details && (
                        <div style={{
                          marginTop: 10, padding: "10px 14px",
                          background: "var(--surface-2)", borderRadius: 7,
                          border: "1px solid var(--border)",
                        }}>
                          <pre style={{ fontSize: 11, fontFamily: "monospace", color: "var(--blue)", margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-all", lineHeight: 1.6 }}>
                            {String(log.details)}
                          </pre>
                        </div>
                      )}

                      {log.tool_version && (
                        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, marginTop: 8, fontSize: 10, color: "var(--text-3)", fontFamily: "monospace", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          <Terminal style={{ width: 11, height: 11 }} />
                          {log.tool_version}
                        </div>
                      )}
                    </div>

                    {/* Right chevron */}
                    <div style={{ flexShrink: 0, display: "flex", alignItems: "flex-start", paddingTop: 6 }}>
                      <ChevronRight style={{ width: 13, height: 13, color: "var(--text-3)" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
