"""Notes to Accounts viewer — tabbed per-note editable grids."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from ..config import THEME as T
from ..core.notes_engine import Note
from ..core.fs_engine import FSLine
from ..gui.theme import label, primary_btn, secondary_btn
from .fs_grid_view import EditableGrid


def _fmt(v):
    if v is None or v == 0: return "-"
    return f"{float(v):,.2f}"


class NotesView(ttk.Frame):
    def __init__(self, parent, notes: list[Note], db):
        super().__init__(parent)
        self._notes = notes
        self._db    = db
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        label(top, "7.  Notes to Accounts", style="Sec.TLabel").pack(side="left")
        primary_btn(top, "Save All Note Edits", command=self._save_all).pack(side="right", padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        self._grids: dict[int, EditableGrid] = {}
        for note in self._notes:
            frame = ttk.Frame(nb)
            nb.add(frame, text=f"Note {note.number}")
            self._build_note_tab(frame, note)

    def _build_note_tab(self, parent, note: Note):
        ttk.Label(parent, text=f"Note {note.number}: {note.title}",
                  style="Sec.TLabel").pack(anchor="w", padx=8, pady=4)
        cols = [
            ("label", "Particulars",    360, "w"),
            ("cy",    "Current Year ₹", 150, "e"),
            ("py",    "Prev Year ₹",    150, "e"),
        ]
        grid = EditableGrid(parent, columns=cols,
                            on_cell_change=None,
                            editable_cols={"cy","py","label"})
        grid.pack(fill="both", expand=True, padx=8, pady=4)
        rows = []
        for i, ln in enumerate(note.lines):
            cy_s = _fmt(ln.cy) if ln.row_type not in ("SECTION","HEADER","BLANK","TEXT") else ""
            py_s = _fmt(ln.py) if ln.row_type not in ("SECTION","HEADER","BLANK","TEXT") else ""
            tag = {
                "TOTAL": "total", "GRAND": "grand",
                "SECTION": "section", "HEADER": "header",
                "TEXT": "alt",
            }.get(ln.row_type, "alt" if i % 2 else "")
            rows.append({
                "iid":    f"n{note.number}_{i}",
                "tag":    tag,
                "values": ["  " * ln.indent + ln.label, cy_s, py_s],
            })
        grid.load_rows(rows)
        self._grids[note.number] = grid

    def _save_all(self):
        for note in self._notes:
            grid = self._grids.get(note.number)
            if not grid:
                continue
            rows = grid.get_all_rows()
            for seq, (row, ln) in enumerate(zip(rows, note.lines)):
                try:
                    cy = float(str(row[1]).replace(",","")) if row[1] not in ("","-") else 0.0
                    py = float(str(row[2]).replace(",","")) if row[2] not in ("","-") else 0.0
                    lbl = str(row[0]).strip()
                    self._db._conn.execute("""
                        INSERT OR REPLACE INTO note_data(note_no,sequence,label,cy_value,py_value,row_type)
                        VALUES(?,?,?,?,?,?)
                    """, (note.number, seq, lbl, cy, py, ln.row_type))
                except (ValueError, IndexError):
                    pass
        self._db._conn.commit()
        from tkinter import messagebox
        messagebox.showinfo("Saved", "Notes saved successfully.")
