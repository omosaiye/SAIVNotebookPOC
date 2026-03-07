from __future__ import annotations

import io
from zipfile import ZipFile

from services.workers.app.parsers.base import ParseRequest
from services.workers.app.parsers.docling_service import DoclingFirstParserService


def test_csv_structured_extraction() -> None:
    parser = DoclingFirstParserService()
    payload = b"name,amount\nalpha,10\nbeta,20\n"

    result = parser.parse(
        ParseRequest(file_name="table.csv", mime_type="text/csv", payload=payload)
    )

    assert result.parser_used == "csv_structured"
    assert result.metadata["rows"] == 2
    assert result.chunks[0].metadata["row"]["name"] == "alpha"


def test_xlsx_structured_extraction() -> None:
    parser = DoclingFirstParserService()
    payload = _minimal_xlsx_payload()

    result = parser.parse(
        ParseRequest(
            file_name="table.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            payload=payload,
        )
    )

    assert result.parser_used == "xlsx_structured"
    assert result.chunks[0].sheet_name == "Sheet1"


def _minimal_xlsx_payload() -> bytes:
    workbook = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
      <sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>
    </workbook>"""
    worksheet = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
      <sheetData>
        <row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><v>Header</v></c></row>
      </sheetData>
    </worksheet>"""
    relationship_type = (
        "http://schemas.openxmlformats.org/officeDocument/"
        "2006/relationships/worksheet"
    )
    relations = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
      <Relationship Id=\"rId1\" Type=\"{relationship_type}\" Target=\"worksheets/sheet1.xml\"/>
    </Relationships>"""

    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
        archive.writestr("xl/_rels/workbook.xml.rels", relations)
    return stream.getvalue()
