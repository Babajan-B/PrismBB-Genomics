"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Dna, History, Upload, LayoutDashboard, Layers, Trophy,
  MessageSquare, FileDown, ShieldCheck, ChevronRight, Home,
  ArrowLeft, Search,
} from "lucide-react";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/";
  const jobId = pathname.startsWith("/jobs/") ? pathname.split("/")[2] : null;

  const isActive = (path: string) =>
    path === "/jobs" ? false :
    pathname === path || (path !== "/" && pathname.startsWith(`${path}/`));

  /* ── top-level nav links */
  const topNav = [
    { href: "/",        label: "SEARCH",   icon: <Search className="h-3.5 w-3.5" /> },
    { href: "/history", label: "MY CASES", icon: <History className="h-3.5 w-3.5" /> },
  ];

  /* ── job workspace sidebar items */
  const jobNav = jobId ? [
    { href: `/jobs/${jobId}`,          label: "Overview",    icon: <LayoutDashboard size={14} />, exact: true },
    { href: `/jobs/${jobId}/variants`, label: "Variants",    icon: <Layers size={14} /> },
    { href: `/jobs/${jobId}/ranking`,  label: "Priority",    icon: <Trophy size={14} /> },
    { href: `/jobs/${jobId}/chat`,     label: "AI Copilot",  icon: <MessageSquare size={14} /> },
    { href: `/jobs/${jobId}/report`,   label: "Reports",     icon: <FileDown size={14} /> },
    { href: `/jobs/${jobId}/audit`,    label: "Audit",       icon: <ShieldCheck size={14} /> },
  ] : [];

  /* ─── Shared Franklin top navigation bar ────────────────────── */
  const FranklinNav = ({ showWorkspaceLinks = false }: { showWorkspaceLinks?: boolean }) => (
    <nav className="franklin-nav">
      {/* Logo */}
      <Link href="/" className="franklin-nav-logo">
        <div className="franklin-nav-logo-icon">P</div>
        <div className="franklin-nav-wordmark">
          <span className="franklin-nav-title">PrismBB</span>
          <span className="franklin-nav-sub">by Genomics</span>
        </div>
      </Link>

      {/* Main nav links */}
      <div className="franklin-nav-links">
        {topNav.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={`franklin-nav-link ${isActive(item.href) || (item.href === "/" && isLanding) ? "active" : ""}`}
          >
            {item.icon}
            {item.label}
          </Link>
        ))}
        {showWorkspaceLinks && jobId && (
          <>
            <div style={{ width: 1, background: "rgba(255,255,255,0.08)", margin: "14px 8px" }} />
            {jobNav.map(item => {
              const active = item.exact ? pathname === item.href : isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`franklin-nav-link ${active ? "active" : ""}`}
                  style={{ fontSize: 12 }}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </>
        )}
      </div>

      {/* Right side */}
      <div className="franklin-nav-right">
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 99, background: "rgba(18,183,106,0.12)", border: "1px solid rgba(18,183,106,0.25)" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#12B76A", display: "inline-block" }} />
          <span style={{ fontSize: 10, fontWeight: 700, color: "#12B76A", letterSpacing: "0.06em" }}>LIVE</span>
        </div>
        <div className="nav-avatar">P</div>
      </div>
    </nav>
  );

  /* ─── Landing page ─────────────────────────────────── */
  if (isLanding) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
        <FranklinNav />
        <main className="min-w-0 w-full">{children}</main>
      </div>
    );
  }

  /* ─── Job workspace: nav + horizontal layout ──────── */
  if (jobId) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
        <FranklinNav showWorkspaceLinks={true} />
        {/* Secondary breadcrumb bar */}
        <div style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          height: 40,
          gap: 6,
          fontSize: 12,
          color: "var(--text-2)",
        }}>
          <Link href="/" style={{ color: "var(--text-3)", display: "flex", alignItems: "center", gap: 4 }}>
            <Home size={11} /> Home
          </Link>
          <ChevronRight size={10} style={{ opacity: 0.4 }} />
          <Link href="/history" style={{ color: "var(--text-3)" }}>Cases</Link>
          <ChevronRight size={10} style={{ opacity: 0.4 }} />
          <span style={{ color: "var(--blue)", fontWeight: 600 }}>{jobId.slice(0, 8)}…</span>
          <ChevronRight size={10} style={{ opacity: 0.4 }} />
          <span style={{ color: "var(--text)", fontWeight: 600 }}>
            {(() => {
              const seg = pathname.split("/").filter(Boolean);
              const last = seg[seg.length - 1];
              if (last === jobId) return "Overview";
              return last.charAt(0).toUpperCase() + last.slice(1);
            })()}
          </span>
        </div>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 24px 72px" }} className="animate-fade-in">
          {children}
        </div>
      </div>
    );
  }

  /* ─── Other pages (history, etc) ─────────────────── */
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <FranklinNav />
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px 72px" }} className="animate-fade-in">
        {children}
      </div>
    </div>
  );
}
