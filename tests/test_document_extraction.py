import io

import pytest
from docx import Document as DocxDocument

from app.services.chunking import create_chunks
from app.services.extraction import (
    InvalidDocumentError,
    extract_document,
)


def test_extract_utf8_text_file():
    sections = extract_document(
        b"RAG stores document chunks and embeddings.",
        "notes.txt",
        "text/plain",
    )

    assert len(sections) == 1
    assert sections[0].text == "RAG stores document chunks and embeddings."
    assert sections[0].metadata == {"section": "text"}


def test_reject_pdf_without_pdf_signature():
    with pytest.raises(InvalidDocumentError, match="PDF signature"):
        extract_document(b"not a pdf", "notes.pdf", "application/pdf")


def test_extract_docx_paragraphs_and_tables():
    output = io.BytesIO()
    document = DocxDocument()
    document.add_paragraph("Document ingestion")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Value"
    document.save(output)

    sections = extract_document(
        output.getvalue(),
        "notes.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert len(sections) == 1
    assert "Document ingestion" in sections[0].text
    assert "Name: Value" in sections[0].text or "Name | Value" in sections[0].text


def test_csv_rows_are_grouped_to_reduce_embedding_requests():
    rows = ["name,score"]
    rows.extend(f"student-{index},{index}" for index in range(1, 22))
    sections = extract_document(
        "\n".join(rows).encode("utf-8"),
        "scores.csv",
        "text/csv",
    )

    assert len(sections) == 2
    assert sections[0].metadata == {"row_start": 2, "row_end": 21}
    assert sections[1].metadata == {"row_start": 22, "row_end": 22}


def test_chunking_preserves_source_metadata(monkeypatch):
    from app.core.config import settings
    from app.services.extraction import ExtractedSection

    monkeypatch.setattr(settings, "CHUNK_SIZE", 40)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP", 10)

    chunks = create_chunks([
        ExtractedSection(
            text="A sentence about retrieval. " * 8,
            metadata={"page": 4},
        )
    ])

    assert len(chunks) > 1
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata == {"page": 4} for chunk in chunks)
    assert all(chunk.content for chunk in chunks)
