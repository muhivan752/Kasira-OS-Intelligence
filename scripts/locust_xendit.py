import time
import asyncio
import nest_asyncio
from locust import User, task, events
from unittest.mock import patch

# Terapkan nest_asyncio agar event loop asyncio bisa berjalan mulus di dalam gevent thread Locust.
nest_asyncio.apply()

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.xendit import xendit_service

# Class Mock untuk merespons layaknya Xendit asli
class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data
        
    def json(self):
        return self._json_data
        
    def raise_for_status(self):
        pass

# Fungsi untuk simulasi latency API Xendit yang lemot (Mocking Network Latency)
async def mock_post_delay(*args, **kwargs):
    # Simulasi Xendit merespons lambat sekitar 1.5 detik
    await asyncio.sleep(1.5)
    return MockResponse(200, {"qr_string": "mock-qr-payload-123456789"})


class XenditStressTester(User):
    # Tidak ada jeda (wait_time), bombardir sistem secepat mungkin
    
    def on_start(self):
        # Setiap virtual user akan punya event loop kecilnya sendiri
        self.loop = asyncio.new_event_loop()
        
    def on_stop(self):
        self.loop.close()

    @task
    def stress_create_qris(self):
        start_time = time.time()
        
        try:
            # Kita monkey-patch metode post dari http.AsyncClient untuk memotong traffic ke public API
            # dan menggantinya dengan mock_post_delay
            with patch('httpx.AsyncClient.post', new=mock_post_delay):
                
                # Eksekusi fungsi internal service yang ada di backend lu
                res = self.loop.run_until_complete(
                    xendit_service.create_qris_transaction(
                        reference_id="stress-test-order",
                        amount=25000.0,
                        for_user_id="test_sub_account_xendit_123"
                    )
                )
            
            # Hitung millisecond
            total_time = int((time.time() - start_time) * 1000)
            
            # Tembakkan event ke Locust Dashboard agar tercatat di UI Web
            events.request.fire(
                request_type="PythonAsync",
                name="XenditService.create_qris_transaction",
                response_time=total_time,
                response_length=len(str(res)),
                exception=None,
            )
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            
            # Jika ada gagal, laporkan exception
            events.request.fire(
                request_type="PythonAsync",
                name="XenditService.create_qris_transaction",
                response_time=total_time,
                response_length=0,
                exception=e,
            )

# Cara nge-run:
# Buka terminal dan jalankan perintah ini di dalam root folder:
# locust -f scripts/locust_xendit.py --host=http://localhost:8000
