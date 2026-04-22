-- Kasira Batch #30 Tahap 2 — Load Test Cleanup (idempotent)
-- Targets: orders, order_items, payments, events created oleh k6 hammer
-- Scope: tenant=_loadtest_tenant (426c79ee-f86d-4b5a-9cef-63bf24bbd677)
--        outlet=LoadTest Outlet (0465ade4-81d3-444b-bd4f-d5d0485263c4)
--
-- Identifier tag: orders.notes LIKE 'batch30-load-%'
--
-- Run (host):
--   sudo docker exec -i kasira-db-1 psql -U kasira -d kasira_db < loadtest/batch30/cleanup.sql
--
-- Safety: pakai BEGIN/ROLLBACK dulu buat dry-run (SELECT count), baru COMMIT.

BEGIN;

-- RLS context — tenant scope enforced
SELECT set_config('app.current_tenant_id', '426c79ee-f86d-4b5a-9cef-63bf24bbd677', false);

-- ── 1. Preview count (dry-run) ──────────────────────────────────────────
WITH target AS (
  SELECT id FROM orders
  WHERE outlet_id = '0465ade4-81d3-444b-bd4f-d5d0485263c4'
    AND notes LIKE 'batch30-load-%'
    AND deleted_at IS NULL
)
SELECT
  (SELECT count(*) FROM target) AS orders_to_delete,
  (SELECT count(*) FROM order_items WHERE order_id IN (SELECT id FROM target)) AS order_items_to_delete,
  (SELECT count(*) FROM payments WHERE order_id IN (SELECT id FROM target)) AS payments_to_delete;

-- ── 2. Delete children first (FK chain) ─────────────────────────────────
DELETE FROM order_items
  WHERE order_id IN (
    SELECT id FROM orders
    WHERE outlet_id = '0465ade4-81d3-444b-bd4f-d5d0485263c4'
      AND notes LIKE 'batch30-load-%'
  );

DELETE FROM payments
  WHERE order_id IN (
    SELECT id FROM orders
    WHERE outlet_id = '0465ade4-81d3-444b-bd4f-d5d0485263c4'
      AND notes LIKE 'batch30-load-%'
  );

-- Sync idempotency records pakai X-Test-Run header tracking — beda table
DELETE FROM sync_idempotency
  WHERE idempotency_key LIKE 'batch30-%'
     OR idempotency_key IN (
       SELECT idempotency_key FROM sync_idempotency
        WHERE created_at >= NOW() - INTERVAL '2 hours'
          AND tenant_id = '426c79ee-f86d-4b5a-9cef-63bf24bbd677'
     );

-- ── 3. Hard-delete orders (bypass soft-delete — load test data) ──────────
DELETE FROM orders
  WHERE outlet_id = '0465ade4-81d3-444b-bd4f-d5d0485263c4'
    AND notes LIKE 'batch30-load-%';

-- ── 4. Events pollution (ingredient deduction events, order events) ─────
DELETE FROM events
  WHERE tenant_id = '426c79ee-f86d-4b5a-9cef-63bf24bbd677'
    AND created_at >= NOW() - INTERVAL '4 hours'
    AND event_type IN ('order.created', 'order.cancelled', 'stock.deducted')
    AND (metadata->>'test_run' = 'batch-30-load'
      OR stream_id LIKE 'order:%' AND stream_id IN (
        SELECT 'order:' || id::text FROM orders WHERE notes LIKE 'batch30-load-%'
      ));

-- ── 5. Post-delete verification ─────────────────────────────────────────
SELECT
  (SELECT count(*) FROM orders WHERE outlet_id = '0465ade4-81d3-444b-bd4f-d5d0485263c4' AND notes LIKE 'batch30-load-%') AS orders_leftover,
  (SELECT count(*) FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE o.notes LIKE 'batch30-load-%') AS items_leftover,
  (SELECT count(*) FROM payments p JOIN orders o ON p.order_id = o.id WHERE o.notes LIKE 'batch30-load-%') AS payments_leftover;

-- Kalau hasil verifikasi semua 0 → commit. Kalau nonzero atau mau dry-run → ROLLBACK.
COMMIT;

-- ── Stock reset (optional — load test products start dari 999700+) ──────
-- Kalau mau reset stock_qty ke 999999 (pristine baseline), uncomment:
-- BEGIN;
-- SELECT set_config('app.current_tenant_id', '426c79ee-f86d-4b5a-9cef-63bf24bbd677', false);
-- UPDATE products
--   SET stock_qty = 999999, row_version = row_version + 1
--   WHERE brand_id IN (SELECT id FROM brands WHERE tenant_id = '426c79ee-f86d-4b5a-9cef-63bf24bbd677')
--     AND stock_enabled = true;
-- COMMIT;
