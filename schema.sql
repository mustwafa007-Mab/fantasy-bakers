-- Fantasy AI ERP Database Schema
-- Optimized for Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- MODULE 1: INVENTORY & SALES
CREATE TABLE inventory (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_name TEXT NOT NULL,
    quantity_kg DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    reorder_level_kg DECIMAL(10, 2) NOT NULL DEFAULT 10.00,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sales (
    sale_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID REFERENCES inventory(item_id),
    quantity_sold_kg DECIMAL(10, 2) NOT NULL,
    sale_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE procurement_orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID REFERENCES inventory(item_id),
    suggested_quantity_kg DECIMAL(10, 2) NOT NULL,
    status TEXT CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')) DEFAULT 'PENDING',
    approved_by_manager_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MODULE 2: SOCIAL PIPELINE
CREATE TABLE pending_posts (
    post_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_video_metadata JSONB, -- Stores info about the uploaded video
    generated_caption_swahili TEXT,
    generated_caption_english TEXT,
    hashtags TEXT[],
    status TEXT CHECK (status IN ('PENDING', 'APPROVED', 'PUBLISHED', 'REJECTED')) DEFAULT 'PENDING',
    approved_by_manager_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MODULE 3: LOGISTICS (TukTuk VRP)
CREATE TABLE tuktuks (
    tuktuk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    driver_name TEXT NOT NULL,
    current_location_gps POINT, -- PostGIS point could be used, but simple point for MVP
    status TEXT CHECK (status IN ('AVAILABLE', 'BUSY', 'MAINTENANCE')) DEFAULT 'AVAILABLE'
);

CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    phone_number TEXT, -- Will be masked in API
    location_gps POINT NOT NULL
);

CREATE TABLE deliveries (
    delivery_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tuktuk_id UUID REFERENCES tuktuks(tuktuk_id),
    customer_id UUID REFERENCES customers(customer_id),
    estimated_freshness_score INT,
    status TEXT CHECK (status IN ('PENDING', 'IN_TRANSIT', 'DELIVERED')) DEFAULT 'PENDING',
    delivery_time TIMESTAMPTZ
);

-- MODULE 4: SECURITY & COMPLIANCE (KEBS Audit Trail)
CREATE TABLE system_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL, -- e.g., 'STOCK_UPDATE', 'SECURITY_ALERT', 'ACCESS_ATTEMPT'
    description TEXT,
    actor_id UUID, -- Who performed the action (if known)
    affected_resource_id UUID, -- What was changed
    metadata JSONB, -- Before/After values
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE security_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    severity TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    message TEXT NOT NULL,
    odpc_report_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS (Row Level Security) Templates
-- Enable RLS on all tables
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE procurement_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Example Policy: Managers can view everything (Implementation would require auth setup)
-- CREATE POLICY "Managers can view all" ON inventory FOR SELECT USING (auth.role() = 'manager');
