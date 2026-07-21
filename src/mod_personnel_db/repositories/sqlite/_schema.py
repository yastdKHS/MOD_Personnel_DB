"""SQLite物理スキーマ。docs/database/schema.md のDDLに対応する。

knowledge_items.provenance_source / .version は docs/api/models.md の
KnowledgeItemモデルが要求するがdocs/database/schema.mdのDDLには存在しない
列であり、実装時に発見した設計文書間の差分を埋めるため追加した
（非破壊的な列追加のため、docs/database/schema.md#Migration方針が
定める「通常のPRレビューで足りる」変更に該当する）。
"""

import sqlite3

_DDL = """
CREATE TABLE pdfs (
    id              INTEGER PRIMARY KEY,
    content_hash    TEXT NOT NULL UNIQUE,
    source_url      TEXT NOT NULL,
    published_date  TEXT NOT NULL,
    fetched_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    file_path       TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'fetched'
                        CHECK (status IN ('fetched', 'analyzed', 'parsed', 'validated', 'failed')),
    created_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_pdfs_published_date ON pdfs (published_date);
CREATE INDEX idx_pdfs_status ON pdfs (status);

CREATE TABLE layouts (
    id                INTEGER PRIMARY KEY,
    era_id            TEXT NOT NULL,
    version           INTEGER NOT NULL DEFAULT 1,
    manifest_path     TEXT NOT NULL,
    manifest_checksum TEXT NOT NULL,
    valid_from        TEXT NOT NULL,
    valid_to          TEXT,
    status            TEXT NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'deprecated')),
    created_at        TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (era_id, version)
);
CREATE INDEX idx_layouts_valid_from ON layouts (valid_from);
CREATE INDEX idx_layouts_status ON layouts (status);

CREATE TABLE parser_versions (
    id                          INTEGER PRIMARY KEY,
    code_version                TEXT NOT NULL UNIQUE,
    knowledge_snapshot_checksum TEXT NOT NULL,
    released_at                 TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    notes                       TEXT
);
CREATE INDEX idx_parser_versions_released_at ON parser_versions (released_at);

CREATE TABLE personnel_sections (
    id                INTEGER PRIMARY KEY,
    pdf_id            INTEGER NOT NULL REFERENCES pdfs (id),
    layout_id         INTEGER NOT NULL REFERENCES layouts (id),
    parser_version_id INTEGER NOT NULL REFERENCES parser_versions (id),
    section_index     INTEGER NOT NULL,
    section_label     TEXT,
    page_range        TEXT,
    section_text      TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'parsed'
                          CHECK (status IN ('parsed', 'superseded')),
    created_at        TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (pdf_id, section_index, parser_version_id)
);
CREATE INDEX idx_personnel_sections_pdf_id ON personnel_sections (pdf_id);
CREATE INDEX idx_personnel_sections_layout_id ON personnel_sections (layout_id);
CREATE INDEX idx_personnel_sections_parser_version_id ON personnel_sections (parser_version_id);
CREATE INDEX idx_personnel_sections_status ON personnel_sections (status);

CREATE TABLE candidate_records (
    id                     INTEGER PRIMARY KEY,
    personnel_section_id   INTEGER NOT NULL REFERENCES personnel_sections (id),
    parser_version_id      INTEGER NOT NULL REFERENCES parser_versions (id),
    record_index           INTEGER NOT NULL,
    raw_fields              TEXT NOT NULL CHECK (json_valid(raw_fields)),
    normalized_fields       TEXT
                                CHECK (normalized_fields IS NULL OR json_valid(normalized_fields)),
    normalization_applied   TEXT
                                CHECK (normalization_applied IS NULL
                                       OR json_valid(normalization_applied)),
    validation_status       TEXT NOT NULL DEFAULT 'pending'
                                 CHECK (validation_status IN ('pending', 'passed', 'failed')),
    created_at              TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (personnel_section_id, record_index, parser_version_id)
);
CREATE INDEX idx_candidate_records_section_id ON candidate_records (personnel_section_id);
CREATE INDEX idx_candidate_records_parser_version_id ON candidate_records (parser_version_id);
CREATE INDEX idx_candidate_records_validation_status ON candidate_records (validation_status);

CREATE TABLE gold_records (
    id                   INTEGER PRIMARY KEY,
    candidate_record_id  INTEGER NOT NULL REFERENCES candidate_records (id),
    person_key           TEXT NOT NULL,
    effective_date       TEXT NOT NULL,
    appointment_type     TEXT NOT NULL,
    fields                TEXT NOT NULL CHECK (json_valid(fields)),
    version               INTEGER NOT NULL DEFAULT 1,
    is_current            INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    superseded_by          INTEGER REFERENCES gold_records (id),
    valid_from              TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    valid_to                 TEXT,
    created_at                TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (person_key, effective_date, version)
);
CREATE INDEX idx_gold_records_person_key ON gold_records (person_key);
CREATE INDEX idx_gold_records_effective_date ON gold_records (effective_date);
CREATE INDEX idx_gold_records_current ON gold_records (person_key, is_current);
CREATE INDEX idx_gold_records_candidate_record_id ON gold_records (candidate_record_id);

CREATE TABLE review_sessions (
    id           INTEGER PRIMARY KEY,
    reviewer     TEXT NOT NULL,
    reason       TEXT NOT NULL,
    target_scope TEXT CHECK (target_scope IS NULL OR json_valid(target_scope)),
    status       TEXT NOT NULL DEFAULT 'in_progress'
                     CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at   TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT
);
CREATE INDEX idx_review_sessions_status ON review_sessions (status);
CREATE INDEX idx_review_sessions_started_at ON review_sessions (started_at);

CREATE TABLE review_changes (
    id                INTEGER PRIMARY KEY,
    review_session_id INTEGER NOT NULL REFERENCES review_sessions (id),
    target_table      TEXT NOT NULL CHECK (target_table IN ('candidate_records', 'gold_records')),
    target_id         INTEGER NOT NULL,
    field_name        TEXT NOT NULL,
    old_value         TEXT,
    new_value         TEXT NOT NULL,
    change_reason     TEXT,
    created_at        TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_review_changes_session_id ON review_changes (review_session_id);
CREATE INDEX idx_review_changes_target ON review_changes (target_table, target_id);

CREATE TABLE knowledge_items (
    id                 INTEGER PRIMARY KEY,
    category           TEXT NOT NULL CHECK (
                           category IN (
                               'organization', 'position', 'rank', 'alias',
                               'historical', 'typography', 'layout', 'validation'
                           )
                       ),
    source_file        TEXT NOT NULL,
    item_key           TEXT NOT NULL,
    canonical_value     TEXT NOT NULL,
    effective_from      TEXT,
    effective_to        TEXT,
    source_checksum      TEXT NOT NULL,
    provenance_source     TEXT NOT NULL,
    version                INTEGER NOT NULL DEFAULT 1,
    created_at              TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (category, item_key, effective_from)
);
CREATE INDEX idx_knowledge_items_category_key ON knowledge_items (category, item_key);
CREATE INDEX idx_knowledge_items_source_file ON knowledge_items (source_file);

CREATE TABLE learning_dataset (
    id                             INTEGER PRIMARY KEY,
    source_candidate_record_id     INTEGER REFERENCES candidate_records (id),
    source_review_change_id        INTEGER REFERENCES review_changes (id),
    pipeline_stage                 TEXT NOT NULL CHECK (
                                        pipeline_stage IN (
                                            'layout_detector', 'section_parser',
                                            'field_extractor', 'normalizer', 'validator'
                                        )
                                    ),
    error_category                 TEXT NOT NULL CHECK (
                                        error_category IN (
                                            'unknown_alias', 'unknown_layout',
                                            'knowledge_gap', 'layout_gap', 'true_exception'
                                        )
                                    ),
    field_name                     TEXT,
    wrong_value                    TEXT NOT NULL,
    correct_value                  TEXT,
    correction_summary             TEXT,
    reviewer_comment                TEXT,
    parser_version_id              INTEGER REFERENCES parser_versions (id),
    layout_id                      INTEGER REFERENCES layouts (id),
    confidence_score                REAL CHECK (
                                        confidence_score IS NULL
                                        OR (confidence_score >= 0 AND confidence_score <= 1)
                                    ),
    confidence_band                 TEXT CHECK (
                                        confidence_band IS NULL
                                        OR confidence_band IN ('verified', 'high', 'medium', 'low')
                                    ),
    status                          TEXT NOT NULL DEFAULT 'open'
                                        CHECK (
                                            status IN
                                                ('open', 'in_review', 'reflected',
                                                 'verified', 'wontfix')
                                        ),
    reflected_in_knowledge_item_id  INTEGER REFERENCES knowledge_items (id),
    reflected_in_layout_id          INTEGER REFERENCES layouts (id),
    git_commit_hash                 TEXT,
    pull_request_url                TEXT,
    regression_status               TEXT NOT NULL DEFAULT 'not_run'
                                        CHECK (
                                            regression_status IN ('not_run', 'passed', 'failed')
                                        ),
    regression_run_at               TEXT,
    regression_details              TEXT,
    improvement_candidate           TEXT,
    created_at                      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    resolved_at                     TEXT
);
CREATE INDEX idx_learning_dataset_status ON learning_dataset (status);
CREATE INDEX idx_learning_dataset_error_category ON learning_dataset (error_category);
CREATE INDEX idx_learning_dataset_pipeline_stage ON learning_dataset (pipeline_stage);
CREATE INDEX idx_learning_dataset_source_candidate_record_id
    ON learning_dataset (source_candidate_record_id);
CREATE INDEX idx_learning_dataset_parser_version_id ON learning_dataset (parser_version_id);
CREATE INDEX idx_learning_dataset_layout_id ON learning_dataset (layout_id);
CREATE INDEX idx_learning_dataset_regression_status ON learning_dataset (regression_status);

CREATE TABLE exports (
    id           INTEGER PRIMARY KEY,
    format       TEXT NOT NULL CHECK (format IN ('csv', 'parquet', 'json')),
    destination  TEXT NOT NULL,
    as_of        TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    checksum     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
    created_at   TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_exports_as_of ON exports (as_of);
CREATE INDEX idx_exports_status ON exports (status);

CREATE TABLE jobs (
    id                INTEGER PRIMARY KEY,
    job_type          TEXT NOT NULL CHECK (
                          job_type IN
                              ('fetch', 'core_pipeline', 'export', 'backfill', 'knowledge_reload')
                      ),
    pdf_id            INTEGER REFERENCES pdfs (id),
    parser_version_id INTEGER REFERENCES parser_versions (id),
    status            TEXT NOT NULL DEFAULT 'running'
                          CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at        TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at       TEXT,
    processed_count   INTEGER NOT NULL DEFAULT 0,
    failed_count      INTEGER NOT NULL DEFAULT 0,
    error_summary     TEXT
);
CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_jobs_job_type ON jobs (job_type);
CREATE INDEX idx_jobs_started_at ON jobs (started_at);
CREATE INDEX idx_jobs_pdf_id ON jobs (pdf_id);
"""


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_DDL)
    connection.commit()
