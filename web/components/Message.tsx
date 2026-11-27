"use client";

import { useState } from "react";
import type { Source } from "@/lib/api";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  status: "streaming" | "done" | "error";
  error?: string;
};

function renderWithCitations(
  text: string,
  sources: Source[],
  open: number | null,
  onCite: (n: number) => void,
) {
  return text.split(/(\[\d+\])/g).map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) return <span key={i}>{part}</span>;
    const n = Number(match[1]);
    if (!sources.some((s) => s.n === n)) return <span key={i}>{part}</span>;
    return (
      <button
        key={i}
        type="button"
        className={`cite${open === n ? " cite-active" : ""}`}
        onClick={() => onCite(n)}
        aria-label={`Show source ${n}`}
      >
        {n}
      </button>
    );
  });
}

export default function Message({ message }: { message: ChatMessage }) {
  const [open, setOpen] = useState<number | null>(null);
  const toggle = (n: number) => setOpen((cur) => (cur === n ? null : n));

  if (message.role === "user") {
    return (
      <div className="row row-user">
        <div className="bubble bubble-user">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="row">
      <div className="avatar" aria-hidden="true">
        D
      </div>
      <div className="assistant">
        <div className="answer" aria-live="polite">
          {message.content
            ? renderWithCitations(message.content, message.sources, open, toggle)
            : message.status === "streaming" && <span className="typing">Thinking…</span>}
          {message.status === "streaming" && message.content && <span className="caret" />}
        </div>

        {message.status === "error" && (
          <div className="inline-error" role="alert">
            {message.error ?? "Something went wrong."}
          </div>
        )}

        {message.sources.length > 0 && (
          <div className="sources">
            <div className="sources-title">Sources</div>
            {message.sources.map((s) => (
              <button
                key={s.n}
                type="button"
                className={`source${open === s.n ? " source-open" : ""}`}
                onClick={() => toggle(s.n)}
                aria-expanded={open === s.n}
              >
                <span className="source-head">
                  <span className="source-n">{s.n}</span>
                  <span className="source-file">{s.filename}</span>
                  <span className="source-meta">
                    p.{s.page} · {Math.round(s.score * 100)}% match
                  </span>
                </span>
                {open === s.n && <span className="source-snippet">{s.snippet}…</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
