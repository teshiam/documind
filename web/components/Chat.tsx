"use client";

import { useEffect, useRef, useState } from "react";
import { askQuestion, type Health } from "@/lib/api";
import Message, { type ChatMessage } from "./Message";

const SAMPLE_QUESTIONS = [
  "How many days of annual leave do employees get?",
  "How many days can I work remotely?",
  "How soon must a security incident be reported?",
];
const GENERIC_QUESTIONS = ["Summarize the key points of my documents", "What are the main topics covered?"];

type Props = {
  hasDocs: boolean;
  hasSample: boolean;
  health: Health | null;
};

export default function Chat({ hasDocs, hasSample, health }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const patchLast = (patch: (m: ChatMessage) => ChatMessage) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? patch(m) : m)));

  async function send(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    const stamp = Date.now();
    setMessages((prev) => [
      ...prev,
      { id: `u${stamp}`, role: "user", content: text, sources: [], status: "done" },
      { id: `a${stamp}`, role: "assistant", content: "", sources: [], status: "streaming" },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await askQuestion(
        text,
        {
          onSources: (sources) => patchLast((m) => ({ ...m, sources })),
          onToken: (token) => patchLast((m) => ({ ...m, content: m.content + token })),
          onError: (message) => patchLast((m) => ({ ...m, status: "error", error: message })),
        },
        controller.signal,
      );
      patchLast((m) => (m.status === "streaming" ? { ...m, status: "done" } : m));
    } catch (err) {
      if (controller.signal.aborted) {
        patchLast((m) => ({ ...m, status: "done" }));
      } else {
        const message = err instanceof Error ? err.message : "Something went wrong.";
        patchLast((m) => ({ ...m, status: "error", error: message }));
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  const suggestions = hasSample ? SAMPLE_QUESTIONS : GENERIC_QUESTIONS;
  const freeMode = health?.llm_provider === "extractive";

  return (
    <section className="chat">
      <div className="thread">
        {messages.length === 0 ? (
          <div className="empty">
            <h1>Ask your documents anything</h1>
            <p>
              {hasDocs
                ? "Answers come with numbered citations that point to the exact file and page."
                : "Upload a PDF, Markdown, or text file in the sidebar, or load the sample document to try it."}
            </p>
            {freeMode && (
              <p className="hint">
                Running in <strong>free mode</strong>: no language model is connected, so you get the
                best-matching passage with its source. Connect a free LLM in <code>.env</code> for
                written answers.
              </p>
            )}
            {hasDocs && (
              <div className="chips">
                {suggestions.map((q) => (
                  <button key={q} type="button" className="chip" onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map((m) => <Message key={m.id} message={m} />)
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={hasDocs ? "Ask a question about your documents…" : "Upload a document first…"}
          disabled={!hasDocs}
          aria-label="Your question"
        />
        {busy ? (
          <button type="button" className="btn btn-stop" onClick={() => abortRef.current?.abort()}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn btn-primary" disabled={!hasDocs || input.trim().length < 3}>
            Ask
          </button>
        )}
      </form>
    </section>
  );
}
