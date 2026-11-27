"use client";

import { useCallback, useEffect, useState } from "react";
import Chat from "@/components/Chat";
import Sidebar from "@/components/Sidebar";
import {
  deleteDocument,
  getHealth,
  listDocuments,
  uploadDocument,
  type DocumentInfo,
  type Health,
} from "@/lib/api";

const SAMPLE_NAME = "acme_handbook.md";

export default function Home() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [h, d] = await Promise.all([getHealth(), listDocuments()]);
      setHealth(h);
      setDocs(d);
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleUpload(files: File[]) {
    setUploading(true);
    setError(null);
    for (const file of files) {
      try {
        await uploadDocument(file);
      } catch (err) {
        setError(`${file.name}: ${err instanceof Error ? err.message : "upload failed"}`);
      }
    }
    await refresh();
    setUploading(false);
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete document");
    }
  }

  async function handleLoadSample() {
    try {
      const res = await fetch(`/sample/${SAMPLE_NAME}`);
      const blob = await res.blob();
      await handleUpload([new File([blob], SAMPLE_NAME, { type: "text/markdown" })]);
    } catch {
      setError("Could not load the sample document.");
    }
  }

  const hasSample = docs.some((d) => d.filename === SAMPLE_NAME);

  return (
    <div className={`app${menuOpen ? " app-menu-open" : ""}`}>
      <button
        type="button"
        className="menu-btn"
        onClick={() => setMenuOpen((v) => !v)}
        aria-label="Toggle documents panel"
      >
        ☰
      </button>
      <Sidebar
        docs={docs}
        health={health}
        offline={offline}
        uploading={uploading}
        error={error}
        hasSample={hasSample}
        onUpload={handleUpload}
        onDelete={handleDelete}
        onLoadSample={handleLoadSample}
      />
      <main className="main">
        {offline && (
          <div className="banner" role="alert">
            Can&apos;t reach the DocuMind API. Start it with <code>docker compose up</code> and
            refresh.
          </div>
        )}
        <Chat hasDocs={docs.length > 0} hasSample={hasSample} health={health} />
      </main>
    </div>
  );
}
