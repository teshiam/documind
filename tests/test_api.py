from fastapi.testclient import TestClient

from app.main import app


def test_health():
    # No `with` block, so the DB lifespan does not run.
    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_provider"] in {"extractive", "openai_compatible", "anthropic"}


def test_rejects_unsupported_upload():
    client = TestClient(app)
    res = client.post("/documents", files={"file": ("pic.png", b"data", "image/png")})
    assert res.status_code == 415


def test_ask_validates_question_length():
    assert TestClient(app).post("/ask", json={"question": "hi"}).status_code == 422
