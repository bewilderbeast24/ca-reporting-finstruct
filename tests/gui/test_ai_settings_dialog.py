import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.ai_settings_dialog import AISettingsDialog

@pytest.fixture
def mock_sdb():
    db = MagicMock()
    db.get_ai_provider.return_value = "Claude"
    db.get_api_key.side_effect = lambda k: f"mock_key_{k}"
    return db

def test_ai_settings_dialog_init(tk_root, mock_sdb):
    dialog = AISettingsDialog(tk_root, mock_sdb)
    assert dialog.title() == "AI Assistance Settings"
    assert dialog._provider_var.get() == "Claude"
    assert dialog._claude_var.get() == "mock_key_Claude"
    assert dialog._openai_var.get() == "mock_key_OpenAI"
    assert dialog._gemini_var.get() == "mock_key_Gemini"

@patch('gui.ai_settings_dialog.messagebox')
def test_ai_settings_dialog_save(mock_msgbox, tk_root, mock_sdb):
    dialog = AISettingsDialog(tk_root, mock_sdb)
    dialog._provider_var.set("OpenAI")
    dialog._claude_var.set("new_claude")
    dialog._openai_var.set("new_openai")
    dialog._gemini_var.set("new_gemini")
    
    with patch.object(dialog, 'destroy') as mock_destroy:
        dialog._save()
        mock_sdb.set_ai_provider.assert_called_with("OpenAI")
        mock_sdb.set_api_key.assert_any_call("new_claude", "Claude")
        mock_sdb.set_api_key.assert_any_call("new_openai", "OpenAI")
        mock_sdb.set_api_key.assert_any_call("new_gemini", "Gemini")
        mock_msgbox.showinfo.assert_called_once()
        mock_destroy.assert_called_once()
