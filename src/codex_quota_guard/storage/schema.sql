PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS epochs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    limit_id TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    reset_at TEXT,
    duration_minutes INTEGER,
    first_percent REAL NOT NULL,
    last_percent REAL NOT NULL,
    estimated_total REAL,
    confidence INTEGER,
    lower_bound REAL,
    upper_bound REAL,
    usage_unit TEXT NOT NULL DEFAULT 'unknown',
    completed INTEGER NOT NULL DEFAULT 0,
    reset_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_epochs_active
ON epochs(window_type, provider, completed);

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER NOT NULL REFERENCES epochs(id),
    timestamp TEXT NOT NULL,
    received_at TEXT,
    window_type TEXT NOT NULL,
    used_percent REAL NOT NULL,
    reset_at TEXT,
    duration_minutes INTEGER,
    cumulative_usage REAL,
    usage_unit TEXT NOT NULL,
    estimated_credits REAL,
    cost_usd REAL,
    input_tokens INTEGER,
    cached_input_tokens INTEGER,
    output_tokens INTEGER,
    model TEXT,
    provider TEXT NOT NULL,
    limit_id TEXT,
    source_signature TEXT,
    stale INTEGER NOT NULL DEFAULT 0,
    UNIQUE(epoch_id, timestamp, used_percent, cumulative_usage)
);

CREATE INDEX IF NOT EXISTS idx_samples_epoch_time
ON samples(epoch_id, timestamp);

CREATE TABLE IF NOT EXISTS epoch_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER NOT NULL REFERENCES epochs(id),
    calculated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    usage_unit TEXT NOT NULL,
    estimated_total REAL,
    estimated_used REAL,
    estimated_remaining REAL,
    lower_bound REAL,
    upper_bound REAL,
    confidence INTEGER NOT NULL,
    sample_count INTEGER NOT NULL,
    percent_span REAL NOT NULL,
    residual_mad REAL,
    warnings TEXT
);

CREATE INDEX IF NOT EXISTS idx_epoch_estimates_epoch_time
ON epoch_estimates(epoch_id, calculated_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER REFERENCES epochs(id),
    timestamp TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    cached_input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_credits REAL,
    cost_usd REAL,
    provider TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_health (
    provider TEXT PRIMARY KEY,
    last_success TEXT,
    last_failure TEXT,
    failure_class TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    backoff_until TEXT,
    status TEXT NOT NULL,
    error TEXT
);

PRAGMA user_version = 1;
