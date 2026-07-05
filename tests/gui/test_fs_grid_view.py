import pytest
import tkinter as tk
from unittest.mock import patch
from gui.fs_grid_view import EditableGrid

def test_editable_grid_init(tk_root):
    cols = [("col1", "Column 1", 100, "w"), ("col2", "Column 2", 100, "e")]
    grid = EditableGrid(tk_root, cols)
    assert grid.tree is not None
    assert len(grid.tree["columns"]) == 2
    assert grid.tree["columns"] == ("col1", "col2")

def test_editable_grid_load_rows(tk_root):
    cols = [("col1", "Column 1", 100, "w"), ("col2", "Column 2", 100, "e")]
    grid = EditableGrid(tk_root, cols)
    
    rows = [
        {"iid": "1", "values": ["A", "B"]},
        {"iid": "2", "values": ["C", "D"]}
    ]
    grid.load_rows(rows)
    
    all_rows = grid.get_all_rows()
    assert len(all_rows) == 2
    assert all_rows[0] == ["A", "B"]
    assert all_rows[1] == ["C", "D"]

def test_editable_grid_update_row(tk_root):
    cols = [("col1", "Column 1", 100, "w"), ("col2", "Column 2", 100, "e")]
    grid = EditableGrid(tk_root, cols)
    
    rows = [{"iid": "1", "values": ["A", "B"]}]
    grid.load_rows(rows)
    grid.update_row("1", ["X", "Y"])
    
    all_rows = grid.get_all_rows()
    assert all_rows[0] == ["X", "Y"]

def test_editable_grid_start_cancel_edit(tk_root):
    cols = [("col1", "Column 1", 100, "w"), ("col2", "Column 2", 100, "e")]
    grid = EditableGrid(tk_root, cols, editable_cols={"col1", "col2"})
    grid.load_rows([{"iid": "1", "values": ["A", "B"]}])
    
    with patch.object(grid._tree, 'bbox', return_value=(0, 0, 100, 20)):
        grid._start_edit("1", "col1", "#1")
    assert grid._edit_entry is not None
    assert grid._edit_entry.get() == "A"
    
    grid._cancel_edit()
    assert grid._edit_entry is None
