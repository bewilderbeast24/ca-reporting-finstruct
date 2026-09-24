import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.report_editor import ReportEditor

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_all_entity.return_value = {"entity_name": "Test Co"}
    db.get_entity.return_value = "Test content"
    return db

def test_report_editor_init_directors(tk_root, mock_db):
    editor = ReportEditor(tk_root, mock_db, "directors")
    assert editor._type == "directors"
    text = editor.get_text()
    assert text == "Test content"

def test_report_editor_init_audit(tk_root, mock_db):
    editor = ReportEditor(tk_root, mock_db, "audit")
    assert editor._type == "audit"
    assert editor._opinion_var.get() == "Test content"  # get_entity mock returns this

def test_report_editor_save(tk_root, mock_db):
    editor = ReportEditor(tk_root, mock_db, "directors")
    editor._save()
    mock_db.set_entity.assert_called_with("directors_report_text", "Test content")

@patch('gui.report_editor.messagebox')
def test_report_editor_on_opinion_change(mock_msgbox, tk_root, mock_db):
    mock_msgbox.askyesno.return_value = True
    editor = ReportEditor(tk_root, mock_db, "audit")
    editor._opinion_var.set("Qualified")
    
    with patch.object(editor, '_reset') as mock_reset:
        editor._on_opinion_change()
        mock_db.set_entity.assert_called_with("opinion_type", "Qualified")
        mock_reset.assert_called_once()


@patch('gui.report_editor.messagebox')
def test_report_editor_reset_confirmation(mock_msgbox, tk_root, mock_db):
    mock_msgbox.askyesno.return_value = False
    editor = ReportEditor(tk_root, mock_db, "directors")
    editor._text.insert("1.0", "Custom text")
    editor._reset()
    # If askyesno returned False, text should not be reset to template
    assert "Custom text" in editor.get_text()

    mock_msgbox.askyesno.return_value = True
    editor._reset()
    assert editor._status_var.get() == "Template reset."


def test_report_editor_navigation(tk_root, mock_db):
    proceed_called = False
    back_called = False
    def on_proceed():
        nonlocal proceed_called
        proceed_called = True
    def on_back():
        nonlocal back_called
        back_called = True

    editor = ReportEditor(tk_root, mock_db, "directors", on_proceed=on_proceed, on_back=on_back)
    editor._proceed()
    assert proceed_called is True
    editor._back()
    assert back_called is True

