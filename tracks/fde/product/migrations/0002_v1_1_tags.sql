-- quillo 1.1.0: gắn nhãn (tags) cho tài liệu. Cột có DEFAULT nên bản 1.0.0 chạy lại trên schema này vẫn ghi được.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS documents_tags_idx ON documents USING gin (tags);
