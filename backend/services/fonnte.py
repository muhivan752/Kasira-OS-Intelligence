"""
Fonnte WhatsApp wrapper — production-hardened.

Problem (audit CRITICAL #13):
  - Dulu bikin `httpx.AsyncClient` baru per-call (no singleton, no keepalive)
  - Zero timeout → koneksi hang bisa block seluruh login request
  - Zero retry → Fonnte transient 5xx / timeout langsung gagal
  - Zero circuit breaker → provider down total = setiap OTP request wait
    sampai timeout habis, cascading slow-fail

Fix architecture:
  1. Singleton AsyncClient reuse connection pool + keepalive
  2. Per-request timeout ketat (connect 2s, read 4s) — worst case 3x4 = 12s
  3. Exponential backoff retry — 3 attempts, 0.5s → 1s gap
  4. Circuit breaker — setelah 5 consecutive fail, skip calls 60s (fail-fast
     biar user gak nunggu OTP yang pasti gagal). Auto half-open setelah
     cooldown — 1 probe request; success tutup circuit, fail re-open.

Scope: wrapper only, public API `send_whatsapp_message(phone, message) -> bool`
unchanged. Zero touch di 9 caller (auth OTP, reservations, payments, webhook,
connect, superadmin, subscription_billing, wa_bot).

Observability: setiap retry + circuit transition di-log untuk Sentry/alerting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


# ─── Config ───────────────────────────────────────────────────────────────────
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 0.5  # 0.5s, 1s — exponential (base * 2^(n-1))
_HTTP_TIMEOUT = httpx.Timeout(4.0, connect=2.0)  # read 4s, connect 2s
_FONNTE_URL = "https://api.fonnte.com/send"

# Circuit breaker tuning
_CIRCUIT_FAIL_THRESHOLD = 5      # 5 consec fails → open circuit
_CIRCUIT_COOLDOWN_SEC = 60.0     # 60s timeout before probing


# ─── Circuit state (module singleton) ─────────────────────────────────────────
@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    opened_at: float = 0.0  # unix timestamp when circuit opened (0 = closed)


_circuit = _CircuitState()


def _circuit_is_open() -> bool:
    """
    True kalau circuit terbuka (skip calls). Auto half-open setelah cooldown
    — 1 probe request diizinkan; success close, failure re-open.
    """
    if _circuit.consecutive_failures < _CIRCUIT_FAIL_THRESHOLD:
        return False  # closed
    elapsed = time.time() - _circuit.opened_at
    if elapsed >= _CIRCUIT_COOLDOWN_SEC:
        # Half-open: probe next call. Reset counter agar 1 fail re-open.
        logger.info(
            "Fonnte circuit half-open after %.1fs cooldown — probing next call",
            elapsed,
        )
        _circuit.consecutive_failures = _CIRCUIT_FAIL_THRESHOLD - 1
        return False
    return True  # still open


def _record_success() -> None:
    """Close circuit on success (reset counter)."""
    if _circuit.consecutive_failures > 0:
        logger.info(
            "Fonnte circuit recovered (was %d consec fails) — closed",
            _circuit.consecutive_failures,
        )
    _circuit.consecutive_failures = 0
    _circuit.opened_at = 0.0


def _record_failure(reason: str) -> None:
    """Track failure; open circuit kalau threshold tercapai."""
    _circuit.consecutive_failures += 1
    if _circuit.consecutive_failures == _CIRCUIT_FAIL_THRESHOLD:
        _circuit.opened_at = time.time()
        logger.error(
            "Fonnte circuit OPENED after %d consecutive failures — "
            "skipping calls for %.0fs. Last reason: %s",
            _CIRCUIT_FAIL_THRESHOLD, _CIRCUIT_COOLDOWN_SEC, reason,
        )


# ─── Singleton HTTP client ────────────────────────────────────────────────────
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client


async def close_client() -> None:
    """Call di shutdown hook kalau ada (opsional, httpx auto-cleanup saat process exit)."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


# ─── Public API ───────────────────────────────────────────────────────────────
async def send_whatsapp_message(phone: str, message: str) -> bool:
    """
    Kirim pesan WA via Fonnte. Return True on success, False on failure.

    Behavior:
      - Kalau FONNTE_TOKEN gak di-set → simulate success (dev mode)
      - Kalau circuit OPEN → fail-fast return False (no network call)
      - Kalau transient error (timeout, 5xx) → retry 2x dgn backoff
      - Kalau permanent error (4xx, logical fail) → no retry, return False
    """
    if not settings.FONNTE_TOKEN:
        logger.warning("FONNTE_TOKEN not set. Simulating WA to %s", phone)
        return True

    # Circuit breaker — fail-fast kalau provider lagi mati total
    if _circuit_is_open():
        logger.warning(
            "Fonnte circuit OPEN — skip send to %s (cooldown %.0fs)",
            phone, _CIRCUIT_COOLDOWN_SEC,
        )
        return False

    headers = {"Authorization": settings.FONNTE_TOKEN}
    data = {"target": phone, "message": message}
    client = _get_client()

    last_reason: str = "unknown"
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            response = await client.post(_FONNTE_URL, headers=headers, data=data)
            # HTTPStatusError untuk 4xx/5xx
            response.raise_for_status()
            result = response.json()
            if result.get("status"):
                _record_success()
                return True
            # API responded 200 tapi logical error (invalid target, quota habis, dll)
            # — don't retry, won't recover dgn retry semata
            last_reason = f"logical_error: {result}"
            logger.error(
                "Fonnte logical error (no retry) phone=%s: %s", phone, result,
            )
            _record_failure(last_reason)
            return False

        except httpx.TimeoutException as e:
            last_reason = f"timeout attempt {attempt}/{_RETRY_ATTEMPTS}: {e!r}"
            logger.warning("Fonnte %s", last_reason)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if 500 <= status < 600:
                # 5xx — retry
                last_reason = f"http_{status} attempt {attempt}/{_RETRY_ATTEMPTS}"
                logger.warning("Fonnte %s", last_reason)
            else:
                # 4xx — auth/validation error, won't recover
                last_reason = f"http_{status} (no retry, permanent)"
                logger.error("Fonnte %s phone=%s", last_reason, phone)
                _record_failure(last_reason)
                return False

        except (httpx.ConnectError, httpx.NetworkError) as e:
            last_reason = f"network_error attempt {attempt}/{_RETRY_ATTEMPTS}: {e!r}"
            logger.warning("Fonnte %s", last_reason)

        except Exception as e:
            last_reason = f"unexpected attempt {attempt}/{_RETRY_ATTEMPTS}: {e!r}"
            logger.warning("Fonnte %s", last_reason)

        # Exponential backoff — skip sleep on last attempt
        if attempt < _RETRY_ATTEMPTS:
            backoff = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)

    # Semua attempt gagal — retries exhausted
    logger.error(
        "Fonnte send failed after %d attempts phone=%s last=%s",
        _RETRY_ATTEMPTS, phone, last_reason,
    )
    _record_failure(last_reason)
    return False
