from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from typing import Any

import fitz
from docx import Document as DocxDocument


MAX_PDF_PAGES = 1000
MAX_CSV_ROWS = 100_000
CSV_ROWS_PER_SECTION = 20
MAX_DOCX_ENTRIES = 5_000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


class InvalidDocumentError(ValueError):
    """Raised when an uploaded file is invalid or cannot be safely parsed."""


@dataclass
class ExtractedSection:
    text: str
    metadata: dict[str, Any]


def _validate_docx(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = {item.filename for item in entries}
            if len(entries) > MAX_DOCX_ENTRIES:
                raise InvalidDocumentError("DOCX contains too many archive entries.")
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise InvalidDocumentError("The uploaded file is not a valid DOCX document.")
            if sum(item.file_size for item in entries) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise InvalidDocumentError("DOCX expands beyond the allowed size.")
            if any(item.file_size > 0 and item.compress_size == 0 for item in entries):
                raise InvalidDocumentError("DOCX contains an invalid compressed entry.")
            if any(
                item.compress_size > 0 and item.file_size / item.compress_size > 200
                for item in entries
            ):
                raise InvalidDocumentError("DOCX has an unsafe compression ratio.")
    except zipfile.BadZipFile as exc:
        raise InvalidDocumentError("The uploaded file is not a valid DOCX archive.") from exc


def extract_document(
    data: bytes,
    file_name: str,
    content_type: str,
) -> list[ExtractedSection]:
    suffix = file_name.lower().rsplit(".", 1)[-1]

    if suffix == "pdf" and content_type == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise InvalidDocumentError("The uploaded file does not have a valid PDF signature.")
        try:
            with fitz.open(stream=data, filetype="pdf") as pdf:
                if pdf.is_encrypted:
                    raise InvalidDocumentError("Password-protected PDFs are not supported.")
                if pdf.page_count > MAX_PDF_PAGES:
                    raise InvalidDocumentError("PDF exceeds the maximum page count.")
                sections = []
                for index, page in enumerate(pdf):
                    page_text = page.get_text("text").strip()
                    if page_text:
                        sections.append(
                            ExtractedSection(
                                text=page_text,
                                metadata={"page": index + 1},
                            )
                        )
                return sections
        except InvalidDocumentError:
            raise
        except Exception as exc:
            raise InvalidDocumentError("Could not parse the uploaded PDF.") from exc

    if (
        suffix == "docx"
        and content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        _validate_docx(data)
        try:
            document = DocxDocument(io.BytesIO(data))
            parts = [
                paragraph.text.strip()
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            for table in document.tables:
                for row in table.rows:
                    values = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    if any(values):
                        parts.append(" | ".join(values))
            text = "\n".join(parts).strip()
            return [ExtractedSection(text=text, metadata={"section": "document"})] if text else []
        except Exception as exc:
            raise InvalidDocumentError("Could not parse the uploaded DOCX file.") from exc

    if suffix == "txt" and content_type == "text/plain":
        try:
            text = data.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise InvalidDocumentError("TXT files must use UTF-8 encoding.") from exc
        return [ExtractedSection(text=text, metadata={"section": "text"})] if text else []

    if suffix == "csv" and content_type in {"text/csv", "application/csv"}:
        try:
            decoded = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidDocumentError("CSV files must use UTF-8 encoding.") from exc

        try:
            sample = decoded[:8192]
            try:
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
            except csv.Error:
                dialect = csv.excel

            rows = csv.reader(io.StringIO(decoded), dialect)
            headers = next(rows, [])
            sections: list[ExtractedSection] = []
            pending_lines: list[str] = []
            row_start: int | None = None
            row_end: int | None = None

            for row_number, row in enumerate(rows, start=2):
                if row_number > MAX_CSV_ROWS + 1:
                    raise InvalidDocumentError("CSV exceeds the maximum row count.")
                if not row or not any(cell.strip() for cell in row):
                    continue

                if headers and len(headers) == len(row):
                    line = " | ".join(
                        f"{header.strip()}: {value.strip()}"
                        for header, value in zip(headers, row)
                    )
                else:
                    line = " | ".join(cell.strip() for cell in row)

                if row_start is None:
                    row_start = row_number
                row_end = row_number
                pending_lines.append(line)

                if len(pending_lines) >= CSV_ROWS_PER_SECTION:
                    sections.append(
                        ExtractedSection(
                            text="\n".join(pending_lines),
                            metadata={"row_start": row_start, "row_end": row_end},
                        )
                    )
                    pending_lines = []
                    row_start = None

            if pending_lines:
                sections.append(
                    ExtractedSection(
                        text="\n".join(pending_lines),
                        metadata={"row_start": row_start, "row_end": row_end},
                    )
                )

            if not sections and headers:
                sections.append(
                    ExtractedSection(text=" | ".join(headers), metadata={"row": 1})
                )
            return sections
        except InvalidDocumentError:
            raise
        except csv.Error as exc:
            raise InvalidDocumentError("Could not parse the uploaded CSV file.") from exc

    raise InvalidDocumentError("File extension and content type are not supported together.")
