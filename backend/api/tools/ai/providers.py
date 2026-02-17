from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings

from .tokenizer import count_message_tokens, count_text_tokens


class ProviderExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatResult:
    content: str
    input_tokens: int
    output_tokens: int
    provider: str
    model_name: str
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class ImageResult:
    images: list[dict[str, Any]]
    image_units: int
    provider: str
    model_name: str
    raw_response: dict[str, Any]


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    merged_headers = {"Content-Type": "application/json", **(headers or {})}
    encoded = json.dumps(payload).encode("utf-8")
    request = Request(url=url, data=encoded, headers=merged_headers, method="POST")
    timeout_seconds = int(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 45))

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - controlled endpoint from settings
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
            return data if isinstance(data, dict) else {"raw": data}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ProviderExecutionError(
            f"Provider request failed with HTTP {exc.code}. {body[:400]}".strip()
        ) from exc
    except URLError as exc:
        raise ProviderExecutionError(f"Provider request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderExecutionError("Provider returned non-JSON response.") from exc


def _parse_chat_content(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content.strip()
    if isinstance(raw_content, list):
        parts: list[str] = []
        for item in raw_content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    return str(raw_content or "").strip()


def _simulate_chat(messages: list[dict[str, Any]], model_name: str, max_output_tokens: int) -> ChatResult:
    serialized = json.dumps(messages, sort_keys=True)
    seed = sum(ord(ch) for ch in serialized)
    rng = random.Random(seed)
    lower = min(max_output_tokens, max(1, max_output_tokens // 2))
    target_tokens = rng.randint(lower, max_output_tokens)

    lexicon = [
        "debug",
        "response",
        "pipeline",
        "quota",
        "usage",
        "cycle",
        "enforced",
        "token",
        "tracking",
        "estimate",
        "server",
        "client",
        "subscription",
        "period",
        "verified",
        "result",
    ]
    words: list[str] = []
    while True:
        words.append(rng.choice(lexicon))
        candidate = " ".join(words).strip().capitalize() + "."
        if count_text_tokens(candidate, model=model_name) >= target_tokens:
            output = candidate
            break
        if len(words) > max_output_tokens * 4:
            output = candidate
            break

    input_tokens = count_message_tokens(messages, model=model_name)
    output_tokens = count_text_tokens(output, model=model_name)
    return ChatResult(
        content=output,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider="simulator",
        model_name=model_name,
        raw_response={"mode": "simulator", "target_output_tokens": target_tokens},
    )


def _simulate_images(prompt: str, count: int, model_name: str) -> ImageResult:
    images = [
        {
            "id": str(uuid4()),
            "url": f"debug://image/{uuid4()}",
            "prompt": prompt,
        }
        for _ in range(count)
    ]
    return ImageResult(
        images=images,
        image_units=count,
        provider="simulator",
        model_name=model_name,
        raw_response={"mode": "simulator"},
    )


def _run_openai_compatible_chat(
    *,
    base_url: str,
    api_key: str,
    messages: list[dict[str, Any]],
    model_name: str,
    max_output_tokens: int,
) -> ChatResult:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_output_tokens,
    }
    response = _http_post_json(
        endpoint,
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    choices = response.get("choices") if isinstance(response.get("choices"), list) else []
    message = choices[0].get("message", {}) if choices else {}
    content = _parse_chat_content(message.get("content"))
    if not content:
        raise ProviderExecutionError("Provider chat response did not include assistant content.")

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_tokens = int(usage.get("prompt_tokens") or count_message_tokens(messages, model=model_name))
    output_tokens = int(usage.get("completion_tokens") or count_text_tokens(content, model=model_name))

    return ChatResult(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider="openai_compatible",
        model_name=model_name,
        raw_response=response,
    )


def _run_openai_compatible_images(
    *,
    base_url: str,
    api_key: str,
    prompt: str,
    count: int,
    model_name: str,
    size: str,
) -> ImageResult:
    endpoint = f"{base_url.rstrip('/')}/images/generations"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "n": count,
        "size": size,
    }
    response = _http_post_json(
        endpoint,
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    raw_images = response.get("data") if isinstance(response.get("data"), list) else []
    images: list[dict[str, Any]] = []
    for item in raw_images:
        if not isinstance(item, dict):
            continue
        images.append(
            {
                "id": str(uuid4()),
                "url": item.get("url"),
                "b64_json": item.get("b64_json"),
                "revised_prompt": item.get("revised_prompt"),
            }
        )
    if not images:
        raise ProviderExecutionError("Image provider did not return images.")
    return ImageResult(
        images=images,
        image_units=count,
        provider="openai_compatible",
        model_name=model_name,
        raw_response=response,
    )


def _run_ollama_chat(
    *,
    base_url: str,
    messages: list[dict[str, Any]],
    model_name: str,
) -> ChatResult:
    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }
    response = _http_post_json(endpoint, payload)
    message = response.get("message") if isinstance(response.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise ProviderExecutionError("Ollama response did not include assistant content.")
    input_tokens = int(response.get("prompt_eval_count") or count_message_tokens(messages, model=model_name))
    output_tokens = int(response.get("eval_count") or count_text_tokens(content, model=model_name))
    return ChatResult(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider="ollama",
        model_name=model_name,
        raw_response=response,
    )


def run_chat(
    *,
    provider: str,
    messages: list[dict[str, Any]],
    model_name: str,
    max_output_tokens: int,
) -> ChatResult:
    normalized_provider = str(provider or "simulator").strip().lower()
    normalized_model = str(model_name or "").strip()

    if normalized_provider == "simulator":
        return _simulate_chat(messages, normalized_model, max_output_tokens)

    if normalized_provider == "openrouter":
        api_key = str(getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
        if not api_key:
            raise ProviderExecutionError("OPENROUTER_API_KEY is not configured.")
        base_url = str(getattr(settings, "OPENROUTER_BASE_URL", "") or "").strip() or "https://openrouter.ai/api/v1"
        result = _run_openai_compatible_chat(
            base_url=base_url,
            api_key=api_key,
            messages=messages,
            model_name=normalized_model,
            max_output_tokens=max_output_tokens,
        )
        return ChatResult(
            content=result.content,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            provider="openrouter",
            model_name=result.model_name,
            raw_response=result.raw_response,
        )

    if normalized_provider == "openai":
        api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
        if not api_key:
            raise ProviderExecutionError("OPENAI_API_KEY is not configured.")
        base_url = str(getattr(settings, "OPENAI_BASE_URL", "") or "").strip() or "https://api.openai.com/v1"
        result = _run_openai_compatible_chat(
            base_url=base_url,
            api_key=api_key,
            messages=messages,
            model_name=normalized_model,
            max_output_tokens=max_output_tokens,
        )
        return ChatResult(
            content=result.content,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            provider="openai",
            model_name=result.model_name,
            raw_response=result.raw_response,
        )

    if normalized_provider == "ollama":
        base_url = str(getattr(settings, "OLLAMA_BASE_URL", "") or "").strip() or "http://127.0.0.1:11434"
        result = _run_ollama_chat(
            base_url=base_url,
            messages=messages,
            model_name=normalized_model,
        )
        return result

    raise ProviderExecutionError(f"Unknown provider '{normalized_provider}'.")


def run_images(
    *,
    provider: str,
    prompt: str,
    count: int,
    model_name: str,
    size: str,
) -> ImageResult:
    normalized_provider = str(provider or "simulator").strip().lower()
    normalized_model = str(model_name or "").strip()
    normalized_size = str(size or "1024x1024").strip() or "1024x1024"

    if normalized_provider == "simulator":
        return _simulate_images(prompt, count, normalized_model)

    if normalized_provider == "openrouter":
        api_key = str(getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
        if not api_key:
            raise ProviderExecutionError("OPENROUTER_API_KEY is not configured.")
        base_url = str(getattr(settings, "OPENROUTER_BASE_URL", "") or "").strip() or "https://openrouter.ai/api/v1"
        result = _run_openai_compatible_images(
            base_url=base_url,
            api_key=api_key,
            prompt=prompt,
            count=count,
            model_name=normalized_model,
            size=normalized_size,
        )
        return ImageResult(
            images=result.images,
            image_units=result.image_units,
            provider="openrouter",
            model_name=result.model_name,
            raw_response=result.raw_response,
        )

    if normalized_provider == "openai":
        api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
        if not api_key:
            raise ProviderExecutionError("OPENAI_API_KEY is not configured.")
        base_url = str(getattr(settings, "OPENAI_BASE_URL", "") or "").strip() or "https://api.openai.com/v1"
        result = _run_openai_compatible_images(
            base_url=base_url,
            api_key=api_key,
            prompt=prompt,
            count=count,
            model_name=normalized_model,
            size=normalized_size,
        )
        return ImageResult(
            images=result.images,
            image_units=result.image_units,
            provider="openai",
            model_name=result.model_name,
            raw_response=result.raw_response,
        )

    if normalized_provider == "ollama":
        raise ProviderExecutionError("Ollama image generation is not supported by this scaffold endpoint.")

    raise ProviderExecutionError(f"Unknown provider '{normalized_provider}'.")
