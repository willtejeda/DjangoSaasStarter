from __future__ import annotations

from collections.abc import Sequence
from typing import Any

try:  # pragma: no cover - import path validated in runtime tests
    import tiktoken
except Exception:  # pragma: no cover - fallback exercised by unit tests
    tiktoken = None


DEFAULT_ENCODING = "o200k_base"
FALLBACK_ENCODING = "cl100k_base"


def _normalize_model(model: str | None) -> str:
    normalized = str(model or "").strip()
    if not normalized:
        return ""
    # OpenRouter model names often include provider prefixes such as
    # "openai/gpt-4.1-mini". tiktoken expects "gpt-4.1-mini".
    if "/" in normalized:
        normalized = normalized.split("/")[-1]
    return normalized


def _resolve_encoding(model: str | None):
    if tiktoken is None:
        return None

    normalized = _normalize_model(model)
    candidates = [normalized]
    if normalized and "-" in normalized:
        candidates.append(normalized.split("-")[0])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return tiktoken.encoding_for_model(candidate)
        except Exception:
            continue

    for encoding_name in (DEFAULT_ENCODING, FALLBACK_ENCODING):
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception:
            continue
    return None


def count_text_tokens(text: str, *, model: str | None = None) -> int:
    value = str(text or "")
    if not value:
        return 0

    encoding = _resolve_encoding(model)
    if encoding is None:
        # Conservative fallback when tokenizer package is unavailable.
        return max(len(value) // 4, 1)
    return len(encoding.encode(value))


def count_message_tokens(messages: Sequence[dict[str, Any]], *, model: str | None = None) -> int:
    if not messages:
        return 0

    # This follows the documented approximate chat counting approach.
    # Exact server-side provider usage still overrides this when available.
    total = 0
    for message in messages:
        total += 4
        role = str((message or {}).get("role") or "")
        content = str((message or {}).get("content") or "")
        name = str((message or {}).get("name") or "")

        total += count_text_tokens(role, model=model)
        total += count_text_tokens(content, model=model)
        if name:
            total += count_text_tokens(name, model=model) - 1

    total += 2
    return max(total, 0)
