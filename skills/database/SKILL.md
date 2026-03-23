# DATABASE SKILL

## Setiap tabel WAJIB punya:
id         UUID DEFAULT gen_random_uuid() PRIMARY KEY
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
deleted_at TIMESTAMPTZ  -- soft delete, nullable

## Naming
- Tabel: snake_case plural (orders, order_items)
- FK: {table_singular}_id
- Index: idx_{table}_{column}

## CRDT Fields (stok/inventory)
crdt_positive JSONB DEFAULT '{}'  -- {device_id: qty}
crdt_negative JSONB DEFAULT '{}'  -- {device_id: qty}
-- computed: sum(positive) - sum(negative)

## Event Store = APPEND ONLY
-- TIDAK BOLEH UPDATE atau DELETE
INSERT INTO events (stream_id, event_type, event_data, metadata)
-- stream_id: "order:uuid" atau "product:uuid"

## Migration
alembic revision --autogenerate -m "desc"
alembic upgrade head
