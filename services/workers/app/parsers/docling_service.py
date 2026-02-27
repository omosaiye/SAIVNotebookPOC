from __future__ import annotations

import csv
import io
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from services.workers.app.models import ParsedChunk, ParsedDocument
from services.workers.app.parsers.base import ParseRequest, ParserService


class DoclingFirstParserService(ParserService):
    def parse(self, request: ParseRequest) -> ParsedDocument:
        extension = Path(request.file_name).suffix.lower()
        if extension in {".csv"} or request.mime_type == "text/csv":
            return self._parse_csv(request)
        if extension in {".xlsx"}:
            return self._parse_xlsx(request)

        docling_result = self._try_docling(request)
        if docling_result is not None:
            return docling_result

        decoded = request.payload.decode("utf-8", errors="ignore")
        chunks = _split_to_chunks(decoded)
        return ParsedDocument(
            parser_used="text_fallback",
            content_type=request.mime_type,
            raw_text=decoded,
            chunks=chunks,
            metadata={"doclingAttempted": True, "doclingAvailable": False},
        )

    def _try_docling(self, request: ParseRequest) -> ParsedDocument | None:
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
        except Exception:
            return None

        converter = DocumentConverter()
        result = converter.convert_bytes(request.payload)
        markdown = result.document.export_to_markdown()
        chunks = _split_to_chunks(markdown)
        return ParsedDocument(
            parser_used="docling",
            content_type=request.mime_type,
            raw_text=markdown,
            chunks=chunks,
            metadata={
                "doclingAttempted": True,
                "doclingAvailable": True,
                "documentTitle": getattr(result.document, "title", None),
            },
        )

    def _parse_csv(self, request: ParseRequest) -> ParsedDocument:
        text = request.payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        chunks: list[ParsedChunk] = []
        for idx, row in enumerate(rows):
            rendered = ", ".join(f"{k}={v}" for k, v in row.items())
            chunks.append(
                ParsedChunk(
                    text=rendered,
                    ordinal=idx,
                    metadata={"rowIndex": idx, "row": row, "columns": reader.fieldnames or []},
                )
            )

        return ParsedDocument(
            parser_used="csv_structured",
            content_type=request.mime_type,
            raw_text=text,
            chunks=chunks,
            metadata={"rows": len(rows), "columns": reader.fieldnames or []},
        )

    def _parse_xlsx(self, request: ParseRequest) -> ParsedDocument:
        workbook_stream = io.BytesIO(request.payload)
        chunks: list[ParsedChunk] = []
        with ZipFile(workbook_stream) as archive:
            workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheets = workbook.findall("main:sheets/main:sheet", namespace)
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                sst = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared_strings = [
                    "".join(si.itertext()) for si in sst.findall("main:si", namespace)
                ]

            for sheet_index, sheet in enumerate(sheets, start=1):
                sheet_name = sheet.attrib.get("name", f"Sheet{sheet_index}")
                rel_id = sheet.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", ""
                )
                target_idx = (
                    int(rel_id.replace("rId", "")) if rel_id.startswith("rId") else sheet_index
                )
                sheet_path = f"xl/worksheets/sheet{target_idx}.xml"
                if sheet_path not in archive.namelist():
                    continue
                sheet_root = ElementTree.fromstring(archive.read(sheet_path))
                rows = sheet_root.findall("main:sheetData/main:row", namespace)
                for row_num, row in enumerate(rows, start=1):
                    values: list[str] = []
                    for cell in row.findall("main:c", namespace):
                        value = cell.find("main:v", namespace)
                        if value is None or value.text is None:
                            continue
                        raw = value.text
                        if (
                            cell.attrib.get("t") == "s"
                            and raw.isdigit()
                            and int(raw) < len(shared_strings)
                        ):
                            raw = shared_strings[int(raw)]
                        values.append(raw)
                    if values:
                        text = " | ".join(values)
                        chunks.append(
                            ParsedChunk(
                                text=text,
                                ordinal=len(chunks),
                                sheet_name=sheet_name,
                                metadata={
                                    "sheetName": sheet_name,
                                    "rowNumber": row_num,
                                    "values": values,
                                },
                            )
                        )

        raw_text = "\n".join(chunk.text for chunk in chunks)
        return ParsedDocument(
            parser_used="xlsx_structured",
            content_type=request.mime_type,
            raw_text=raw_text,
            chunks=chunks,
            metadata={"rowsExtracted": len(chunks)},
        )


def _split_to_chunks(text: str, size: int = 1200) -> list[ParsedChunk]:
    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[ParsedChunk] = []
    cursor = 0
    ordinal = 0
    while cursor < len(normalized):
        part = normalized[cursor : cursor + size]
        chunks.append(
            ParsedChunk(text=part, ordinal=ordinal, token_estimate=max(len(part) // 4, 1))
        )
        cursor += size
        ordinal += 1
    return chunks
