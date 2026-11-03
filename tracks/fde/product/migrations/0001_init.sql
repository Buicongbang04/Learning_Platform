-- quillo 1.0.0: tài liệu và các đoạn (chunk) kèm embedding 768 chiều (nomic-embed-text-v1.5).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          text PRIMARY KEY,
    filename    text NOT NULL,
    size_bytes  integer NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    doc_id     text NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk      integer NOT NULL,
    text       text NOT NULL,
    embedding  vector(768) NOT NULL,
    PRIMARY KEY (doc_id, chunk)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
