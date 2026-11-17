
-- =====================================================
-- GCP RAG SYSTEM
-- Database schema: Cloud SQL PostgreSQL + pgvector
-- =====================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- 1. USERS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,

    subscription_tier VARCHAR(50)
        NOT NULL DEFAULT 'free',

    user_role VARCHAR(50)
        NOT NULL DEFAULT 'user',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =====================================================
-- 2. DOCUMENTS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,

    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(100) NOT NULL,

    storage_path TEXT NOT NULL,

    file_size BIGINT CHECK (file_size >= 0),

    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'processing',
                'completed',
                'failed',
                'deleting'
            )
        ),

    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Supports composite ownership reference from chunks.
    CONSTRAINT uq_documents_id_user UNIQUE (id, user_id)
);


-- =====================================================
-- 3. DOCUMENT CHUNKS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,

    document_id UUID NOT NULL,

    chunk_index INTEGER NOT NULL
        CHECK (chunk_index >= 0),

    content TEXT NOT NULL,

    -- Initial embedding dimension: 768
    embedding VECTOR(768) NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    content_hash CHAR(64),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_document_chunk
        UNIQUE (document_id, chunk_index),

    -- Ensures that the chunk's user owns its document.
    CONSTRAINT fk_chunk_document_owner
        FOREIGN KEY (document_id, user_id)
        REFERENCES documents(id, user_id)
        ON DELETE CASCADE
);


-- =====================================================
-- 4. RELATIONAL INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_documents_user_id
ON documents(user_id);

CREATE INDEX IF NOT EXISTS idx_documents_status
ON documents(status);

CREATE INDEX IF NOT EXISTS idx_chunks_user_id
ON document_chunks(user_id);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
ON document_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_user_document
ON document_chunks(user_id, document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_content_hash
ON document_chunks(document_id, content_hash);


-- =====================================================
-- 5. JSONB INDEX
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_chunks_metadata
ON document_chunks
USING GIN(metadata);


-- =====================================================
-- END OF SCHEMA
-- =====================================================
