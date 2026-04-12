import httpx
import base64
from typing import Dict, Any, Optional
from backend.core.config import settings


class XenditService:
    """
    Xendit xenPlatform Service.

    Menggunakan singleton httpx.AsyncClient dengan connection pooling
    untuk menghindari TCP handshake berulang saat 500+ request concurrent.

    Golden Rule #9: FastAPI async ONLY — tidak boleh ada sync blocking call.
    """

    def __init__(self):
        # Singleton client dengan persistent connection pool.
        # limits: max 100 koneksi keep-alive, max 500 total koneksi (cukup untuk 500 user).
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
            # Header krusial xenPlatform: request dilakukan atas nama Sub-Account merchant
            headers["for-user-id"] = for_user_id
        return headers

    async def create_sub_account(
        self,
        email: str,
        business_profile_name: str,
    ) -> Dict[str, Any]:
        """
        Buat Sub-Account bertipe MANAGED untuk Outlet/Tenant baru.
        Dipanggil otomatis saat onboarding outlet baru.
        """
        payload = {
            "email": email,
            "type": "MANAGED",
            "business_profile": {"business_name": business_profile_name},
        }
        response = await self._client.post(
            "/v2/accounts",
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

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

        Phase 1 (pilot): merchant_api_key diisi → pakai key merchant langsung, no platform fee
        Phase 2 (xenPlatform): for_user_id diisi → uang masuk ke sub-account merchant, kasira potong fee
        """
        payload = {
            "reference_id": reference_id,
            "type": "DYNAMIC",
            "currency": "IDR",
            "amount": int(amount),
        }
        if for_user_id and not merchant_api_key:
            # Phase 2 xenPlatform
            platform_fee = int(amount * (platform_fee_percent / 100))
            payload["metadata"] = {"kasira_platform_fee": platform_fee}

        response = await self._client.post(
            "/qr_codes",
            headers=self._get_headers(for_user_id=for_user_id, api_key=merchant_api_key),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def create_invoice(
        self,
        external_id: str,
        amount: int,
        payer_email: str,
        description: str,
        success_redirect_url: str = "https://kasira.online/dashboard/settings/billing",
        invoice_duration_seconds: int = 86400,
    ) -> Dict[str, Any]:
        """
        Buat Xendit Invoice untuk subscription billing.
        Pakai platform API key (bukan merchant key).
        """
        payload = {
            "external_id": external_id,
            "amount": amount,
            "payer_email": payer_email,
            "description": description,
            "success_redirect_url": success_redirect_url,
            "invoice_duration": invoice_duration_seconds,
            "currency": "IDR",
        }
        response = await self._client.post(
            "/v2/invoices",
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def verify_webhook(self, received_token: str) -> bool:
        """Verifikasi Xendit webhook callback token."""
        return received_token == settings.XENDIT_WEBHOOK_TOKEN


# Singleton global — di-share oleh seluruh request FastAPI
xendit_service = XenditService()
