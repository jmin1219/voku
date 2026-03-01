-- Voku v2 Schema Migration
-- Created: 2026-02-28
-- Source: docs/SPEC.md five-table data model
--
-- Run against a fresh database. v1 database preserved as data/voku_v1.db.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Layer 1: Immutable Ground Truth
CREATE TABLE IF NOT EXISTS traces (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,           -- ISO 8601
    content         TEXT NOT NULL,           -- raw text, never modified
    conversation_id TEXT,                    -- groups traces into sessions
    parent_trace_id TEXT,                    -- threading within and across sessions
    source          TEXT NOT NULL,           -- 'user' | 'assistant' | 'resource' | 'system'
    FOREIGN KEY (parent_trace_id) REFERENCES traces(id)
);

-- Layer 2: Computed Annotations
CREATE TABLE IF NOT EXISTS annotations (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    type            TEXT NOT NULL,           -- free text: no predefined types
    key             TEXT,                    -- what was measured/committed/decided/felt
    value           TEXT,                    -- the extracted value
    confidence      REAL,
    extracted_at    TEXT NOT NULL,           -- ISO 8601
    extractor       TEXT NOT NULL,           -- model/version that produced this
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);

-- Layer 3: Relationships
CREATE TABLE IF NOT EXISTS connections (
    source_id       TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    type            TEXT NOT NULL,           -- 'semantic' | 'temporal' | 'intentional' | 'supersedes'
    weight          REAL,
    created_at      TEXT NOT NULL,           -- ISO 8601
    FOREIGN KEY (source_id) REFERENCES traces(id),
    FOREIGN KEY (target_id) REFERENCES traces(id),
    PRIMARY KEY (source_id, target_id, type)
);

-- Layer 4: External References
CREATE TABLE IF NOT EXISTS resources (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,           -- the trace where this was introduced
    type            TEXT NOT NULL,           -- 'paper' | 'transcript' | 'url' | 'file' | 'image'
    uri             TEXT,
    relationship    TEXT DEFAULT 'encountered',  -- 'encountered' | 'understood' | 'applied' | 'revised' | 'abandoned'
    summary         TEXT,                    -- LLM-generated on ingest
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);

-- Layer 5: Embeddings (separate for re-embedding)
CREATE TABLE IF NOT EXISTS embeddings (
    trace_id        TEXT PRIMARY KEY,
    model           TEXT NOT NULL,           -- 'bge-base-en-v1.5'
    vector          BLOB NOT NULL,
    computed_at     TEXT NOT NULL,           -- ISO 8601
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_traces_conversation ON traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp);
CREATE INDEX IF NOT EXISTS idx_traces_source ON traces(source);
CREATE INDEX IF NOT EXISTS idx_annotations_trace ON annotations(trace_id);
CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_id);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_id);
CREATE INDEX IF NOT EXISTS idx_resources_trace ON resources(trace_id);
