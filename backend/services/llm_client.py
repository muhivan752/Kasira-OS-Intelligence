"""Router provider LLM untuk Kasira.

Kasira jalan di dua provider sekaligus:

- **DeepSeek** — semua task kelas Haiku: chat POS, insight Beranda, proposal
  menu/resep, WA bot. Murah, cukup buat analitik UMKM bahasa Indonesia.
- **Anthropic** — dipertahankan buat PRICING_COACH (Sonnet) dan invoice OCR
  (vision — DeepSeek belum punya model yang bisa baca gambar).

Routing-nya satu switch: model id yang mengandung "haiku" dibelokin ke DeepSeek
selama `DEEPSEEK_API_KEY` keisi. Artinya call site gak perlu ganti string model
satu-satu, dan rollback = kosongin DEEPSEEK_API_KEY di .env (semua balik ke
Anthropic tanpa deploy kode).

Facade ini sengaja meniru permukaan SDK Anthropic yang dipakai call site —
`await client.messages.create(...)` dan `async with client.messages.stream(...)`
dengan `.text_stream` + `.get_final_message()` — supaya `ai_service.py` dan
`wa_bot.py` cukup ganti cara bikin client, bukan cara manggilnya.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# deepseek-v4-flash = tier murah (alias "deepseek-chat"). v4-pro dipakai kalau
# suatu saat butuh reasoning lebih berat.
DEEPSEEK_CHAT_MODEL = "deepseek-v4-flash"


# ─── Response shim (bentuknya niru objek SDK Anthropic) ──────────────────────

@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _Message:
    content: list = field(default_factory=list)
    usage: _Usage = field(default_factory=_Usage)
    model: str = ""


# ─── Routing ─────────────────────────────────────────────────────────────────

def deepseek_enabled() -> bool:
    return bool(settings.DEEPSEEK_API_KEY)


def chat_configured() -> bool:
    """Ada minimal satu provider chat yang bisa dipakai."""
    return bool(settings.DEEPSEEK_API_KEY or settings.ANTHROPIC_API_KEY)


def route_model(model: str) -> tuple[str, str]:
    """Model id → (provider, model id yang dikirim ke provider)."""
    if deepseek_enabled() and "haiku" in (model or "").lower():
        return "deepseek", settings.DEEPSEEK_CHAT_MODEL or DEEPSEEK_CHAT_MODEL
    return "anthropic", model


def _to_openai_messages(system: Optional[str], messages: list) -> list:
    """Format Anthropic → format OpenAI/DeepSeek.

    Beda utamanya: Anthropic naruh system prompt di parameter terpisah,
    DeepSeek naruh sebagai message pertama dengan role "system".
    """
    out = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages or []:
        content = m.get("content")
        if isinstance(content, list):
            # Content block Anthropic — ambil bagian teksnya aja.
            content = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        out.append({"role": m.get("role", "user"), "content": content or ""})
    return out


def _base_payload(model: str, max_tokens: int, system: Optional[str],
                  messages: list) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": _to_openai_messages(system, messages),
        # WAJIB. deepseek-v4 itu reasoning model by default, dan token thinking
        # dihitung ke dalam max_tokens. Tanpa ini, request pendek (insight
        # Beranda max_tokens=160) habis 159 token buat mikir → `content` balik
        # STRING KOSONG tanpa error, dan proposal menu/resep kepotong separo.
        # Task Kasira analitik ringan, gak butuh reasoning trace.
        "thinking": {"type": "disabled"},
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


# ─── DeepSeek: non-streaming ─────────────────────────────────────────────────

async def _deepseek_create(
    *, model: str, max_tokens: int, system: Optional[str],
    messages: list, timeout: float,
) -> _Message:
    payload = _base_payload(model, max_tokens, system, messages)
    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload, headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices") or []
    text = (choices[0].get("message", {}).get("content") or "") if choices else ""
    usage = data.get("usage") or {}
    return _Message(
        content=[_TextBlock(text=text)],
        usage=_Usage(
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        ),
        model=data.get("model", model),
    )


# ─── DeepSeek: streaming ─────────────────────────────────────────────────────

class _DeepSeekStream:
    """Async context manager yang meniru `client.messages.stream()` Anthropic."""

    def __init__(self, *, model: str, max_tokens: int, system: Optional[str],
                 messages: list, timeout: float):
        self._payload = {
            **_base_payload(model, max_tokens, system, messages),
            "stream": True,
            # Tanpa ini DeepSeek gak kirim usage di akhir stream, dan
            # tracking token (+ billing counter) jadi nol terus.
            "stream_options": {"include_usage": True},
        }
        self._model = model
        self._timeout = timeout
        self._usage = _Usage()
        self._buffer: list[str] = []

    async def __aenter__(self) -> "_DeepSeekStream":
        self._http = httpx.AsyncClient(timeout=self._timeout)
        self._ctx = self._http.stream(
            "POST", f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=self._payload, headers=_headers(),
        )
        self._resp = await self._ctx.__aenter__()
        if self._resp.status_code >= 400:
            body = (await self._resp.aread()).decode("utf-8", "replace")[:400]
            await self.__aexit__(None, None, None)
            raise RuntimeError(f"DeepSeek HTTP {self._resp.status_code}: {body}")
        return self

    async def __aexit__(self, *exc) -> None:
        try:
            await self._ctx.__aexit__(*exc)
        finally:
            await self._http.aclose()

    @property
    def text_stream(self) -> AsyncGenerator[str, None]:
        return self._iter_text()

    async def _iter_text(self) -> AsyncGenerator[str, None]:
        async for line in self._resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            usage = event.get("usage")
            if usage:
                self._usage = _Usage(
                    input_tokens=int(usage.get("prompt_tokens") or 0),
                    output_tokens=int(usage.get("completion_tokens") or 0),
                )
            for choice in event.get("choices") or []:
                chunk = (choice.get("delta") or {}).get("content")
                if chunk:
                    self._buffer.append(chunk)
                    yield chunk

    async def get_final_message(self) -> _Message:
        return _Message(
            content=[_TextBlock(text="".join(self._buffer))],
            usage=self._usage,
            model=self._model,
        )


# ─── Facade ──────────────────────────────────────────────────────────────────

class _Messages:
    def __init__(self, timeout: float):
        self._timeout = timeout
        self._anthropic: Any = None

    def _anthropic_client(self):
        if self._anthropic is None:
            import anthropic
            self._anthropic = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY, timeout=self._timeout,
            )
        return self._anthropic

    async def create(self, *, model: str, max_tokens: int, messages: list,
                     system: Optional[str] = None, **kwargs):
        provider, model_id = route_model(model)
        if provider == "deepseek":
            return await _deepseek_create(
                model=model_id, max_tokens=max_tokens, system=system,
                messages=messages, timeout=self._timeout,
            )
        kw = {"model": model_id, "max_tokens": max_tokens, "messages": messages, **kwargs}
        if system is not None:
            kw["system"] = system
        return await self._anthropic_client().messages.create(**kw)

    def stream(self, *, model: str, max_tokens: int, messages: list,
               system: Optional[str] = None, **kwargs):
        provider, model_id = route_model(model)
        if provider == "deepseek":
            return _DeepSeekStream(
                model=model_id, max_tokens=max_tokens, system=system,
                messages=messages, timeout=self._timeout,
            )
        kw = {"model": model_id, "max_tokens": max_tokens, "messages": messages, **kwargs}
        if system is not None:
            kw["system"] = system
        return self._anthropic_client().messages.stream(**kw)


class LLMClient:
    def __init__(self, timeout: float = 25.0):
        self.messages = _Messages(timeout)


def get_llm_client(timeout: float = 25.0) -> LLMClient:
    """Client chat yang otomatis milih provider per model id."""
    return LLMClient(timeout=timeout)
