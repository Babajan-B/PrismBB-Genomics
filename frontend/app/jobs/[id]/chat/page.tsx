"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { sendChat } from "@/lib/api";
import { 
  Send, 
  Loader2, 
  Bot, 
  User, 
  ExternalLink, 
  ChevronLeft, 
  Sparkles, 
  Terminal,
  ChevronRight
} from "lucide-react";

interface Message { 
  role: "user" | "assistant"; 
  content: string; 
  sources?: unknown[]; 
  toolCalls?: unknown[]; 
}

const SUGGESTIONS = [
  "Why is the top ranked variant prioritized?",
  "What is the ClinVar significance of the most damaging candidate?",
  "Compare the clinical evidence for the top 3 candidates",
  "Draft a clinical report summary for the primary variant",
];

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hello! I'm Gemini Chat for this workspace, running on Gemini 2.5 Flash. I can review variants, read evidence cards, perform NCBI and OMIM lookups on your behalf.\n\nHow can I help you interpret these findings?`,
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send(text?: string) {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    const userMsg: Message = { role: "user", content: msg };
    const history = messages.slice(1);
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    
    try {
      const geminiHistory = history.map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [m.content],
      }));
      const result = await sendChat({ message: msg, job_id: id, history: geminiHistory }) as { 
        response?: string; 
        evidence_sources?: unknown[]; 
        tool_calls?: unknown[]; 
      };
      
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.response || "No response",
        sources: result.evidence_sources,
        toolCalls: result.tool_calls,
      }]);
    } catch {
      setMessages((prev) => [...prev, { 
        role: "assistant", 
        content: "Sorry, I encountered an error communicating with the agent. Please try again or check the backend console." 
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-160px)] flex flex-col animate-fade-in relative z-10">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8 pb-6 border-b border-[var(--line)]">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-[var(--text-secondary)] mb-4">
            <Link href={`/jobs/${id}`} className="hover:text-[var(--accent)] transition-colors">
              Analysis Workspace
            </Link>
            <ChevronRight className="h-4 w-4 opacity-50" />
            <span className="text-white bg-[var(--surface-muted)] px-3 py-1 rounded-lg border border-[var(--line)]">Gemini Chat</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#818CF8] to-[#C084FC] flex items-center justify-center shadow-[0_0_20px_rgba(192,132,252,0.4)] border border-[rgba(255,255,255,0.2)]">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-white tracking-tight">Gemini Chat</h1>
              <p className="text-sm leading-relaxed text-[var(--text-secondary)] mt-1">Chat directly with the data and external knowledge bases.</p>
            </div>
          </div>
        </div>
        
        <Link href={`/jobs/${id}`} className="btn-secondary flex items-center gap-2 shadow-inner">
          <ChevronLeft className="w-4 h-4" />
          Back to Overview
        </Link>
      </div>

      {/* Chat Container */}
      <div className="flex-1 glass-card flex flex-col overflow-hidden relative shadow-[0_15px_40px_-10px_rgba(0,0,0,0.8)]">
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-8 scroll-smooth">
          {messages.map((msg, i) => (
            <div 
              key={i} 
              className={`flex gap-5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              {/* Avatar */}
              <div className={`
                w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border
                ${msg.role === "assistant" 
                  ? "bg-gradient-to-br from-[#818CF8] to-[#C084FC] border-[#C084FC]/50 shadow-[0_0_15px_rgba(192,132,252,0.3)] text-white" 
                  : "bg-[var(--surface-solid)] border-[var(--line)] text-[var(--text-muted)] shadow-inner"
                }
              `}>
                {msg.role === "assistant" ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
              </div>

              {/* Message Content */}
              <div className={`flex-1 max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col space-y-3`}>
                <div className={`
                  px-6 py-4 rounded-2xl text-sm leading-8 shadow-md border
                  ${msg.role === "user"
                    ? "bg-[var(--accent-soft)] border-[var(--accent-soft)] text-white rounded-tr-none shadow-[0_4px_15px_rgba(56,189,248,0.1)]"
                    : "bg-[var(--surface-muted)] border-[var(--line)] text-[var(--text-primary)] rounded-tl-none"
                  }
                `}>
                  {msg.content}
                </div>

                {/* Agent Tool Execution Badges */}
                {msg.toolCalls && (msg.toolCalls as unknown[]).length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {(msg.toolCalls as Record<string, string>[]).map((tc, ti) => (
                      <span 
                        key={ti} 
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-[rgba(16,185,129,0.1)] text-[var(--success)] rounded-lg text-[11px] font-bold tracking-wider border border-[rgba(16,185,129,0.2)] shadow-inner uppercase"
                      >
                        <Terminal className="w-3.5 h-3.5" /> 
                        Executed {tc.tool}
                      </span>
                    ))}
                  </div>
                )}

                {/* Evidence Sources */}
                {msg.sources && (msg.sources as unknown[]).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-l-2 border-[var(--line)] pl-3 ml-2">
                    <span className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">References:</span>
                    {(msg.sources as Record<string, string>[]).map((src, si) => (
                      <a 
                        key={si} 
                        href={src.url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--surface-solid)] border border-[var(--line)] hover:bg-[var(--surface-muted)] hover:border-[var(--accent-soft)] hover:text-[var(--accent)] text-[var(--text-secondary)] rounded shadow-inner text-[11px] font-bold uppercase transition-all"
                      >
                        <ExternalLink className="w-3 h-3" />
                        {src.type}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-5 animate-fade-in-up">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#818CF8] to-[#C084FC] border border-[#C084FC]/50 shadow-[0_0_15px_rgba(192,132,252,0.3)] flex items-center justify-center">
                <Bot className="w-5 h-5 text-white animate-pulse" />
              </div>
              <div className="bg-[var(--surface-muted)] border border-[var(--line)] rounded-2xl rounded-tl-none px-6 py-4 flex items-center gap-4 shadow-md">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs text-[var(--text-secondary)] font-bold tracking-widest uppercase ml-2 animate-pulse">Gemini is thinking...</span>
              </div>
            </div>
          )}
          
          <div ref={bottomRef} className="h-4" />
        </div>

        {/* Action Tray */}
        <div className="p-4 sm:p-6 bg-[var(--surface-solid)] border-t border-[var(--line)] relative z-10 shadow-[0_-10px_20px_rgba(0,0,0,0.2)]">
          {messages.length <= 1 && (
            <div className="mb-5">
              <p className="text-[10px] uppercase font-bold tracking-[0.2em] text-[var(--accent)] mb-3">Suggested queries</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button 
                    key={s} 
                    onClick={() => send(s)}
                    className="px-4 py-2 bg-[var(--surface-muted)] hover:bg-[var(--surface)] border border-[var(--line)] hover:border-[var(--accent-soft)] text-white hover:text-[var(--accent)] rounded-xl text-xs font-semibold tracking-wide transition-all shadow-inner hover:-translate-y-0.5"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 relative">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask for details, compare variants, or draft summaries..."
              className="flex-1 px-5 py-4 bg-[var(--surface-muted)] border border-[var(--line)] rounded-xl text-sm font-medium text-white placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] focus:bg-[var(--surface)] focus:ring-4 focus:ring-[var(--accent-soft)] transition-all shadow-inner"
              disabled={loading}
              autoFocus
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="px-6 py-4 bg-gradient-to-br from-[var(--accent)] to-[#2563EB] shadow-[0_0_15px_rgba(56,189,248,0.4)] hover:shadow-[0_0_25px_rgba(56,189,248,0.6)] disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-all hover:scale-105 active:scale-95"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
