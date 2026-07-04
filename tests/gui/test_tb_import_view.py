import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from pathlib import Path
from gui.tb_import_view import TBImportView, ColumnMappingDialog

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

def test_tb_import_view_init(tk_root, mock_db):
    view = TBImportView(tk_root, mock_db)
    assert view._import_result is None
    assert view._path is None

@patch('gui.tb_import_view.filedialog')
def test_tb_import_view_browse(mock_fd, tk_root, mock_db):
    mock_fd.askopenfilename.return_value = "/mock/tb.xlsx"
    view = TBImportView(tk_root, mock_db)
    view._browse()
    assert view._path_var.get() == "/mock/tb.xlsx"
    assert view._path == Path("/mock/tb.xlsx")

@patch('gui.tb_import_view.messagebox')
def test_tb_import_view_do_import_no_file(mock_msgbox, tk_root, mock_db):
    view = TBImportView(tk_root, mock_db)
    view._do_import()
    mock_msgbox.showerror.assert_called_once()

def test_column_mapping_dialog(tk_root):
    headers = ["Name", "Amount"]
    preview = [["Sales", "100"], ["Rent", "50"]]
    auto_map = {"ledger": 0, "net": 1}
    
    dialog = ColumnMappingDialog(tk_root, headers, preview, auto_map)
    assert len(dialog._combos) == 2
    dialog._combos[0].set("Ledger Name")
    dialog._combos[1].set("Net Balance (CY)")
    
    # Confirm
    dialog._confirm()
    assert dialog.result is not None
