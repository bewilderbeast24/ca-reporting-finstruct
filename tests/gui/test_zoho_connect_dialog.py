import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.zoho_connect_dialog import ZohoConnectDialog

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_meta.side_effect = lambda k: f"mock_{k}"
    return db

def test_zoho_connect_dialog_init(tk_root, mock_db):
    dialog = ZohoConnectDialog(tk_root, mock_db)
    assert dialog.title() == "Connect Zoho Books"
    assert dialog._vars["zoho_client_id"].get() == "mock_zoho_client_id"
    assert dialog._vars["zoho_client_secret"].get() == "mock_zoho_client_secret"
    assert dialog._vars["zoho_org_id"].get() == "mock_zoho_org_id"

@patch('gui.zoho_connect_dialog.messagebox')
def test_zoho_connect_dialog_save(mock_msgbox, tk_root, mock_db):
    dialog = ZohoConnectDialog(tk_root, mock_db)
    dialog._vars["zoho_client_id"].set("new_client_id")
    
    with patch.object(dialog, 'destroy') as mock_destroy:
        dialog._save()
        mock_db.set_meta.assert_any_call("zoho_client_id", "new_client_id")
        mock_msgbox.showinfo.assert_called_once()
        mock_destroy.assert_called_once()
