CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tripproof_source_units (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    page INTEGER NOT NULL,
    unit_index INTEGER NOT NULL,
    locator TEXT NOT NULL,
    text TEXT NOT NULL,
    search_text TEXT NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tripproof_source_embeddings (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL,
    source_unit_id TEXT NOT NULL REFERENCES tripproof_source_units(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding VECTOR(768),
    status TEXT NOT NULL CHECK (status IN ('pending', 'ready', 'failed')),
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS tripproof_source_units_material_idx
    ON tripproof_source_units (material_id, page, unit_index);

CREATE INDEX IF NOT EXISTS tripproof_source_embeddings_material_idx
    ON tripproof_source_embeddings (material_id);

CREATE INDEX IF NOT EXISTS tripproof_source_embeddings_source_unit_idx
    ON tripproof_source_embeddings (source_unit_id);

CREATE INDEX IF NOT EXISTS tripproof_source_embeddings_embedding_hnsw_idx
    ON tripproof_source_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WHERE status = 'ready' AND embedding IS NOT NULL;

CREATE OR REPLACE FUNCTION match_tripproof_source_units (
    query_embedding VECTOR(768),
    match_count INTEGER,
    p_material_ids TEXT[],
    similarity_threshold FLOAT DEFAULT 0.0
) RETURNS TABLE (
    source_unit_id TEXT,
    material_id TEXT,
    file_name TEXT,
    page INTEGER,
    unit_index INTEGER,
    locator TEXT,
    text TEXT,
    search_text TEXT,
    start_offset INTEGER,
    end_offset INTEGER,
    metadata JSONB,
    embedding_id TEXT,
    provider TEXT,
    model TEXT,
    dimensions INTEGER,
    similarity FLOAT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        su.id AS source_unit_id,
        su.material_id,
        su.file_name,
        su.page,
        su.unit_index,
        su.locator,
        su.text,
        su.search_text,
        su.start_offset,
        su.end_offset,
        su.metadata,
        se.id AS embedding_id,
        se.provider,
        se.model,
        se.dimensions,
        1 - (se.embedding <=> query_embedding) AS similarity
    FROM tripproof_source_embeddings AS se
    JOIN tripproof_source_units AS su ON su.id = se.source_unit_id
    WHERE
        su.material_id = ANY(p_material_ids)
        AND se.status = 'ready'
        AND se.embedding IS NOT NULL
        AND 1 - (se.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY se.embedding <=> query_embedding
    LIMIT match_count;
$$;
