"""Egységes LLM-kliens: Groq (OpenAI-kompatibilis), Gemini és lokális OpenAI-kompatibilis végpont (Ollama/vLLM).

- lemezes gyorsítótár (prompt-hash -> válasz): a kiértékelés megismételhető, és nem égeti a free tier kvótát;
- újrapróbálkozás 429/5xx esetén (exponenciális várakozás, a Retry-After figyelembevételével);
- tartalék lánc: ha egy modell tartósan nem elérhető, a következő következik (TERV 1.7).
Modellazonosító formátum: "groq:qwen/qwen3.8-27b", "gemini:gemini-3.5-flash", "local:qwen3:14b".
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests
import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
CACHE_DIR = ROOT / ".cache" / "llm"

DEFAULT_GENERATOR = ["groq:qwen/qwen3.8-27b", "groq:openai/gpt-oss-120b", "gemini:gemini-3.5-flash"]
DEFAULT_JUDGE = ["gemini:gemini-3.5-flash", "groq:openai/gpt-oss-120b"]


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    model: str
    cached: bool
    latency_s: float
    usage: dict


def _cache_key(model: str, messages: list[dict], temperature: float, json_mode: bool) -> str:
    blob = json.dumps({"m": model, "msg": messages, "t": temperature, "j": json_mode}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _post(url: str, headers: dict, payload: dict, max_retries: int = 6) -> dict:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.RequestException as e:  # hálózati hiba
            if attempt == max_retries - 1:
                raise LLMError(str(e)) from e
            time.sleep(delay)
            delay *= 2
            continue
        if r.ok:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
            ra = r.headers.get("retry-after")
            wait = float(ra) if ra and ra.replace(".", "").isdigit() else delay
            time.sleep(min(wait, 60))
            delay = min(delay * 2, 60)
            continue
        raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
    raise LLMError("túl sok újrapróbálkozás")


def _call_groq(model: str, messages: list[dict], temperature: float, json_mode: bool) -> tuple[str, dict]:
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    j = _post(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        payload,
    )
    return j["choices"][0]["message"]["content"], j.get("usage", {})


def _call_local(model: str, messages: list[dict], temperature: float, json_mode: bool) -> tuple[str, dict]:
    base = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    j = _post(f"{base}/chat/completions", {}, payload)
    return j["choices"][0]["message"]["content"], j.get("usage", {})


def _call_gemini(model: str, messages: list[dict], temperature: float, json_mode: bool) -> tuple[str, dict]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    payload: dict = {"contents": contents, "generationConfig": {"temperature": temperature}}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    j = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        payload,
    )
    try:
        text = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError) as e:
        raise LLMError(f"üres Gemini-válasz: {json.dumps(j)[:300]}") from e
    return text, j.get("usageMetadata", {})


PROVIDERS = {"groq": _call_groq, "gemini": _call_gemini, "local": _call_local}


def chat(
    messages: list[dict],
    models: list[str] | str = DEFAULT_GENERATOR,
    temperature: float = 0.0,
    json_mode: bool = False,
    use_cache: bool = True,
) -> LLMResponse:
    chain = [models] if isinstance(models, str) else list(models)
    errors = []
    for model in chain:
        key = _cache_key(model, messages, temperature, json_mode)
        path = CACHE_DIR / key[:2] / f"{key}.json"
        if use_cache and path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            return LLMResponse(d["text"], model, True, 0.0, d.get("usage", {}))
        provider, _, name = model.partition(":")
        t0 = time.time()
        try:
            text, usage = PROVIDERS[provider](name, messages, temperature, json_mode)
        except (LLMError, KeyError) as e:
            errors.append(f"{model}: {e}")
            continue
        resp = LLMResponse(text, model, False, time.time() - t0, usage)
        if use_cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": model, "text": text, "usage": usage}, ensure_ascii=False), encoding="utf-8")
        return resp
    raise LLMError("minden modell sikertelen:\n" + "\n".join(errors))


def parse_json(text: str) -> dict:
    """JSON-válasz kinyerése (a modellek néha ```json kerítésbe teszik)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start : end + 1])
