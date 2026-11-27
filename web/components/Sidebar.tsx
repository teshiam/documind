"use client";

import { useRef, useState, type DragEvent } from "react";
import type { DocumentInfo, Health } from "@/lib/api";

type Props = {
  docs: DocumentInfo[];
  health: Health | null;
  offline: boolean;
  uploading: boolean;
  error: string | null;
  hasSample: boolean;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
  onLoadSample: () => void;
};

export default function Sidebar({
  docs,
  health,
  offline,
  uploading,
  error,
  hasSample,
  onUpload,
  onDelete,
  onLoadSample,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onUpload(files);
  };

  const modeLabel = offline
    ? "API offline"
    : health?.llm_provider === "extractive"
      ? "Free mode · passages only"
      : health
        ? `LLM · ${health.llm_model}`
        : "Connecting…";

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="logo" aria-hidden="true">
          D
        </span>
        <span className="brand-name">DocuMind</span>
      </div>

      <div className={`status${offline ? " status-off" : ""}`}>
        <span className="dot" />
        {modeLabel}
      </div>

      <div
        className={`drop${dragging ? " drop-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.md,.txt"
          multiple
          hidden
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            if (files.length) onUpload(files);
            e.target.value = "";
          }}
        />
        <p>Drop files here</p>
        <small>PDF, Markdown or text · up to 10 MB</small>
        <button
          type="button"
          className="btn"
          onClick={() => inputRef.current?.click()}
          disabled={uploading || offline}
        >
          {uploading ? "Processing…" : "Choose files"}
        </button>
      </div>

      {!hasSample && (
        <button type="button" className="btn btn-ghost" onClick={onLoadSample} disabled={uploading || offline}>
          Try with a sample document
        </button>
      )}

      {error && (
        <div className="inline-error" role="alert">
          {error}
        </div>
      )}

      <div className="docs-title">Documents ({docs.length})</div>
      <ul className="docs">
        {docs.length === 0 && <li className="docs-empty">Nothing uploaded yet.</li>}
        {docs.map((d) => (
          <li key={d.id} className="doc">
            <div className="doc-info">
              <span className="doc-name" title={d.filename}>
                {d.filename}
              </span>
              <span className="doc-meta">{d.chunks} chunks</span>
            </div>
            <button
              type="button"
              className="icon-btn"
              onClick={() => onDelete(d.id)}
              aria-label={`Delete ${d.filename}`}
              title="Delete"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
