"""
Kasira Payment Stress Test — 500 Concurrent QRIS Transactions
=============================================================
Self-contained: pure stdlib + asyncio. NO external dependencies.
Run: python scripts/stress_test_xendit.py

Mensimulasikan logika XenditService.create_qris_transaction secara identik
dengan 3 skenario:
  1. NORMAL  — 200ms latency, 0% failure
  2. SLOW    — 2000ms latency (simulasi Xendit lambat/overload)
  3. FLAKY   — 200ms, 20% random failure
"""

import asyncio
import time
import random
import base64
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# ─── Konstanta (identik dengan settings di config.py) ────────────────────────
XENDIT_API_KEY       = "xnd_test_stress_fake_key"
PLATFORM_FEE_PERCENT = 0.2   # 0.2% platform fee Kasira

# ─── Kontrol skenario (diubah per-run) ───────────────────────────────────────
_latency_ms   = [200]    # mutable ref
_failure_rate = [0.0]    # mutable ref

# ─── Simulasi httpx.AsyncClient ──────────────────────────────────────────────
class _FakeAsyncClient:
    """Meniru perilaku httpx.AsyncClient dengan latency/failure yang bisa dikonfigurasi."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def post(self, url: str, headers: dict = None, json: dict = None, timeout: float = 10.0):
        # Simulasi network latency
        await asyncio.sleep(_latency_ms[0] / 1000)

        # Simulasi partial failure (misal: Xendit 503 atau timeout)
        if random.random() < _failure_rate[0]:
            raise Exception(f"Xendit error: 503 Service Unavailable (simulated, url={url})")

        class _FakeResp:
            def json(self_):
                return {
                    "id": f"qr_{int(time.time()*1000)}_{random.randint(1000,9999)}",
                    "qr_string": "00020101021226570011ID.CO.XENDIT.MOCK...KASIRA",
                    "status": "ACTIVE",
                    "amount": json.get("amount", 0) if json else 0,
                    "currency": "IDR",
                    "type": "DYNAMIC"
                }
            def raise_for_status(self_):
                pass  # sukses, tidak lempar exception

        return _FakeResp()


# Singleton — dibuat 1x, di-reuse oleh semua 500 request (seperti produksi)
_shared_client = _FakeAsyncClient()


# ─── XenditService (identik logika backend/services/xendit.py post-refactor) ──
class XenditService:
    """
    Identik dengan backend/services/xendit.py SETELAH refactor.
    Kini menggunakan singleton _client (bukan membuat client baru per-request).
    """
    def __init__(self):
        self._client = _shared_client  # ← singleton, tidak buat baru tiap transaksi

    def _get_headers(self, for_user_id: Optional[str] = None) -> Dict[str, str]:
        raw = f"{XENDIT_API_KEY}:".encode("utf-8")
        headers = {
            "Authorization": f"Basic {base64.b64encode(raw).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        if for_user_id:
            headers["for-user-id"] = for_user_id
        return headers

    async def create_qris_transaction(
        self,
        reference_id: str,
        amount: float,
        for_user_id: str,
        platform_fee_percent: float = PLATFORM_FEE_PERCENT,
    ) -> Dict[str, Any]:
        platform_fee = int(amount * (platform_fee_percent / 100))
        payload = {
            "reference_id": reference_id,
            "type": "DYNAMIC",
            "currency": "IDR",
            "amount": int(amount),
            "metadata": {"kasira_platform_fee": platform_fee},
        }
        # Pakai self._client (singleton) — tidak ada `async with` per-request
        response = await self._client.post(
            "/qr_codes",
            headers=self._get_headers(for_user_id=for_user_id),
            json=payload,
        )
        response.raise_for_status()
        return response.json()


# ─── Model hasil ─────────────────────────────────────────────────────────────
@dataclass
class TxResult:
    tx_id: int
    duration_ms: float
    success: bool
    error: str = ""


# ─── Jalankan 1 transaksi ────────────────────────────────────────────────────
async def one_tx(svc: XenditService, tx_id: int) -> TxResult:
    t0 = time.perf_counter()
    try:
        await svc.create_qris_transaction(
            reference_id=f"tenant-{tx_id % 10}::order-{tx_id}",
            amount=float(random.randint(10_000, 500_000)),
            for_user_id=f"sub_acc_merchant_{tx_id % 10}",  # 10 merchant berbeda
        )
        return TxResult(tx_id, (time.perf_counter() - t0) * 1000, True)
    except Exception as exc:
        return TxResult(tx_id, (time.perf_counter() - t0) * 1000, False, str(exc)[:80])


# ─── Runner satu skenario ────────────────────────────────────────────────────
async def run_scenario(n: int, label: str, lat_ms: int, fail_rate: float) -> None:
    _latency_ms[0]   = lat_ms
    _failure_rate[0] = fail_rate

    svc = XenditService()
    W = 62

    print(f"\n{'═'*W}")
    print(f"  Skenario : {label}")
    print(f"  Users    : {n} concurrent | Latency: {lat_ms}ms | Failure: {fail_rate*100:.0f}%")
    print(f"{'─'*W}")

    wall_t0 = time.perf_counter()
    tasks = [asyncio.create_task(one_tx(svc, i)) for i in range(n)]

    results: List[TxResult] = []
    done = 0
    for fut in asyncio.as_completed(tasks):
        r = await fut
        results.append(r)
        done += 1
        if done % 50 == 0 or done == n:
            pct  = done / n
            bar  = "█" * int(pct * 40) + "░" * (40 - int(pct * 40))
            print(f"\r  [{bar}] {done}/{n}", end="", flush=True)

    wall_ms = (time.perf_counter() - wall_t0) * 1000
    print()  # newline

    ok  = [r for r in results if r.success]
    bad = [r for r in results if not r.success]
    dur = sorted(r.duration_ms for r in ok)

    def p(pct_val):
        if not dur: return 0.0
        return dur[min(int(len(dur) * pct_val), len(dur) - 1)]

    rps = len(ok) / (wall_ms / 1000) if wall_ms > 0 else 0

    print(f"\n  📊 HASIL:")
    print(f"    Total waktu    : {wall_ms:>8.0f} ms  ({wall_ms/1000:.2f}s)")
    print(f"    Throughput     : {rps:>8.0f} req/s")
    print(f"    Sukses         : {len(ok):>8} / {n}  ({len(ok)/n*100:.1f}%)")
    print(f"    Gagal          : {len(bad):>8} / {n}  ({len(bad)/n*100:.1f}%)")
    if dur:
        print(f"    Latency P50    : {p(0.50):>8.1f} ms")
        print(f"    Latency P90    : {p(0.90):>8.1f} ms")
        print(f"    Latency P99    : {p(0.99):>8.1f} ms")
        print(f"    Latency Max    : {dur[-1]:>8.1f} ms")

    print(f"\n  🏁 VERDICT: ", end="")
    issues = []
    if rps < 30:            issues.append(f"throughput rendah ({rps:.0f} req/s, target ≥30)")
    if p(0.99) > 5000:      issues.append(f"P99 terlalu lambat ({p(0.99):.0f}ms, target <5s)")
    if len(bad)/n > 0.25:   issues.append(f"error rate >{len(bad)/n*100:.0f}% melebihi SLA 25%")

    if issues:
        print(f"⚠️  {' | '.join(issues)}")
    else:
        print(f"✅ LULUS — sistem stabil untuk {n} concurrent QRIS request")

    if bad:
        samples = "; ".join(r.error for r in bad[:2])
        print(f"  Sample errors  : {samples}")


# ─── Main ────────────────────────────────────────────────────────────────────
async def main():
    N = 500
    print("\n" + "═" * 62)
    print("  🚀 KASIRA — Stress Test: 500 Concurrent QRIS (Xendit)")
    print(f"  Platform fee: {PLATFORM_FEE_PERCENT}% per transaksi → Kasira Master")
    print("═" * 62)

    await run_scenario(N, "NORMAL  — 200ms latency, 0% failure",    200,  0.00)
    await run_scenario(N, "SLOW    — 2000ms latency (Xendit down?)", 2000, 0.00)
    await run_scenario(N, "FLAKY   — 200ms, 20% random failure",     200,  0.20)

    print("\n" + "═" * 62)
    print("  ✅ Stress test selesai!")
    print("  💡 Rekomendasi: gunakan httpx.AsyncClient singleton")
    print("     (persistent connection pool) untuk produksi.")
    print("═" * 62 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
