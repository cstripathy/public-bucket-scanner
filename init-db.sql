-- Database initialization script
-- This will be executed when PostgreSQL container starts

-- Ensure the database exists (this runs as postgres user)
SELECT 'CREATE DATABASE bucket_scanner'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bucket_scanner')\gexec

-- Connect to the database
\c bucket_scanner

-- Create tables matching SQLAlchemy models
CREATE TABLE IF NOT EXISTS scan_results (
    id SERIAL PRIMARY KEY,
    bucket_name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    exists BOOLEAN DEFAULT FALSE,
    is_accessible BOOLEAN DEFAULT FALSE,
    access_level VARCHAR(50),
    url VARCHAR(500),
    permissions JSONB,
    files_found JSONB,
    sensitive_files JSONB,
    risk_level VARCHAR(20),
    risk_score INTEGER DEFAULT 0,
    error TEXT,
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(bucket_name, provider)
);

CREATE TABLE IF NOT EXISTS scan_tasks (
    id SERIAL PRIMARY KEY,
    bucket_name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    result_count INTEGER DEFAULT 0,
    error TEXT,
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    scan_result_id INTEGER,
    bucket_name VARCHAR(255) NOT NULL,
    provider VARCHAR(50),
    finding_type VARCHAR(100),
    severity VARCHAR(20),
    title VARCHAR(500),
    description TEXT,
    file_path VARCHAR(1000),
    url VARCHAR(500),
    recommendations JSONB,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (scan_result_id) REFERENCES scan_results(id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_scan_results_bucket ON scan_results(bucket_name);
CREATE INDEX IF NOT EXISTS idx_scan_results_is_accessible ON scan_results(is_accessible);
CREATE INDEX IF NOT EXISTS idx_scan_results_provider ON scan_results(provider);
CREATE INDEX IF NOT EXISTS idx_scan_results_risk ON scan_results(risk_level);
CREATE INDEX IF NOT EXISTS idx_scan_tasks_status ON scan_tasks(status);
CREATE INDEX IF NOT EXISTS idx_scan_tasks_priority ON scan_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_bucket ON findings(bucket_name);

-- Grant permissions to scanner user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scanner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scanner;
