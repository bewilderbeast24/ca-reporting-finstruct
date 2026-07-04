import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from pathlib import Path
from gui.dashboard import Dashboard, NewProjectDialog

@pytest.fixture
def mock_sdb():
    db = MagicMock()
    db.get_recent.return_value = [
        {"path": "/mock/path1.finstruct", "entity_name": "Entity 1", "entity_type": "COMPANY", "fy": "2024-25", "last_opened": "2024-01-01T12:00:00"}
    ]
    return db

def test_dashboard_init_and_refresh(tk_root, mock_sdb):
    open_cb = MagicMock()
    dash = Dashboard(tk_root, mock_sdb, open_cb)
    assert "/mock/path1.finstruct" in dash._row_widgets

def test_dashboard_select_recent(tk_root, mock_sdb):
    dash = Dashboard(tk_root, mock_sdb, MagicMock())
    dash._select_recent("/mock/path1.finstruct")
    assert dash._selected_path == "/mock/path1.finstruct"

@patch('gui.dashboard.Path.exists', return_value=True)
def test_dashboard_open_path(mock_exists, tk_root, mock_sdb):
    open_cb = MagicMock()
    dash = Dashboard(tk_root, mock_sdb, open_cb)
    dash._open_path("/mock/path1.finstruct")
    open_cb.assert_called_once()
    assert open_cb.call_args[0][0].name == "path1.finstruct"

@patch('gui.dashboard.filedialog')
def test_dashboard_browse_open(mock_fd, tk_root, mock_sdb):
    mock_fd.askopenfilename.return_value = "/mock/path_browse.finstruct"
    open_cb = MagicMock()
    dash = Dashboard(tk_root, mock_sdb, open_cb)
    dash._browse_open()
    open_cb.assert_called_once()
    assert open_cb.call_args[0][0].name == "path_browse.finstruct"

def test_dashboard_remove_recent(tk_root, mock_sdb):
    dash = Dashboard(tk_root, mock_sdb, MagicMock())
    dash._selected_path = "/mock/path1.finstruct"
    dash._remove_recent()
    mock_sdb.remove_recent.assert_called_with("/mock/path1.finstruct")

@patch('gui.dashboard.messagebox')
def test_new_project_dialog(mock_msgbox, tk_root, mock_sdb):
    create_cb = MagicMock()
    dialog = NewProjectDialog(tk_root, mock_sdb, create_cb)
    dialog._name_var.set("Test Company")
    dialog._fy_var.set("2024-25")
    dialog._etype_var.set("Company")
    
    dialog._create()
    create_cb.assert_called_once()
