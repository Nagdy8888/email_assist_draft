-- Add created_at timestamp to LangGraph checkpoint tables (in email_assistant schema).
-- Run AFTER scripts/setup_db.py has created the checkpoint tables (cp.setup()).
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE checkpoint_migrations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoints           ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoint_blobs      ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoint_writes     ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
