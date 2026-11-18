
import uuid

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


# --------------------------------------------------
# USER MODEL
# --------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    firebase_uid: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(String, nullable=True)

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    subscription_tier: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'free'"),
    )

    user_role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'user'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="user",
        viewonly=True,
    )


# --------------------------------------------------
# DOCUMENT MODEL
# --------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "file_size >= 0",
            name="ck_documents_file_size",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', "
            "'completed', 'failed', 'deleting')",
            name="ck_documents_status",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_documents_id_user_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'pending'"),
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="documents",
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


# --------------------------------------------------
# DOCUMENT CHUNK MODEL
# --------------------------------------------------

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_document_chunks_chunk_index",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_index",
        ),
        ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            ondelete="CASCADE",
            name="fk_chunks_document_owner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    # "metadata" is reserved by SQLAlchemy's Declarative API.
    # Therefore, the Python attribute is called chunk_metadata,
    # while the actual PostgreSQL column remains "metadata".
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    content_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="chunks",
        viewonly=True,
    )

    document: Mapped["Document"] = relationship(
        back_populates="chunks",
    )