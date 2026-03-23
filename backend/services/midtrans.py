import httpx
import base64
import json
import hashlib
from typing import Dict, Any, Optional
from backend.core.config import settings

class MidtransService:
    def _get_base_url(self, is_production: bool) -> str:
        if is_production:
            return "https://api.midtrans.com/v2"
        return "https://api.sandbox.midtrans.com/v2"
        
    def _get_headers(self, server_key: str) -> Dict[str, str]:
        auth_string = f"{server_key}:".encode("utf-8")
        auth_header = f"Basic {base64.b64encode(auth_string).decode('utf-8')}"
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": auth_header
        }

    async def create_qris_transaction(
        self, 
        order_id: str, 
        gross_amount: float, 
        server_key: str,
        is_production: bool,
        custom_field1: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a QRIS transaction using Midtrans Core API.
        """
        payload = {
            "payment_type": "qris",
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(gross_amount)
            }
        }
        
        if custom_field1:
            payload["custom_field1"] = custom_field1

        base_url = self._get_base_url(is_production)
        headers = self._get_headers(server_key)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/charge",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            
            response.raise_for_status()
            return response.json()

    def verify_signature(
        self, 
        order_id: str, 
        status_code: str, 
        gross_amount: str, 
        signature_key: str,
        server_key: str
    ) -> bool:
        """
        Verify Midtrans webhook signature key.
        """
        payload = f"{order_id}{status_code}{gross_amount}{server_key}"
        calculated_signature = hashlib.sha512(payload.encode("utf-8")).hexdigest()
        return calculated_signature == signature_key

midtrans_service = MidtransService()
