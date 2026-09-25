import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.annexures_view import AnnexuresView
from core.annexures import AnnexureRow

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_sdb():
    db = MagicMock()
    db.get_annexure_tolerance.return_value = 10.0
    return db

@patch('gui.annexures_view.build_wtb_lines', return_value=[])
@patch('gui.annexures_view.aggregate_by_code', return_value={})
@patch('gui.annexures_view.load_annexure')
def test_annexures_view_init(mock_load, mock_agg, mock_build, tk_root, mock_db, mock_sdb):
    mock_annx = MagicMock()
    mock_annx.rows = []
    mock_annx.is_balanced = True
    mock_annx.variance_cy = 0.0
    mock_annx.variance_py = 0.0
    mock_annx.tb_total_cy = 0.0
    mock_annx.tb_total_py = 0.0
    mock_annx.tolerance = 10
    mock_load.return_value = mock_annx
    
    view = AnnexuresView(tk_root, mock_db, mock_sdb)
    
    assert view._tolerance == 10.0
    assert view._tol_var.get() == "10"
    
@patch('gui.annexures_view.build_wtb_lines', return_value=[])
@patch('gui.annexures_view.aggregate_by_code', return_value={})
@patch('gui.annexures_view.load_annexure')
def test_annexures_view_set_tolerance(mock_load, mock_agg, mock_build, tk_root, mock_db, mock_sdb):
    mock_annx = MagicMock()
    mock_annx.is_balanced = True
    mock_annx.variance_cy = 0.0
    mock_annx.variance_py = 0.0
    mock_annx.tb_total_cy = 0.0
    mock_annx.tb_total_py = 0.0
    mock_annx.tolerance = 0.0
    mock_load.return_value = mock_annx
    
    view = AnnexuresView(tk_root, mock_db, mock_sdb)
    view._tol_var.set("25.0")
    view._set_tolerance()
    mock_sdb.set_annexure_tolerance.assert_called_with(25.0)
    assert view._tolerance == 25.0

@patch('gui.annexures_view.messagebox')
@patch('gui.annexures_view.build_wtb_lines', return_value=[])
@patch('gui.annexures_view.aggregate_by_code', return_value={})
@patch('gui.annexures_view.save_annexure')
@patch('gui.annexures_view.load_annexure')
def test_annexures_view_save(mock_load, mock_save, mock_agg, mock_build, mock_msgbox, tk_root, mock_db, mock_sdb):
    mock_annx = MagicMock()
    mock_annx.is_balanced = True
    mock_annx.variance_cy = 0.0
    mock_annx.variance_py = 0.0
    mock_annx.tb_total_cy = 0.0
    mock_annx.tb_total_py = 0.0
    mock_annx.tolerance = 10.0
    mock_load.return_value = mock_annx
    
    view = AnnexuresView(tk_root, mock_db, mock_sdb)
    view._save()
    mock_save.assert_called_once()
    mock_msgbox.showinfo.assert_called_once()


@patch('gui.annexures_view.build_wtb_lines', return_value=[])
@patch('gui.annexures_view.aggregate_by_code', return_value={})
@patch('gui.annexures_view.load_annexure')
def test_annexures_view_navigation(mock_load, mock_agg, mock_build, tk_root, mock_db, mock_sdb):
    mock_annx = MagicMock()
    mock_annx.rows = []
    mock_annx.is_balanced = True
    mock_annx.variance_cy = 0.0
    mock_annx.variance_py = 0.0
    mock_annx.tb_total_cy = 0.0
    mock_annx.tb_total_py = 0.0
    mock_annx.tolerance = 10.0
    mock_load.return_value = mock_annx

    proceed_called = False
    back_called = False
    def on_proceed():
        nonlocal proceed_called
        proceed_called = True
    def on_back():
        nonlocal back_called
        back_called = True

    view = AnnexuresView(tk_root, mock_db, mock_sdb, on_proceed=on_proceed, on_back=on_back)
    view._proceed()
    assert proceed_called is True
    view._back()
    assert back_called is True


@patch('gui.annexures_view.messagebox')
@patch('tkinter.filedialog.askopenfilename', return_value="dummy_annexure.xlsx")
@patch('openpyxl.load_workbook')
@patch('gui.annexures_view.build_wtb_lines', return_value=[])
@patch('gui.annexures_view.aggregate_by_code', return_value={})
@patch('gui.annexures_view.load_annexure')
def test_annexures_view_import_excel(mock_load, mock_agg, mock_build, mock_wb_load, mock_ask, mock_msgbox, tk_root, mock_db, mock_sdb):
    row1 = AnnexureRow(label="Bucket A", cy_value=0.0, py_value=0.0)
    row2 = AnnexureRow(label="Bucket B", cy_value=0.0, py_value=0.0)
    mock_annx = MagicMock()
    mock_annx.rows = [row1, row2]
    mock_annx.is_balanced = True
    mock_annx.variance_cy = 0.0
    mock_annx.variance_py = 0.0
    mock_annx.tb_total_cy = 150.0
    mock_annx.tb_total_py = 250.0
    mock_annx.tolerance = 10.0
    mock_load.return_value = mock_annx

    # Mock openpyxl workbook
    mock_ws = MagicMock()
    mock_ws.iter_rows.return_value = [
        ("Bucket / Sub-Heading", "CY (₹)", "PY (₹)"),
        ("Bucket A", 100.0, 200.0),
        ("Bucket B", 50.0, 50.0),
    ]
    mock_wb = MagicMock()
    mock_wb.active = mock_ws
    mock_wb_load.return_value = mock_wb

    view = AnnexuresView(tk_root, mock_db, mock_sdb)
    view._import_excel()

    assert row1.cy_value == 100.0
    assert row1.py_value == 200.0
    assert row2.cy_value == 50.0
    assert row2.py_value == 50.0
    mock_msgbox.showinfo.assert_called_once()

