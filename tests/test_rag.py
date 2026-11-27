from app import rag
from app.store import Retrieved


def _r(text: str, page: int = 1, score: float = 0.8) -> Retrieved:
    return Retrieved(content=text, page=page, filename="handbook.md", score=score)


def test_context_numbers_excerpts_with_source_and_page():
    ctx = rag.build_context([_r("Alpha fact.", page=2), _r("Beta fact.", page=5)])
    assert "[1] (handbook.md, p.2)\nAlpha fact." in ctx
    assert "[2] (handbook.md, p.5)\nBeta fact." in ctx


def test_user_prompt_contains_question_and_context():
    prompt = rag.build_user_prompt("What is alpha?", [_r("Alpha fact.")])
    assert "What is alpha?" in prompt
    assert "Alpha fact." in prompt


def test_filter_relevant_drops_low_scores():
    kept = rag.filter_relevant([_r("good", score=0.7), _r("bad", score=0.1)], min_score=0.3)
    assert [c.content for c in kept] == ["good"]


def test_no_chunks_skips_llm_and_returns_fallback():
    assert rag.answer("anything?", []) == rag.NO_ANSWER


def test_extractive_mode_returns_best_passage_with_citation(monkeypatch):
    monkeypatch.setattr(rag.settings, "llm_provider", "extractive")
    text = rag.answer("alpha?", [_r("Alpha fact is 42."), _r("Other.")])
    assert "Alpha fact is 42." in text
    assert text.rstrip().endswith("[1]")


def test_openai_compatible_mode_streams_tokens(monkeypatch):
    class Delta:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.delta = Delta(content)

    class Event:
        def __init__(self, content):
            self.choices = [Choice(content)]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["stream"] is True
            assert "Alpha fact." in kwargs["messages"][1]["content"]
            return iter([Event("Hello "), Event("world [1]"), Event(None)])

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setattr(rag.settings, "llm_provider", "openai_compatible")
    assert rag.answer("q?", [_r("Alpha fact.")]) == "Hello world [1]"
