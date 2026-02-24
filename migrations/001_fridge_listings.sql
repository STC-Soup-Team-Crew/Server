-- ============================================================
-- Fridge Share: Community leftover sharing feature
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Create the fridge_listings table
CREATE TABLE IF NOT EXISTS fridge_listings (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         TEXT NOT NULL,
    user_display_name TEXT NOT NULL DEFAULT 'Anonymous',
    title           TEXT NOT NULL,
    description     TEXT,
    items           JSONB NOT NULL DEFAULT '[]'::JSONB,   -- e.g. ["3 tomatoes", "1 carton milk"]
    quantity        TEXT,                                  -- e.g. "enough for 2 meals"
    expiry_hint     TEXT,                                  -- e.g. "use within 2 days"
    pickup_instructions TEXT,
    image_url       TEXT,
    status          TEXT NOT NULL DEFAULT 'available'
                      CHECK (status IN ('available', 'claimed', 'deleted')),
    claimed_by      TEXT,
    claimed_by_name TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2. Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_fridge_listings_status
    ON fridge_listings (status);

CREATE INDEX IF NOT EXISTS idx_fridge_listings_user_id
    ON fridge_listings (user_id);

CREATE INDEX IF NOT EXISTS idx_fridge_listings_created_at
    ON fridge_listings (created_at DESC);

-- 3. Enable Row Level Security
ALTER TABLE fridge_listings ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies

-- Everyone can READ all non-deleted listings
CREATE POLICY "Anyone can view listings"
    ON fridge_listings
    FOR SELECT
    USING (status <> 'deleted');

-- Anyone can INSERT (API passes user_id in body)
CREATE POLICY "Anyone can create listings"
    ON fridge_listings
    FOR INSERT
    WITH CHECK (true);

-- Anyone can UPDATE (claims, etc. — backend validates ownership where needed)
CREATE POLICY "Anyone can update listings"
    ON fridge_listings
    FOR UPDATE
    USING (true);

-- NOTE: We use soft-delete (status = 'deleted') so no DELETE policy needed.
-- The Supabase service-role key bypasses RLS anyway for the backend.
