import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.notes_view import NotesView
from core.notes_engine import Note
from core.fs_engine import FSLine

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_all_meta.return_value = {"financial_year": "2024-25"}
    return db

def test_notes_view_derive_fy_labels(tk_root, mock_db):
    view = NotesView(tk_root, [], mock_db)
    assert view._fy_labels == ("Rs. FY 2024-25", "Rs. FY 2023-24")

def test_notes_view_no_notes(tk_root, mock_db):
    view = NotesView(tk_root, [], mock_db)
    assert any("No notes generated yet" in w.cget("text") for w in view.winfo_children()[-1].winfo_children() if isinstance(w, (tk.ttk.Label, tk.Label)))

def test_notes_view_with_notes(tk_root, mock_db):
    note = Note(number=1, title="Test Note", lines=[FSLine(label="Item", cy=10, py=9, note=None, indent=0, row_type="ITEM")])
    view = NotesView(tk_root, [note], mock_db)
    assert 1 in view._grids
    assert len(view._note_frames) == 1

    note = Note(number=1, title="Test Note", lines=[FSLine(label="Item", cy=10, py=9, note=None, indent=0, row_type="ITEM")])
    view = NotesView(tk_root, [note], mock_db)
    
    # Mock connection
    mock_db._conn = MagicMock()
    
    view._save_all()
    mock_db._conn.execute.assert_called_once()
    mock_db._conn.commit.assert_called_once()
