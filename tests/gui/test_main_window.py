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
