import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.main_window import MainWindow

@patch('gui.main_window.SettingsDB')
def test_main_window_init(mock_settings, tk_root):
    mock_settings.instance.return_value = MagicMock()
    app = MainWindow(tk_root)
    assert app._db is None
    assert len(app._step_btns) == 10

@patch('gui.main_window.Dashboard')
@patch('gui.main_window.SettingsDB')
def test_main_window_show_dashboard(mock_settings, mock_dash, tk_root):
    app = MainWindow(tk_root)
    app._show_dashboard()
    assert mock_dash.call_count == 2

@patch('gui.main_window.ProjectDB')
@patch('gui.main_window.SettingsDB')
def test_main_window_open_db(mock_settings, mock_proj_db, tk_root):
    app = MainWindow(tk_root)
    
    mock_db_inst = MagicMock()
    mock_db_inst.get_entity.return_value = "Test Co"
    mock_db_inst.get_meta.side_effect = lambda k: "2024-25" if k == "financial_year" else "COMPANY"
    mock_proj_db.return_value = mock_db_inst
    
    from pathlib import Path
    app._open_db(Path("/mock/path.finstruct"))
    
    assert app._db is mock_db_inst
    assert app._status_var.get() == "Opened: path.finstruct"
    
@patch('gui.main_window.messagebox')
@patch('gui.main_window.SettingsDB')
def test_main_window_go_step_without_project(mock_settings, mock_msgbox, tk_root):
    app = MainWindow(tk_root)
    app._go_step(0)
    mock_msgbox.showinfo.assert_called_once()
    assert "open or create a project" in mock_msgbox.showinfo.call_args[0][1].lower()


@patch('gui.main_window.SettingsDB')
def test_main_window_step_navigation(mock_settings, tk_root):
    mock_settings.instance.return_value = MagicMock()
    app = MainWindow(tk_root)
    mock_db = MagicMock()
    mock_db.get_entity.return_value = "Test Co"
    mock_db.get_all_entity.return_value = {"entity_name": "Test Co"}
    mock_db.get_meta.return_value = "COMPANY"
    mock_db.get_all_meta.return_value = {"entity_type": "COMPANY", "financial_year": "2024-25"}
    mock_db.get_directors.return_value = []
    mock_db.get_raw_tb.return_value = []
    mock_db.get_wtb.return_value = []
    mock_db.get_adjustments.return_value = []
    mock_db.get_ppe.return_value = []
    mock_db.get_all_annexure_codes.return_value = []
    app._db = mock_db

    # Test navigating to Step 0 (Entity)
    with patch('gui.company_master.CompanyMasterForm') as mock_cmf:
        app._go_step(0)
        mock_cmf.assert_called_once()
        assert "on_proceed" in mock_cmf.call_args[1]

    # Test navigating to Step 1 (TB Import)
    with patch('gui.tb_import_view.TBImportView') as mock_tiv:
        app._go_step(1)
        mock_tiv.assert_called_once()
        assert "on_back" in mock_tiv.call_args[1]
        assert "on_complete" in mock_tiv.call_args[1]

    # Test navigating to Step 2 (Mapping)
    with patch('gui.mapping_view.MappingView') as mock_mv:
        app._go_step(2)
        mock_mv.assert_called_once()
        assert "on_back" in mock_mv.call_args[1]
        assert "on_complete" in mock_mv.call_args[1]

    # Test navigating to Step 3 (WTB)
    with patch('gui.wtb_view.WTBView') as mock_wv:
        app._go_step(3)
        mock_wv.assert_called_once()
        assert "on_back" in mock_wv.call_args[1]
        assert "on_proceed" in mock_wv.call_args[1]

    # Test navigating to Step 4 (PPE)
    with patch('gui.ppe_view.PPEView') as mock_pv:
        app._go_step(4)
        mock_pv.assert_called_once()
        assert "on_back" in mock_pv.call_args[1]
        assert "on_proceed" in mock_pv.call_args[1]

    # Test navigating to Step 5 (Annexures)
    with patch('gui.annexures_view.AnnexuresView') as mock_av:
        app._go_step(5)
        mock_av.assert_called_once()
        assert "on_back" in mock_av.call_args[1]
        assert "on_proceed" in mock_av.call_args[1]

