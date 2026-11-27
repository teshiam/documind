import json

from fastapi.testclient import TestClient

from app import main
from app.store import Retrieved


def _parse_sse(body: str) -> list[tuple[str, object]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.split("\n")
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


def test_ask_streams_sources_tokens_then_done(monkeypatch):
    chunks = [Retrieved("Employees get 25 days of leave.", 1, "handbook.md", 0.82)]
    monkeypatch.setattr(main, "embed_query", lambda q: [0.0] * 384)
    monkeypatch.setattr(main.store, "search", lambda emb, k: chunks)
    monkeypatch.setattr(main.rag.settings, "llm_provider", "extractive")

    res = TestClient(main.app).post("/ask", json={"question": "How much leave?"})
    assert res.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(res.text)
    names = [name for name, _ in events]
    assert names[0] == "sources"
    assert names[-1] == "done"
    assert "token" in names

    sources = events[0][1]
    assert sources[0]["filename"] == "handbook.md" and sources[0]["n"] == 1
    answer = "".join(data for name, data in events if name == "token")
    assert "25 days of leave" in answer


def test_ask_with_no_relevant_chunks_returns_fallback(monkeypatch):
    monkeypatch.setattr(main, "embed_query", lambda q: [0.0] * 384)
    monkeypatch.setattr(main.store, "search", lambda emb, k: [Retrieved("x", 1, "a.md", 0.05)])

    res = TestClient(main.app).post("/ask", json={"question": "Unrelated question"})
    events = _parse_sse(res.text)
    assert events[0] == ("sources", [])
    answer = "".join(data for name, data in events if name == "token")
    assert "couldn't find" in answer
