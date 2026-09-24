import pytest
import sqlite3
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


@patch('gui.wtb_view.build_wtb_lines', return_value=[])
@patch('gui.wtb_view.aggregate_by_code', return_value={})
@patch('gui.wtb_view.validate_balance')
def test_wtb_view_load_with_sqlite_rows(mock_val, mock_agg, mock_build, tk_root):
    mock_val.return_value = MagicMock(ok=True)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adj_id TEXT,
            ledger_name TEXT,
            mapping_code TEXT,
            dr_amount REAL,
            cr_amount REAL,
            narration TEXT
        )
    """)
    con.execute("""
        INSERT INTO adjustments (adj_id, ledger_name, mapping_code, dr_amount, cr_amount, narration)
        VALUES ('AJE-1', 'Rent Expense', 'PL015', 5000.0, 0.0, 'Prepaid rent adjust')
    """)
    row = con.execute("SELECT * FROM adjustments").fetchone()
    assert isinstance(row, sqlite3.Row)

    db = MagicMock()
    db.get_wtb.return_value = []
    db.get_raw_tb.return_value = [
        {"id": 1, "ledger_name": "Sales", "group_name": "Rev", "cy_net": -100, "py_net": -90}
    ]
    db.get_adjustments.return_value = [row]
    db.get_meta.return_value = "COMPANY"

    view = WTBView(tk_root, db)
    assert "Failed" not in view._status_var.get()
    children = view._adj_tree.get_children()
    assert len(children) == 1
    vals = view._adj_tree.item(children[0], "values")
    assert vals[0] == "AJE-1"
    assert vals[1] == "Rent Expense"
    assert vals[2] == "PL015"
    assert "5,000.00" in vals[3]
    assert vals[5] == "Prepaid rent adjust"


def test_wtb_view_displays_mapped_trial_balance(tk_root):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE raw_tb (
            id INTEGER PRIMARY KEY, ledger_name TEXT, group_name TEXT,
            cy_debit REAL, cy_credit REAL, cy_net REAL, py_net REAL, source TEXT
        )
    """)
    con.execute("""
        CREATE TABLE wtb (
            id INTEGER PRIMARY KEY, raw_tb_id INTEGER, mapping_code TEXT,
            confidence REAL, confidence_source TEXT, cy_net REAL, py_net REAL, is_confirmed INTEGER
        )
    """)
    con.execute("INSERT INTO raw_tb VALUES (1, 'Equity Capital', 'Share Capital', 0, 50000, -50000, -50000, 'EXCEL')")
    con.execute("INSERT INTO wtb VALUES (10, 1, 'CO_EL001', 1.0, 'MANUAL', -50000, -50000, 1)")

    db = MagicMock()
    db.get_wtb.return_value = con.execute("SELECT * FROM wtb").fetchall()
    db.get_raw_tb.return_value = con.execute("SELECT * FROM raw_tb").fetchall()
    db.get_adjustments.return_value = []
    db.get_meta.return_value = "COMPANY"

    view = WTBView(tk_root, db)
    rows = view._grid.get_all_rows()
    assert len(rows) == 1
    # Check [group, heading, ledger_name, mapping_code, cy_s, py_s, fs_tag]
    assert rows[0][0] == "Shareholders Funds"
    assert rows[0][1] == "Share Capital"
    assert rows[0][2] == "Equity Capital"
    assert rows[0][3] == "CO_EL001"
    assert "-50,000.00" in rows[0][4]
    assert rows[0][6] == "BS"


