// Kasira Batch #30 Tahap 2 — Load Hammer
// Target: /sync/ (read-heavy) + /orders/ (write path)
// Tenant: _loadtest_tenant (426c79ee-f86d-4b5a-9cef-63bf24bbd677)
// Outlet: LoadTest Outlet (0465ade4-81d3-444b-bd4f-d5d0485263c4)
// Ramp: 10 → 25 → 50 → 100 VUs, ~12min total
//
// Run:
//   k6 run --env TOKEN="<jwt>" --env PRODUCT_IDS="id1,id2,id3" loadtest/batch30/k6_hammer.js
//
// Metrics: p50, p95, p99, error rate, RPS per endpoint
// Abort criteria: error_rate > 1% (auto-fail via thresholds)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// ── Config ───────────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api/v1';
const TOKEN = __ENV.TOKEN;
const TENANT_ID = __ENV.TENANT_ID || '426c79ee-f86d-4b5a-9cef-63bf24bbd677';
const OUTLET_ID = __ENV.OUTLET_ID || '0465ade4-81d3-444b-bd4f-d5d0485263c4';
const PRODUCT_IDS = (__ENV.PRODUCT_IDS || '').split(',').filter(Boolean);

if (!TOKEN) throw new Error('Pass TOKEN env: --env TOKEN="<jwt>"');
if (PRODUCT_IDS.length === 0) throw new Error('Pass PRODUCT_IDS env: comma-separated UUID list');

const baseHeaders = {
  'Authorization': `Bearer ${TOKEN}`,
  'X-Tenant-ID': TENANT_ID,
  'X-Test-Run': 'batch-30-load',
  'Content-Type': 'application/json',
};

// ── Custom metrics per endpoint ─────────────────────────────────────────
const syncDuration = new Trend('sync_duration', true);
const ordersDuration = new Trend('orders_duration', true);
const syncFails = new Rate('sync_fails');
const ordersFails = new Rate('orders_fails');
const ordersCreated = new Counter('orders_created');

// ── Load profile ─────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '2m', target: 25 },   // ramp 10→25
        { duration: '2m', target: 50 },   // ramp 25→50
        { duration: '2m', target: 50 },   // hold 50 (measure baseline)
        { duration: '2m', target: 100 },  // ramp 50→100
        { duration: '3m', target: 100 },  // hold 100 (stress peak)
        { duration: '1m', target: 0 },    // ramp down graceful
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    // Abort criteria — abortOnFail cancels run immediately
    'http_req_failed': [{ threshold: 'rate<0.01', abortOnFail: true, delayAbortEval: '30s' }],
    'http_req_duration{endpoint:sync}': ['p(95)<1500', 'p(99)<3000'],
    'http_req_duration{endpoint:orders}': ['p(95)<2000', 'p(99)<5000'],
    'sync_fails': ['rate<0.01'],
    'orders_fails': ['rate<0.02'],
  },
};

// ── Request helpers ──────────────────────────────────────────────────────
function doSyncPull() {
  const payload = JSON.stringify({
    node_id: `k6-vu-${__VU}`,
    outlet_id: OUTLET_ID,
    last_sync_hlc: null,
    idempotency_key: uuidv4(),
    changes: {
      products: [], categories: [], orders: [], order_items: [],
      payments: [], outlet_stock: [], shifts: [], cash_activities: [],
    },
  });
  const res = http.post(`${BASE_URL}/sync/`, payload, {
    headers: baseHeaders,
    tags: { endpoint: 'sync' },
  });
  syncDuration.add(res.timings.duration);
  syncFails.add(res.status !== 200);
  check(res, { 'sync 200': (r) => r.status === 200 });
}

function doCreateOrder() {
  const productId = PRODUCT_IDS[Math.floor(Math.random() * PRODUCT_IDS.length)];
  const idemKey = uuidv4();
  const payload = JSON.stringify({
    outlet_id: OUTLET_ID,
    order_type: 'dine_in',
    notes: `batch30-load-${idemKey.slice(0, 8)}`,
    items: [
      { product_id: productId, quantity: 1, notes: null },
    ],
  });
  const headers = { ...baseHeaders, 'Idempotency-Key': idemKey };
  const res = http.post(`${BASE_URL}/orders/`, payload, {
    headers,
    tags: { endpoint: 'orders' },
  });
  ordersDuration.add(res.timings.duration);
  ordersFails.add(res.status >= 400);
  const ok = check(res, { 'orders 200/201': (r) => r.status === 200 || r.status === 201 });
  if (ok) ordersCreated.add(1);
}

// ── Scenario body ────────────────────────────────────────────────────────
export default function () {
  // 70% sync pull, 30% order create — skewed read to mimic typical workload
  const r = Math.random();
  if (r < 0.7) {
    doSyncPull();
  } else {
    doCreateOrder();
  }
  sleep(Math.random() * 0.5 + 0.2); // 0.2–0.7s between iterations per VU
}

// ── Summary output — print simple table at end ───────────────────────────
export function handleSummary(data) {
  const m = data.metrics;
  const get = (name, field) => m[name]?.values?.[field]?.toFixed?.(0) ?? 'n/a';
  const summary = `
╔════════════════════════════════════════════════════════════════╗
║ KASIRA BATCH #30 — LOAD HAMMER RESULT                          ║
╚════════════════════════════════════════════════════════════════╝

Total requests:   ${m.http_reqs.values.count}
Request rate:     ${m.http_reqs.values.rate.toFixed(2)} RPS
Failure rate:     ${(m.http_req_failed.values.rate * 100).toFixed(2)}%
VUs peak:         ${m.vus_max.values.max}

┌─────────────┬──────────┬──────────┬──────────┬──────────┐
│ Endpoint    │ p50 (ms) │ p95 (ms) │ p99 (ms) │ fails %  │
├─────────────┼──────────┼──────────┼──────────┼──────────┤
│ /sync/      │ ${get('sync_duration','med').padStart(8)} │ ${get('sync_duration','p(95)').padStart(8)} │ ${get('sync_duration','p(99)').padStart(8)} │ ${((m.sync_fails?.values?.rate ?? 0) * 100).toFixed(2).padStart(7)}% │
│ /orders/    │ ${get('orders_duration','med').padStart(8)} │ ${get('orders_duration','p(95)').padStart(8)} │ ${get('orders_duration','p(99)').padStart(8)} │ ${((m.ordersFails?.values?.rate ?? 0) * 100).toFixed(2).padStart(7)}% │
└─────────────┴──────────┴──────────┴──────────┴──────────┘

Orders created:   ${m.orders_created?.values?.count ?? 0}
Total duration:   ${(m.http_req_duration.values.avg).toFixed(0)}ms avg

Thresholds:
  p95 /sync <1500ms: ${(m.http_req_duration?.thresholds?.['p(95)<1500'] ?? 'n/a')}
  p95 /orders <2000ms: (see log)
  failure <1%: (see log)
`;
  return {
    stdout: summary,
    'loadtest/batch30/result.json': JSON.stringify(data, null, 2),
  };
}
