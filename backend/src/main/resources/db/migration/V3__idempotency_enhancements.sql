-- PulseCart V3 Migration: Customer-scoped idempotency, payload hashing, and cascade delete

-- 1. Drop existing global unique constraint and index on idempotency_key
ALTER TABLE idempotency_records DROP CONSTRAINT IF EXISTS idempotency_records_idempotency_key_key;
DROP INDEX IF EXISTS idx_idempotency_key;

-- 2. Add request_hash column to verify payload integrity and reject tampering
ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS request_hash VARCHAR(64) NOT NULL DEFAULT '';

-- 3. Scope idempotency key uniqueness to (user_id, idempotency_key)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_idempotency_user_key'
    ) THEN
        ALTER TABLE idempotency_records ADD CONSTRAINT uq_idempotency_user_key UNIQUE (user_id, idempotency_key);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_idempotency_user_key ON idempotency_records(user_id, idempotency_key);

-- 4. Recreate order_id foreign key with ON DELETE CASCADE to allow clean order deletions
ALTER TABLE idempotency_records DROP CONSTRAINT IF EXISTS idempotency_records_order_id_fkey;
ALTER TABLE idempotency_records ADD CONSTRAINT idempotency_records_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE;
