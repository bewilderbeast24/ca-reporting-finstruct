import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.mapping_view import MappingView

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_raw_tb.return_value = [
        {"id": 1, "ledger_name": "Sales", "group_name": "Revenue", "cy_net": 100, "py_net": 90}
    ]
    db.get_wtb.return_value = []
    return db

@pytest.fixture
def mock_sdb():
    return MagicMock()

@patch('gui.mapping_view.get_lookup_map', return_value={})
@patch('gui.mapping_view.get_group_tree', return_value={"Grp1": {"H1": ["S1"]}})
@patch('gui.mapping_view.threading.Thread')
def test_mapping_view_init(mock_thread, mock_tree, mock_lookup, tk_root, mock_db, mock_sdb):
    view = MappingView(tk_root, mock_db, mock_sdb, "COMPANY")
    
    assert view._status_var.get() == "Loading …"
    mock_thread.assert_called_once()

@patch('gui.mapping_view.get_lookup_map', return_value={})
@patch('gui.mapping_view.get_group_tree', return_value={"Grp1": {"H1": ["S1"]}})
@patch('gui.mapping_view.messagebox')
def test_mapping_view_confirm_all(mock_msgbox, mock_tree, mock_lookup, tk_root, mock_db, mock_sdb):
    # Overriding async load
    with patch('gui.mapping_view.threading.Thread'):
        view = MappingView(tk_root, mock_db, mock_sdb, "COMPANY")
        view._mapper = MagicMock()
        
    view._rows = [
        {"raw_tb_id": 1, "ledger": "Sales", "code": "", "conf": 0, "confirmed": False, "cy": 100.0, "py": 90.0, "source": "API", "group": "Income"}
    ]
    view._confirm_all()
    mock_msgbox.showerror.assert_called_once()
    assert "not mapped" in mock_msgbox.showerror.call_args[0][1]

    view._rows[0]["code"] = "PL001"
    complete_cb = MagicMock()
    view._on_complete = complete_cb
    view._confirm_all()
    assert view._rows[0]["confirmed"] is True
    complete_cb.assert_called_once()

@patch('gui.mapping_view.get_lookup_map', return_value={})
@patch('gui.mapping_view.get_group_tree', return_value={"Grp1": {"H1": ["S1"]}})
def test_mapping_view_back_navigation(mock_tree, mock_lookup, tk_root, mock_db, mock_sdb):
    back_cb = MagicMock()
    with patch('gui.mapping_view.threading.Thread'):
        view = MappingView(tk_root, mock_db, mock_sdb, "COMPANY", on_back=back_cb)
    view._back()
    back_cb.assert_called_once()

@patch('gui.mapping_view.get_lookup_map', return_value={})
@patch('gui.mapping_view.get_group_tree', return_value={"Grp1": {"H1": ["S1"]}})
def test_mapping_view_search_and_status_filter(mock_tree, mock_lookup, tk_root, mock_db, mock_sdb):
    with patch('gui.mapping_view.threading.Thread'):
        view = MappingView(tk_root, mock_db, mock_sdb, "COMPANY")
    view._rows = [
        {"raw_tb_id": 1, "ledger": "Sales A/c", "code": "PL001", "conf": 0.95, "confirmed": True, "cy": 100.0, "py": 90.0, "source": "API", "group": "Income"},
        {"raw_tb_id": 2, "ledger": "Rent Expense", "code": "", "conf": 0.0, "confirmed": False, "cy": 50.0, "py": 40.0, "source": "", "group": "Expense"}
    ]
    # Filter by search
    view._filter_search_var.set("Rent")
    assert "showing 1" in view._status_var.get()
    
    # Filter by status
    view._filter_search_var.set("")
    view._status_filter_var.set("Unresolved (Red)")
    view._render()
    assert "showing 1" in view._status_var.get()
