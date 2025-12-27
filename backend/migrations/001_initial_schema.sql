-- Initial database schema migration
-- Creates all tables for signals, snapshots, events, watchlists, alerts, and audit logs

-- Signals table
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    market TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence TEXT NOT NULL,
    last_updated DATE NOT NULL,
    data_asof DATE NOT NULL,
    explanation TEXT NOT NULL,
    definition TEXT NOT NULL,
    source TEXT NOT NULL,
    key_driver TEXT NOT NULL,
    validity_window TEXT NOT NULL,
    decay_behavior TEXT NOT NULL,
    related_signal_ids TEXT,  -- JSON array
    related_markets TEXT,  -- JSON array
    signal_type TEXT NOT NULL,
    score REAL,
    confidence_rationale TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for signals
CREATE INDEX IF NOT EXISTS idx_signals_signal_id ON signals(signal_id);
CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(market);
CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_last_updated ON signals(last_updated);

-- Signal snapshots table
CREATE TABLE IF NOT EXISTS signal_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    signal_data TEXT NOT NULL,  -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);

-- Indexes for snapshots
CREATE INDEX IF NOT EXISTS idx_snapshots_signal_id ON signal_snapshots(signal_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON signal_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_signal_date ON signal_snapshots(signal_id, snapshot_date);

-- Regimes table
CREATE TABLE IF NOT EXISTS regimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime_date DATE NOT NULL UNIQUE,
    regime_type TEXT NOT NULL,
    description TEXT NOT NULL,
    usd_strength TEXT,
    rates_direction TEXT,
    growth_strength TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for regimes
CREATE INDEX IF NOT EXISTS idx_regimes_date ON regimes(regime_date);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    name TEXT NOT NULL,
    event_date DATE NOT NULL,
    description TEXT NOT NULL,
    impact_markets TEXT,  -- JSON array
    related_signal_ids TEXT,  -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for events
CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);

-- Watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    signal_ids TEXT,  -- JSON array
    market_ids TEXT,  -- JSON array
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE
);

-- Indexes for watchlists
CREATE INDEX IF NOT EXISTS idx_watchlists_watchlist_id ON watchlists(watchlist_id);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT UNIQUE NOT NULL,
    alert_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    conditions TEXT NOT NULL,  -- JSON
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at DATE DEFAULT CURRENT_DATE,
    last_triggered DATE
);

-- Indexes for alerts
CREATE INDEX IF NOT EXISTS idx_alerts_alert_id ON alerts(alert_id);
CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON alerts(enabled);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    old_value TEXT,  -- JSON
    new_value TEXT,  -- JSON
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_change_type ON audit_logs(change_type);
CREATE INDEX IF NOT EXISTS idx_audit_entity_id ON audit_logs(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity_type ON audit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);

