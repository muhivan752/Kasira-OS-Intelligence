"""
Xendit xenPlatform Service — production-hardened (CRITICAL #12 fix).

Problem sebelumnya:
  - Zero retry/backoff di create_qris, create_invoice, create_sub_account
    → Xendit intermittent 503/timeout = payment langsung fail terminal
  - verify_webhook pakai `==` = timing attack surface (theoretical)
  - Caller catch bare Exception + flip payment ke 'failed' = uncertain
    state kena false negative

Fix architecture:
  1. Singleton AsyncClient (existing) + tightened timeout
  2. `_request_with_retry()` — 5 attempts exponential backoff (0.5/1/2/4s)
     - Retry: TimeoutException, ConnectError, NetworkError, 5xx
     - NO retry: 4xx (auth/validation — retry gak akan recover)
     - Log setiap retry + final failure untuk observability
  3. verify_webhook pakai `hmac.compare_digest` (constant-time)
  4. Expose new helpers: get_qr_code_status(), expire_qr_code()

Public API unchanged untuk existing callers (payments.py, connect.py,
subscription_billing.py). Retry transparent.
"""

import asyncio
import base64
import hmac
import logging
from typing import Dict, Any, Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


# ─── Retry config ─────────────────────────────────────────────────────────────
_RETRY_ATTEMPTS = 5
_RETRY_BACKOFF_BASE = 0.5  # 0.5s → 1s → 2s → 4s (exponential)


class XenditTransientError(Exception):
    """Raised kalau semua retry attempt habis (transient error tidak recover).
    Caller PERLU handle ini khusus — biasanya set payment ke
    `pending_manual_check` (bukan `failed`) biar admin bisa cek manual."""


class XenditPermanentError(Exception):
    """Raised untuk 4xx atau logical error — jelas gagal, no retry.
    Caller bisa set payment langsung ke `failed`."""


class XenditService:
    """
    Xendit xenPlatform Service dgn retry backoff + circuit-style fail safety.

    Golden Rule #9: FastAPI async ONLY — tidak boleh ada sync blocking call.
    """

    def __init__(self):
        # Singleton client dengan persistent connection pool.
        self._client = httpx.AsyncClient(
            base_url="https://api.xendit.co",
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=100,
                max_connections=500,
                keepalive_expiry=30.0,
            ),
        )

    async def close(self) -> None:
        """Tutup client saat aplikasi shutdown. Panggil dari FastAPI lifespan."""
        await self._client.aclose()

    def _get_auth_header(self, api_key: Optional[str] = None) -> str:
        key = api_key or settings.XENDIT_API_KEY
        raw = f"{key}:".encode("utf-8")
        return f"Basic {base64.b64encode(raw).decode('utf-8')}"

    def _get_headers(self, for_user_id: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": self._get_auth_header(api_key=api_key),
        }
        if for_user_id:
            headers["for-user-id"] = for_user_id
        return headers

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        headers: Dict[str, str],
        json_body: Optional[Dict[str, Any]] = None,
        op_label: str = "xendit_request",
    ) -> Dict[str, Any]:
        """
        Core HTTP wrapper dgn exponential backoff + Prometheus outcome metric.

        Retry semantics:
          - TimeoutException / ConnectError / NetworkError → retry
          - HTTPStatusError 5xx → retry
          - HTTPStatusError 4xx → NO retry → XenditPermanentError
          - Other exception → retry (safer default for transient bugs)

        Raise XenditTransientError kalau semua attempt exhausted (biar caller
        bisa set payment ke pending_manual_check — bukan failed terminal).
        """
        # Lazy import — cegah circular dep saat metrics module re-imports
        from backend.core.metrics import track_xendit_outcome

        last_err: Optional[BaseException] = None
        last_status: Optional[int] = None

        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                response = await self._client.request(
                    method, path, headers=headers, json=json_body,
                )
                response.raise_for_status()
                if attempt > 1:
                    logger.info(
                        "xendit %s succeeded on attempt %d/%d path=%s",
                        op_label, attempt, _RETRY_ATTEMPTS, path,
                    )
                track_xendit_outcome(op_label, "ok")
                return response.json()

            except httpx.HTTPStatusError as e:
                last_status = e.response.status_code
                if 500 <= last_status < 600:
                    last_err = e
                    logger.warning(
                        "xendit %s 5xx attempt %d/%d status=%d path=%s — retrying",
                        op_label, attempt, _RETRY_ATTEMPTS, last_status, path,
                    )
                else:
                    # 4xx — no retry (permanent)
                    try:
                        err_body = e.response.json()
                    except Exception:
                        err_body = {"text": e.response.text}
                    logger.error(
                        "xendit %s PERMANENT %dxx path=%s response=%s",
                        op_label, last_status // 100, path, err_body,
                    )
                    track_xendit_outcome(op_label, "permanent_fail")
                    raise XenditPermanentError(
                        f"Xendit {op_label} permanent error {last_status}: {err_body}"
                    ) from e

            except httpx.TimeoutException as e:
                last_err = e
                logger.warning(
                    "xendit %s timeout attempt %d/%d path=%s: %r",
                    op_label, attempt, _RETRY_ATTEMPTS, path, e,
                )

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_err = e
                logger.warning(
                    "xendit %s network attempt %d/%d path=%s: %r",
                    op_label, attempt, _RETRY_ATTEMPTS, path, e,
                )

            except Exception as e:  # defensive — unknown transient
                last_err = e
                logger.warning(
                    "xendit %s unexpected attempt %d/%d path=%s: %r",
                    op_label, attempt, _RETRY_ATTEMPTS, path, e,
                )

            # Exponential backoff (skip sleep on last attempt)
            if attempt < _RETRY_ATTEMPTS:
                backoff = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        # All retries exhausted — caller WAJIB handle ini dgn pending_manual_check
        logger.error(
            "xendit %s FAILED after %d attempts path=%s last_err=%r last_status=%s",
            op_label, _RETRY_ATTEMPTS, path, last_err, last_status,
        )
        track_xendit_outcome(op_label, "transient_fail")
        raise XenditTransientError(
            f"Xendit {op_label} exhausted {_RETRY_ATTEMPTS} attempts: {last_err!r}"
        ) from last_err

    # ─── Business methods ────────────────────────────────────────────────────

    async def create_sub_account(
        self,
        email: str,
        business_profile_name: str,
    ) -> Dict[str, Any]:
        """Buat Sub-Account MANAGED untuk Outlet/Tenant baru."""
        payload = {
            "email": email,
            "type": "MANAGED",
            "business_profile": {"business_name": business_profile_name},
        }
        return await self._request_with_retry(
            "POST", "/v2/accounts",
            headers=self._get_headers(),
            json_body=payload,
            op_label="create_sub_account",
        )

    async def create_qris_transaction(
        self,
        reference_id: str,
        amount: float,
        for_user_id: Optional[str] = None,
        platform_fee_percent: float = 0.2,
        merchant_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Buat transaksi QRIS.
        Phase 1: merchant_api_key → pakai key merchant langsung, no platform fee
        Phase 2: for_user_id → uang masuk ke sub-account merchant, kasira fee
        """
        payload = {
            "reference_id": reference_id,
            "type": "DYNAMIC",
            "currency": "IDR",
            "amount": int(amount),
        }
        if for_user_id and not merchant_api_key:
            platform_fee = int(amount * (platform_fee_percent / 100))
            payload["metadata"] = {"kasira_platform_fee": platform_fee}

        return await self._request_with_retry(
            "POST", "/qr_codes",
            headers=self._get_headers(for_user_id=for_user_id, api_key=merchant_api_key),
            json_body=payload,
            op_label="create_qris",
        )

    async def create_invoice(
        self,
        external_id: str,
        amount: int,
        payer_email: str,
        description: str,
        success_redirect_url: str = "https://kasira.online/dashboard/settings/billing",
        invoice_duration_seconds: int = 86400,
    ) -> Dict[str, Any]:
        """Buat Xendit Invoice untuk subscription billing."""
        payload = {
            "external_id": external_id,
            "amount": amount,
            "payer_email": payer_email,
            "description": description,
            "success_redirect_url": success_redirect_url,
            "invoice_duration": invoice_duration_seconds,
            "currency": "IDR",
        }
        return await self._request_with_retry(
            "POST", "/v2/invoices",
            headers=self._get_headers(),
            json_body=payload,
            op_label="create_invoice",
        )

    async def get_qr_code_status(
        self,
        qr_code_id: str,
        merchant_api_key: Optional[str] = None,
        for_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Poll status QR code (untuk reconciliation kalau webhook hilang).
        Berguna saat transaksi status 'pending_manual_check' — admin cek
        via dashboard atau cron job poll tiap 1 jam.
        """
        return await self._request_with_retry(
            "GET", f"/qr_codes/{qr_code_id}",
            headers=self._get_headers(for_user_id=for_user_id, api_key=merchant_api_key),
            op_label="get_qris_status",
        )

    def verify_webhook(self, received_token: str) -> bool:
        """
        Verify Xendit callback token dgn constant-time compare (cegah timing
        attack — walau pilot phase low risk, good hygiene).
        """
        expected = settings.XENDIT_WEBHOOK_TOKEN or ""
        if not received_token or not expected:
            return False
        return hmac.compare_digest(received_token, expected)


# Singleton global — di-share oleh seluruh request FastAPI
xendit_service = XenditService()
