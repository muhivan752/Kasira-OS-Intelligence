import httpx
import base64
from typing import Dict, Any, Optional
from backend.core.config import settings

class XenditService:
    def _get_base_url(self) -> str:
        return "https://api.xendit.co"
        
    def _get_headers(self, for_user_id: Optional[str] = None) -> Dict[str, str]:
        auth_string = f"{settings.XENDIT_API_KEY}:".encode("utf-8")
        auth_header = f"Basic {base64.b64encode(auth_string).decode('utf-8')}"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": auth_header
        }
        
        if for_user_id:
            # Menggunakan xenPlatform untuk mengarahkan request ke Sub-Account
            headers["for-user-id"] = for_user_id
            
        return headers

    async def create_sub_account(
        self, 
        email: str, 
        business_profile_name: str,
    ) -> Dict[str, Any]:
        """
        Membuat Sub-Account bertipe MANAGED untuk Outlet/Tenant baru.
        Akun Managed ini akan menerima pembayaran langsung, dan Pemilik bisa diundang ke Dashboard Xendit.
        """
        payload = {
            "email": email,
            "type": "MANAGED",
            "business_profile": {
                "business_name": business_profile_name
            }
        }
        
        base_url = self._get_base_url()
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v2/accounts",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def create_qris_transaction(
        self, 
        reference_id: str, 
        amount: float, 
        for_user_id: str,
        platform_fee_percent: float = 0.2
    ) -> Dict[str, Any]:
        """
        Create a QRIS transaction for a Sub-Account.
        """
        # Kalkulasi platform fee (contoh: 0.2%)
        platform_fee_amount = int(amount * (platform_fee_percent / 100))
        
        # Payload standar untuk QR_CODES. 
        # (Catatan: Dokumentasi Xendit untuk Split Fee QRIS yang dinamis biasa menggunakan Payment Requests API 
        # atau setting Split Rule pada akun xenPlatform secara global. Di sini kita set payload standarnya).
        payload = {
            "reference_id": reference_id,
            "type": "DYNAMIC",
            "currency": "IDR",
            "amount": int(amount),
            "metadata": {
                "kasira_platform_fee": platform_fee_amount
            }
        }
        
        base_url = self._get_base_url()
        # Header for_user_id krusial agar uang masuk ke akun Merchant, BUKAN Kasira Master!
        headers = self._get_headers(for_user_id=for_user_id) 

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/qr_codes",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    def verify_webhook(self, received_token: str) -> bool:
        """
        Verify Xendit webhook signature using the global callback token.
        """
        return received_token == settings.XENDIT_WEBHOOK_TOKEN

xendit_service = XenditService()
