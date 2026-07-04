import pytest
from unittest.mock import patch, MagicMock
from export.xlsx_exporter import _fill, _font, _border, _write_fs_sheet, _write_note_sheet, export_xlsx

def test_styles_helpers():
    fill = _fill("FF000000")
    assert fill.__class__.__name__ == "PatternFill"
    assert fill.fill_type == "solid"
    
    font = _font(bold=True, white=True, sz=10)
    assert font.__class__.__name__ == "Font"
    assert font.bold is True
    assert font.size == 10
    
    border = _border()
    assert border.__class__.__name__ == "Border"
    assert border.top.style == "thin"

@pytest.fixture
def mock_fs_line():
    line = MagicMock()
    line.row_type = "ITEM"
    line.label = "Test Item"
    line.cy = 1000
    line.py = 500
    line.indent = 1
    line.note = "1"
    return line

@pytest.fixture
def mock_fs_document(mock_fs_line):
    doc = MagicMock()
    doc.entity_master = {"entity_name": "Test XLSX Corp"}
    doc.fy = "2024-25"
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

def test_write_fs_sheet_all_row_types():
    ws = MagicMock()
    em = {"entity_name": "Test Corp"}
    
    lines = []
    for rt in ["BLANK", "HEADER", "SECTION", "TEXT", "GRAND", "TOTAL", "SUBTOTAL", "ITEM", "ITEM_ALT"]:
        line = MagicMock()
        line.row_type = "ITEM" if rt == "ITEM_ALT" else rt
        line.label = f"Label {rt}"
        line.cy = 100 if rt not in ["SECTION", "HEADER", "BLANK", "TEXT"] else None
        line.py = 50 if rt not in ["SECTION", "HEADER", "BLANK", "TEXT"] else None
        line.indent = 1
        line.note = "1" if "ITEM" in rt else ""
        lines.append(line)
        
    _write_fs_sheet(ws, lines, "Balance Sheet", em, "2024-25")
    assert ws.append.call_count >= 5

def test_write_note_sheet_all_row_types(mock_note):
    ws = MagicMock()
    
    lines = []
    for rt in ["BLANK", "HEADER", "SECTION", "TEXT", "GRAND", "TOTAL", "SUBTOTAL", "ITEM", "ITEM_ALT"]:
        line = MagicMock()
        line.row_type = "ITEM" if rt == "ITEM_ALT" else rt
        line.label = f"Label {rt}"
        line.cy = 100 if rt not in ["SECTION", "HEADER", "BLANK", "TEXT"] else None
        line.py = 50 if rt not in ["SECTION", "HEADER", "BLANK", "TEXT"] else None
        line.indent = 1
        lines.append(line)
        
    mock_note.lines = lines
    _write_note_sheet(ws, mock_note)
    assert ws.append.call_count >= 3

@patch('export.xlsx_exporter.Workbook')
def test_export_xlsx(mock_wb_class, mock_fs_document, mock_note, tmp_path):
    mock_wb = MagicMock()
    mock_ws = MagicMock()
    mock_wb.active = mock_ws
    mock_wb.create_sheet.return_value = MagicMock()
    mock_wb_class.return_value = mock_wb
    
    output_path = tmp_path / "test_report.xlsx"
    
    export_xlsx(mock_fs_document, [mock_note], output_path)
    
    mock_wb_class.assert_called_once()
    # 1 active + 4 other sheets + 1 note
    assert mock_wb.create_sheet.call_count == 5
    mock_wb.save.assert_called_once_with(output_path)
    
@patch('export.xlsx_exporter.Workbook')
def test_export_xlsx_invalid_fy(mock_wb_class, mock_fs_document, mock_note, tmp_path):
    mock_fs_document.fy = "InvalidFY"
    
    mock_wb = MagicMock()
    mock_wb.active = MagicMock()
    mock_wb.create_sheet.return_value = MagicMock()
    mock_wb_class.return_value = mock_wb
    
    output_path = tmp_path / "test_report_err.xlsx"
    
    export_xlsx(mock_fs_document, [mock_note], output_path)
    
    mock_wb_class.assert_called_once()
    mock_wb.save.assert_called_once_with(output_path)
