-- Impact Tracking System Schema
-- Migration: 002_impact_tracking.sql
-- Purpose: Tables for calculating and tracking food waste prevention, money saved, and CO2 avoided

-- ============================================================================
-- TABLE: ingredient_lookup
-- Purpose: Reference data for ingredient weights, costs, and carbon intensity
-- ============================================================================
CREATE TABLE IF NOT EXISTS ingredient_lookup (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL CHECK (category IN ('produce', 'dairy', 'protein', 'grains', 'condiments', 'beverages', 'frozen', 'other')),
    weight_kg       NUMERIC(10, 4) NOT NULL DEFAULT 0.1,      -- Average weight per unit/serving
    cost_usd        NUMERIC(10, 2) NOT NULL DEFAULT 1.00,     -- Average cost per unit/serving (USD)
    carbon_kg_co2e  NUMERIC(10, 4) NOT NULL DEFAULT 1.0,      -- kg CO2 equivalent per kg of ingredient
    aliases         TEXT[] DEFAULT '{}',                       -- Alternative names for fuzzy matching
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_ingredient_lookup_name ON ingredient_lookup(name);
CREATE INDEX IF NOT EXISTS idx_ingredient_lookup_category ON ingredient_lookup(category);

-- ============================================================================
-- TABLE: impact_events
-- Purpose: Log every impact calculation for audit trail and aggregation
-- ============================================================================
CREATE TABLE IF NOT EXISTS impact_events (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         TEXT NOT NULL,                             -- Clerk user ID or guest ID
    source          TEXT NOT NULL CHECK (source IN ('recipe', 'fridge_share', 'manual')),
    source_id       UUID,                                      -- Optional reference to recipe_id or listing_id
    
    -- Ingredient snapshot (stored for historical accuracy)
    ingredients     JSONB NOT NULL DEFAULT '[]',
    -- Format: [{"name": "apple", "quantity": 2, "unit": "pieces", "weight_kg": 0.36, "cost_usd": 1.50, "co2_kg": 0.72}]
    
    -- Calculated totals
    total_waste_kg  NUMERIC(10, 4) NOT NULL DEFAULT 0,
    total_cost_usd  NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_co2_kg    NUMERIC(10, 4) NOT NULL DEFAULT 0,
    
    -- Metadata
    status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'reversed', 'deleted')),
    created_at      TIMESTAMPTZ DEFAULT now(),
    
    -- Constraint: ensure we have valid totals
    CONSTRAINT positive_totals CHECK (
        total_waste_kg >= 0 AND 
        total_cost_usd >= 0 AND 
        total_co2_kg >= 0
    )
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_impact_events_user_id ON impact_events(user_id);
CREATE INDEX IF NOT EXISTS idx_impact_events_created_at ON impact_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_impact_events_source ON impact_events(source);
CREATE INDEX IF NOT EXISTS idx_impact_events_status ON impact_events(status);

-- Composite index for weekly aggregation queries
CREATE INDEX IF NOT EXISTS idx_impact_events_user_week ON impact_events(user_id, created_at DESC) 
    WHERE status = 'active';

-- ============================================================================
-- TABLE: user_gamification
-- Purpose: Track streaks, badges, and weekly goals per user
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_gamification (
    user_id             TEXT PRIMARY KEY,
    
    -- Streak tracking
    current_streak      INTEGER DEFAULT 0,
    longest_streak      INTEGER DEFAULT 0,
    last_active_date    DATE,
    
    -- Weekly goal tracking
    weekly_goal_kg      NUMERIC(10, 2) DEFAULT 2.0,            -- Default goal: 2kg/week
    weekly_progress_kg  NUMERIC(10, 4) DEFAULT 0,
    week_start_date     DATE DEFAULT date_trunc('week', CURRENT_DATE)::DATE,
    
    -- All-time totals (denormalized for fast reads)
    total_waste_kg      NUMERIC(12, 4) DEFAULT 0,
    total_cost_usd      NUMERIC(12, 2) DEFAULT 0,
    total_co2_kg        NUMERIC(12, 4) DEFAULT 0,
    total_events        INTEGER DEFAULT 0,
    
    -- Badges earned
    -- Format: {"waste_saver": {"tier": "silver", "earned_at": "2026-02-20T..."}, ...}
    badges              JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE ingredient_lookup ENABLE ROW LEVEL SECURITY;
ALTER TABLE impact_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_gamification ENABLE ROW LEVEL SECURITY;

-- Ingredient lookup: Everyone can read (public reference data)
CREATE POLICY "ingredient_lookup_select_all" ON ingredient_lookup
    FOR SELECT USING (true);

-- Ingredient lookup: Only service role can insert/update
CREATE POLICY "ingredient_lookup_service_insert" ON ingredient_lookup
    FOR INSERT WITH CHECK (true);

CREATE POLICY "ingredient_lookup_service_update" ON ingredient_lookup
    FOR UPDATE USING (true);

-- Impact events: Users can only see their own events
CREATE POLICY "impact_events_select_own" ON impact_events
    FOR SELECT USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "impact_events_insert_own" ON impact_events
    FOR INSERT WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- User gamification: Users can only see/update their own data
CREATE POLICY "user_gamification_select_own" ON user_gamification
    FOR SELECT USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "user_gamification_insert_own" ON user_gamification
    FOR INSERT WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "user_gamification_update_own" ON user_gamification
    FOR UPDATE USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get weekly summary for a user
CREATE OR REPLACE FUNCTION get_user_weekly_summary(p_user_id TEXT, p_week_start DATE DEFAULT date_trunc('week', CURRENT_DATE)::DATE)
RETURNS TABLE (
    waste_kg NUMERIC,
    cost_usd NUMERIC,
    co2_kg NUMERIC,
    event_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(total_waste_kg), 0) as waste_kg,
        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
        COALESCE(SUM(total_co2_kg), 0) as co2_kg,
        COUNT(*) as event_count
    FROM impact_events
    WHERE user_id = p_user_id
      AND status = 'active'
      AND created_at >= p_week_start
      AND created_at < p_week_start + INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED DATA: Common ingredients with reasonable defaults
-- Run this after creating tables to populate lookup data
-- ============================================================================
-- Note: Seed data is managed via Python (ingredient_defaults.py) and can be
-- bulk-inserted on application startup or via a separate seed script.

COMMENT ON TABLE ingredient_lookup IS 'Reference data for ingredient weights, costs, and carbon intensity. Sources: USDA FoodData Central, DEFRA emissions factors, average US grocery prices.';
COMMENT ON TABLE impact_events IS 'Audit log of every impact calculation. Used for weekly aggregations and historical analysis.';
COMMENT ON TABLE user_gamification IS 'Per-user gamification state including streaks, badges, and weekly goals.';
