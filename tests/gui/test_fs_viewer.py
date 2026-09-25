import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.fs_viewer import FSViewer
from core.fs_engine import FSDocument, FSLine

@pytest.fixture
def mock_db():
    return MagicMock()

def test_fs_viewer_init(tk_root, mock_db):
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    doc.bs = [FSLine(label="Assets", cy=100, py=90, note=None, indent=0, row_type="SECTION")]
    
    viewer = FSViewer(tk_root, doc, mock_db)
    
    assert viewer._include_cf.get() is True
    assert "bs" in viewer._grids
    assert len(viewer._nb.tabs()) > 0

@patch('gui.fs_viewer.messagebox')
def test_fs_viewer_save_overrides(mock_msgbox, tk_root, mock_db):
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    doc.bs = [FSLine(label="Assets", cy=100.0, py=90.0, note=None, indent=0, row_type="ITEM")]
    
    viewer = FSViewer(tk_root, doc, mock_db)
    
    # Mocking grid values
    grid = viewer._grids["bs"]
    # Update grid row with new values
    iid = "bs_0"
    grid.update_row(iid, ["Assets", "", "150.0", "90.0"])
    
    viewer._save_overrides()
    mock_db.set_override.assert_called_with("bs", "bs_0", 150.0, 90.0, "Manual edit")
    mock_msgbox.showinfo.assert_called_once()


def test_fs_viewer_navigation(tk_root, mock_db):
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    proceed_called = False
    back_called = False
    def on_proceed():
        nonlocal proceed_called
        proceed_called = True
    def on_back():
        nonlocal back_called
        back_called = True

    viewer = FSViewer(tk_root, doc, mock_db, on_proceed=on_proceed, on_back=on_back)
    viewer._go_notes()
    assert proceed_called is True
    viewer._back()
    assert back_called is True


@patch('gui.fs_viewer.messagebox')
def test_fs_viewer_revert_overrides(mock_msgbox, tk_root, mock_db):
    mock_msgbox.askyesno.return_value = True
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    doc.bs = [FSLine(label="Assets", cy=100.0, py=90.0, note=None, indent=0, row_type="ITEM")]

    viewer = FSViewer(tk_root, doc, mock_db)
    # Simulate a cell edit changing doc.bs[0].cy
    doc.bs[0].cy = 999.0
    grid = viewer._grids["bs"]
    grid.update_row("bs_0", ["Assets", "", "999.0", "90.0"])

    viewer._revert_overrides()

    mock_db.clear_overrides.assert_called_once()
    assert doc.bs[0].cy == 100.0
    mock_msgbox.showinfo.assert_called_once()


def test_fs_viewer_edit_signatories(tk_root, mock_db):
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    sig_called = False
    def on_edit_sig():
        nonlocal sig_called
        sig_called = True

    viewer = FSViewer(tk_root, doc, mock_db, on_edit_signatories=on_edit_sig)
    viewer._edit_signatories()
    assert sig_called is True

