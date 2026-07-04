import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.export_dialog import ExportDialog

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_all_entity.return_value = {"entity_name": "Test Entity"}
    db.get_all_meta.return_value = {"entity_type": "COMPANY", "financial_year": "2024-25"}
    db.get_wtb.return_value = []
    return db

def test_export_dialog_init(tk_root, mock_db):
    dialog = ExportDialog(tk_root, mock_db)
    assert dialog.title() == "Export Financial Statements"
    assert dialog._do_pdf.get() is True
    assert dialog._do_xlsx.get() is True
    assert dialog._do_docx.get() is False

@patch('gui.export_dialog.filedialog')
def test_export_dialog_browse_folder(mock_fd, tk_root, mock_db):
    mock_fd.askdirectory.return_value = "/mock/export/folder"
    dialog = ExportDialog(tk_root, mock_db)
    dialog._browse_folder()
    assert dialog._folder_var.get() == "/mock/export/folder"

@patch('gui.export_dialog.threading.Thread')
def test_export_dialog_export_starts_thread(mock_thread, tk_root, mock_db):
    dialog = ExportDialog(tk_root, mock_db)
    dialog._export()
    mock_thread.assert_called_once()
    assert dialog._status_var.get() == "Preparing …"

@patch('gui.export_dialog.messagebox')
def test_export_dialog_export_validation(mock_msg, tk_root, mock_db):
    dialog = ExportDialog(tk_root, mock_db)
    dialog._do_pdf.set(False)
    dialog._do_xlsx.set(False)
    dialog._do_docx.set(False)
    dialog._export()
    mock_msg.showinfo.assert_called_once()
    assert "Select at least one format" in mock_msg.showinfo.call_args[0][1]
