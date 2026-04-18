"""
Kasira load test scenarios — locust.

Run:
    cd /var/www/kasira/load_test
    locust -f locustfile.py --host http://localhost:8000

UI: http://<vps-ip>:8089. Atau headless:
    locust -f locustfile.py --host http://localhost:8000 \
        --users 50 --spawn-rate 5 --run-time 3m --headless \
        --csv=results/run_50u --html=results/run_50u.html

Scenarios (weights):
  - CashierUser (70%): auth/me → products → create order → pay
  - SyncUser (20%): POST /sync/ push offline orders + pull latest
  - DashboardUser (10%): reports/daily + products list
"""
import json
import random
import uuid
from pathlib import Path

from locust import HttpUser, task, between, events


# ── Load seeded config ───────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"
with CONFIG_PATH.open() as f:
    CFG = json.load(f)

JWTS = CFG.get("jwts") or [CFG["jwt"]]
USER_IDS = CFG.get("user_ids") or [CFG["user_id"]]
USER_SHIFTS = CFG.get("user_shifts") or {CFG["user_id"]: CFG["shift_id"]}
TENANT_ID = CFG["tenant_id"]
OUTLET_ID = CFG["outlet_id"]
PRODUCT_IDS = CFG["product_ids"]
PRODUCT_PRICES = CFG["product_prices"]

_user_counter = 0


def pick_user_config() -> dict:
    """Round-robin pick: returns (headers, shift_id) buat 1 locust user."""
    global _user_counter
    idx = _user_counter % len(JWTS)
    _user_counter += 1
    uid = USER_IDS[idx]
    return {
        "headers": {
            "Authorization": f"Bearer {JWTS[idx]}",
            "X-Tenant-ID": TENANT_ID,
            "Content-Type": "application/json",
        },
        "shift_id": USER_SHIFTS.get(uid, CFG.get("shift_id")),
    }


class CashierUser(HttpUser):
    """Simulate cashier doing normal POS flow."""
    weight = 7
    wait_time = between(1, 3)  # think time 1-3 detik antar action

    def on_start(self):
        cfg = pick_user_config(); self.HEADERS = cfg["headers"]; self.SHIFT_ID = cfg["shift_id"]

    @task(1)
    def auth_me(self):
        self.client.get("/api/v1/auth/me", headers=self.HEADERS, name="GET /auth/me")

    @task(5)
    def list_products(self):
        self.client.get(
            f"/api/v1/products/?outlet_id={OUTLET_ID}&limit=50",
            headers=self.HEADERS,
            name="GET /products/",
        )

    @task(3)
    def create_order_and_pay(self):
        # Random 1-3 items per order
        num_items = random.randint(1, 3)
        items = []
        total = 0.0
        for _ in range(num_items):
            pid = random.choice(PRODUCT_IDS)
            qty = random.randint(1, 2)
            price = PRODUCT_PRICES[pid]
            item_total = price * qty
            total += item_total
            items.append({
                "product_id": pid,
                "quantity": qty,
                "unit_price": price,
                "total_price": item_total,
            })

        # Step 1: create order (takeaway biar gak butuh meja)
        order_payload = {
            "outlet_id": OUTLET_ID,
            "shift_session_id": self.SHIFT_ID,
            "order_type": "takeaway",
            "items": items,
        }
        with self.client.post(
            "/api/v1/orders/",
            headers=self.HEADERS,
            json=order_payload,
            name="POST /orders/",
            catch_response=True,
        ) as order_res:
            if order_res.status_code >= 300:
                order_res.failure(f"order create fail {order_res.status_code}: {order_res.text[:200]}")
                return
            try:
                order_data = order_res.json().get("data") or order_res.json()
                order_id = order_data.get("id") or order_data.get("order_id")
            except Exception:
                order_res.failure("invalid JSON response")
                return
            if not order_id:
                order_res.failure("no order_id in response")
                return

        # Step 2: create payment
        payment_payload = {
            "order_id": order_id,
            "outlet_id": OUTLET_ID,
            "amount": total,
            "amount_due": total,
            "amount_paid": total,
            "payment_method": "cash",
            "idempotency_key": str(uuid.uuid4()),
        }
        self.client.post(
            "/api/v1/payments/",
            headers=self.HEADERS,
            json=payment_payload,
            name="POST /payments/",
        )


class SyncUser(HttpUser):
    """Simulate offline POS pushing batch + pulling latest."""
    weight = 2
    wait_time = between(5, 15)  # sync less frequent

    def on_start(self):
        cfg = pick_user_config(); self.HEADERS = cfg["headers"]; self.SHIFT_ID = cfg["shift_id"]

    @task
    def sync_push_pull(self):
        # Minimal push — empty changes + pull
        payload = {
            "node_id": f"loadtest:{OUTLET_ID}:node-{random.randint(1, 100)}",
            "last_sync_hlc": None,
            "changes": {
                "categories": [],
                "products": [],
                "orders": [],
                "order_items": [],
                "payments": [],
                "shifts": [],
                "cash_activities": [],
                "outlet_stock": [],
            },
        }
        self.client.post(
            "/api/v1/sync/",
            headers=self.HEADERS,
            json=payload,
            name="POST /sync/",
        )


class DashboardUser(HttpUser):
    """Simulate owner checking dashboard."""
    weight = 1
    wait_time = between(3, 8)

    def on_start(self):
        cfg = pick_user_config(); self.HEADERS = cfg["headers"]; self.SHIFT_ID = cfg["shift_id"]

    @task(2)
    def daily_report(self):
        self.client.get(
            f"/api/v1/reports/daily?outlet_id={OUTLET_ID}",
            headers=self.HEADERS,
            name="GET /reports/daily",
        )

    @task(1)
    def products_list(self):
        self.client.get(
            f"/api/v1/products/?outlet_id={OUTLET_ID}&limit=50",
            headers=self.HEADERS,
            name="GET /products/ (dashboard)",
        )


# ── Hook: print summary ────────────────────────────────────────────────
@events.test_stop.add_listener
def on_test_stop(environment, **kw):
    stats = environment.stats.total
    print(f"\n── Summary ──")
    print(f"Total requests: {stats.num_requests}")
    print(f"Failures: {stats.num_failures} ({100*stats.num_failures/max(stats.num_requests,1):.2f}%)")
    print(f"Median response time: {stats.median_response_time} ms")
    print(f"P95: {stats.get_response_time_percentile(0.95)} ms")
    print(f"P99: {stats.get_response_time_percentile(0.99)} ms")
    print(f"RPS: {stats.total_rps:.1f}")
