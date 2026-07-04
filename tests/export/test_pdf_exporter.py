import pytest
from unittest.mock import patch, MagicMock
from export.pdf_exporter import _fmt, _styles, _fs_table, _note_table, export_pdf

def test_fmt():
    assert _fmt(1234.567) == "1,234.57"
    assert _fmt(0) == "-"
    assert _fmt(None) == "-"
    assert _fmt(1234567.89) == "1,234,567.89"

@pytest.fixture
def mock_fs_line():
    line = MagicMock()
    line.row_type = "ITEM"
    line.label = "Test Item"
    line.cy = 1000
    line.py = 500
    line.indent = 0
    line.note = "1"
    return line

@pytest.fixture
def mock_fs_document(mock_fs_line):
    doc = MagicMock()
    doc.entity_master = {"entity_name": "Test PDF Corp"}
    doc.fy = "2024-25"
    doc.divisor = 1
    
    doc.bs = [mock_fs_line]
    doc.pl = [mock_fs_line]
    doc.ie = [mock_fs_line]
    doc.rp = [mock_fs_line]
    doc.cf = [mock_fs_line]
    return doc

@pytest.fixture
def mock_note():
    note = MagicMock()
    note.number = 1
    note.title = "Share Capital"
    line = MagicMock()
    line.row_type = "ITEM"
    line.label = "Equity"
    line.cy = 1000
    line.py = 500
    line.indent = 0
    note.lines = [line]
    return note

def test_styles():
    styles = _styles()
    assert "base" in styles
    assert "title" in styles
    assert "entity" in styles
    assert "sub" in styles
    assert "note" in styles
    assert "draft" in styles

def test_fs_table_all_row_types():
    lines = []
    for rt in ["BLANK", "HEADER", "SECTION", "TEXT", "GRAND", "TOTAL", "SUBTOTAL", "ITEM", "ITEM_ALT"]:
        line = MagicMock()
        line.row_type = "ITEM" if rt == "ITEM_ALT" else rt
        line.label = f"Label {rt}"
        line.cy = 100 if rt not in ["SECTION", "HEADER", "BLANK"] else None
        line.py = 50 if rt not in ["SECTION", "HEADER", "BLANK"] else None
        line.indent = 1
        line.note = "1" if "ITEM" in rt else ""
        lines.append(line)
        
    table = _fs_table(lines, "BS")
    assert table is not None

def test_note_table(mock_note):
    table = _note_table(mock_note)
    assert table is not None

@patch('export.pdf_exporter.SimpleDocTemplate')
def test_export_pdf_draft(mock_sdt_class, mock_fs_document, mock_note, tmp_path):
    mock_sdt = MagicMock()
    mock_sdt_class.return_value = mock_sdt
    
    output_path = tmp_path / "test_report.pdf"
    
    export_pdf(mock_fs_document, [mock_note], output_path, is_draft=True)
    
    mock_sdt_class.assert_called_once()
    mock_sdt.build.assert_called_once()

@patch('export.pdf_exporter.SimpleDocTemplate')
def test_export_pdf_final_with_db(mock_sdt_class, mock_fs_document, mock_note, tmp_path):
    mock_sdt = MagicMock()
    mock_sdt_class.return_value = mock_sdt
    
    mock_db = MagicMock()
    mock_db.get_directors.return_value = [
        {"name": "Dir 1", "is_signing_auth": True, "designation": "Director", "din": "123"},
        {"name": "Dir 2", "is_signing_auth": True, "designation": "Director", "din": "456"},
    ]
    
    output_path = tmp_path / "test_report_db.pdf"
    
    export_pdf(mock_fs_document, [mock_note], output_path, is_draft=False, db=mock_db)
    
    mock_sdt_class.assert_called_once()
    mock_sdt.build.assert_called_once()

@patch('export.pdf_exporter.SimpleDocTemplate')
def test_export_pdf_error_handling(mock_sdt_class, mock_fs_document, mock_note, tmp_path):
    mock_sdt = MagicMock()
    mock_sdt_class.return_value = mock_sdt
    
    mock_fs_document.fy = "InvalidFY"
    
    output_path = tmp_path / "test_report_err.pdf"
    export_pdf(mock_fs_document, [mock_note], output_path, is_draft=True)
    
    mock_sdt_class.assert_called_once()
    mock_sdt.build.assert_called_once()
