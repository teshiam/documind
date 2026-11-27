import time
from collections.abc import Iterator

from .config import settings
from .store import Retrieved

SYSTEM_PROMPT = """You are DocuMind, an assistant that answers questions using ONLY the provided \
context excerpts from the user's documents.

Rules:
- If the context does not contain the answer, say you couldn't find it in the documents. \
Do not guess or use outside knowledge.
- Cite the excerpts you used inline like [1] or [2][3], matching the excerpt numbers.
- Be concise and direct."""

NO_ANSWER = "I couldn't find anything relevant to that in your documents."


def filter_relevant(chunks: list[Retrieved], min_score: float | None = None) -> list[Retrieved]:
    threshold = settings.min_score if min_score is None else min_score
    return [c for c in chunks if c.score >= threshold]


def build_context(chunks: list[Retrieved]) -> str:
    return "\n\n".join(
        f"[{i}] ({c.filename}, p.{c.page})\n{c.content}" for i, c in enumerate(chunks, start=1)
    )


def build_user_prompt(question: str, chunks: list[Retrieved]) -> str:
    return f"Context excerpts:\n\n{build_context(chunks)}\n\nQuestion: {question}"


def _stream_extractive(chunks: list[Retrieved]) -> Iterator[str]:
    """Free mode: no LLM. Show the best-matching passage with a citation.

    The remaining matches are returned separately as `sources`, so the UI still shows them.
    """
    yield "Free mode (no language model configured). The best match in your documents is: "
    best = chunks[0].content.strip()
    words = best.split()
    shown = " ".join(words[:90]) + (" …" if len(words) > 90 else "")
    for i in range(0, len(shown), 24):  # small slices so the UI streams like a real answer
        yield shown[i : i + 24]
        time.sleep(0.01)
    yield " [1]"


def _stream_openai_compatible(question: str, chunks: list[Retrieved]) -> Iterator[str]:
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.llm_base_url or None,
        api_key=settings.llm_api_key or "not-needed",  # local servers like Ollama ignore it
    )
    stream = client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=1024,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, chunks)},
        ],
    )
    for event in stream:
        if event.choices and event.choices[0].delta.content:
            yield event.choices[0].delta.content


def _stream_anthropic(question: str, chunks: list[Retrieved]) -> Iterator[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    with client.messages.stream(
        model=settings.llm_model or "claude-sonnet-5-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(question, chunks)}],
    ) as stream:
        yield from stream.text_stream


def stream_answer(question: str, chunks: list[Retrieved]) -> Iterator[str]:
    """Yield answer text as it is generated. Never calls an LLM when nothing relevant was found."""
    if not chunks:
        yield NO_ANSWER
        return

    provider = settings.llm_provider
    if provider == "extractive":
        yield from _stream_extractive(chunks)
    elif provider == "openai_compatible":
        yield from _stream_openai_compatible(question, chunks)
    else:
        yield from _stream_anthropic(question, chunks)


def answer(question: str, chunks: list[Retrieved]) -> str:
    return "".join(stream_answer(question, chunks))
