-- USER INDEXES

CREATE INDEX IF NOT EXISTS idx_users_firebase_uid
ON users(firebase_uid);


-- DOCUMENT INDEXES

CREATE INDEX IF NOT EXISTS idx_documents_user_id
ON documents(user_id);

CREATE INDEX IF NOT EXISTS idx_documents_status
ON documents(status);


-- CHUNK INDEXES

CREATE INDEX IF NOT EXISTS idx_chunks_user_id
ON document_chunks(user_id);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
ON document_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_user_document
ON document_chunks(user_id, document_id);