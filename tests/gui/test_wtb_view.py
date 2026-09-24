import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.wtb_view import WTBView, AdjDialog

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_wtb.return_value = []
    db.get_raw_tb.return_value = [
        {"id": 1, "ledger_name": "Sales", "group_name": "Rev", "cy_net": -100, "py_net": -90}
    ]
    db.get_adjustments.return_value = []
    db.get_meta.return_value = "COMPANY"
    return db

@patch('gui.wtb_view.build_wtb_lines', return_value=[])
@patch('gui.wtb_view.aggregate_by_code', return_value={})
@patch('gui.wtb_view.validate_balance')
def test_wtb_view_init(mock_val, mock_agg, mock_build, tk_root, mock_db):
    mock_val.return_value = MagicMock(ok=True)
    view = WTBView(tk_root, mock_db)
    assert "✅" in view._status_var.get()

@patch('gui.wtb_view.messagebox')
@patch('gui.wtb_view.build_wtb_lines', return_value=[])
@patch('gui.wtb_view.aggregate_by_code', return_value={})
@patch('gui.wtb_view.validate_balance')
def test_wtb_view_validate(mock_val, mock_agg, mock_build, mock_msgbox, tk_root, mock_db):
    mock_val.return_value = MagicMock(ok=True)
    view = WTBView(tk_root, mock_db)
    view._validate()
    mock_msgbox.showinfo.assert_called_once()

def test_adj_dialog_save(tk_root, mock_db):
    dialog = AdjDialog(tk_root, mock_db)
    dialog._vars["ledger"].set("Rent")
    dialog._vars["code"].set("PL001 — Revenue from Operations")
    dialog._vars["dr"].set("100")
    
    with patch.object(dialog, 'destroy') as mock_destroy:
        dialog._save()
        mock_db.add_adjustment.assert_called_once()
        assert mock_db.add_adjustment.call_args[0][2] == "PL001"
        mock_destroy.assert_called_once()

@patch('gui.wtb_view.build_wtb_lines', return_value=[])
@patch('gui.wtb_view.aggregate_by_code', return_value={})
@patch('gui.wtb_view.validate_balance')
def test_wtb_view_back(mock_val, mock_agg, mock_build, tk_root, mock_db):
    back_cb = MagicMock()
    view = WTBView(tk_root, mock_db, on_back=back_cb)
    view._back()
    back_cb.assert_called_once()

@patch('gui.wtb_view.messagebox')
@patch('gui.wtb_view.build_wtb_lines', return_value=[])
@patch('gui.wtb_view.aggregate_by_code', return_value={})
@patch('gui.wtb_view.validate_balance')
def test_wtb_view_delete_adj(mock_val, mock_agg, mock_build, mock_msgbox, tk_root, mock_db):
    mock_msgbox.askyesno.return_value = True
    view = WTBView(tk_root, mock_db)
    view._adj_tree.insert("", "end", iid="42", values=("AJE-1", "Rent", "PL001", "100.00", "—", "Narration"))
    view._adj_tree.selection_set("42")
    view._delete_adj()
    mock_db.delete_adjustment.assert_called_with("42")
