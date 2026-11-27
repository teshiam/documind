export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DocumentInfo = {
  id: string;
  filename: string;
  chunks: number;
  created_at?: string | null;
};

export type Source = {
  n: number;
  filename: string;
  page: number;
  score: number;
  snippet: string;
};

export type Health = {
  status: string;
  llm_provider: "extractive" | "openai_compatible" | "anthropic";
  llm_model: string;
};

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through
  }
  return `Request failed (${res.status})`;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_URL}/documents`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await errorMessage(res));
}

export type AskHandlers = {
  onSources: (sources: Source[]) => void;
  onToken: (token: string) => void;
  onError: (message: string) => void;
};

function dispatch(block: string, handlers: AskHandlers) {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return;
  const data = JSON.parse(dataLines.join("\n"));
  if (event === "sources") handlers.onSources(data as Source[]);
  else if (event === "token") handlers.onToken(data as string);
  else if (event === "error") handlers.onError(String(data));
}

/** POSTs a question and consumes the Server-Sent Events stream until it ends. */
export async function askQuestion(
  question: string,
  handlers: AskHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(await errorMessage(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      dispatch(buffer.slice(0, boundary), handlers);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
  }
}
