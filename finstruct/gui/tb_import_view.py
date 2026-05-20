"""Trial Balance import wizard — file picker, column mapping, preview."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from ..config import THEME as T
from ..core.tb_importer import import_xlsx, import_csv, import_tally_xml
from ..gui.theme import primary_btn, secondary_btn, label


class TBImportView(ttk.Frame):
    def __init__(self, parent, db, on_complete: callable = None):
        super().__init__(parent)
        self._db          = db
        self._on_complete = on_complete
        self._import_result = None
        self._path: Path | None = None
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        label(top, "2.  Import Trial Balance", style="Sec.TLabel").pack(side="left")

        # File picker
        pick = ttk.Frame(self)
        pick.pack(fill="x", padx=8, pady=4)
        label(pick, "Source File:").pack(side="left", padx=4)
        self._path_var = tk.StringVar()
        ttk.Entry(pick, textvariable=self._path_var, width=50,
                  state="readonly").pack(side="left", padx=4)
        secondary_btn(pick, "Browse …", command=self._browse).pack(side="left", padx=4)
        primary_btn(pick, "Import", command=self._do_import).pack(side="left", padx=8)

        # Status
        self._status_var = tk.StringVar(value="Select a file to import Trial Balance data.")
        ttk.Label(self, textvariable=self._status_var,
                  style="Muted.TLabel", wraplength=700).pack(fill="x", padx=8, pady=2)

        # Warnings/errors text
        self._msg = tk.Text(self, height=3, bg=T["bg"], fg=T["error"],
                            font=(T["font"], 9), relief="flat", state="disabled")
        self._msg.pack(fill="x", padx=8, pady=2)

        # Preview grid
        cols = [
            ("ledger", "Ledger Name",       220, "w"),
            ("group",  "Group",             140, "w"),
            ("dr",     "Debit",             100, "e"),
            ("cr",     "Credit",            100, "e"),
            ("net",    "Closing (CY)",      110, "e"),
            ("py",     "PY Net",            110, "e"),
            ("src",    "Source",             70, "center"),
        ]
        from .fs_grid_view import EditableGrid
        self._grid = EditableGrid(self, columns=cols)
        self._grid.pack(fill="both", expand=True, padx=8, pady=4)

        # Bottom bar
        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=8, pady=6)
        self._count_var = tk.StringVar(value="")
        ttk.Label(bot, textvariable=self._count_var,
                  style="Muted.TLabel").pack(side="left")
        primary_btn(bot, "✔ Confirm & Proceed  →", command=self._confirm).pack(side="right")
        secondary_btn(bot, "Clear / Re-import", command=self._clear).pack(side="right", padx=6)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Trial Balance File",
            filetypes=[
                ("All supported", "*.xlsx *.xls *.csv *.txt *.xml"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV / Text", "*.csv *.txt"),
                ("Tally XML", "*.xml"),
            ]
        )
        if path:
            self._path_var.set(path)
            self._path = Path(path)

    def _do_import(self):
        if not self._path or not self._path.exists():
            messagebox.showerror("Error", "Please select a valid file first.")
            return
        suffix = self._path.suffix.lower()
        try:
            if suffix in (".xlsx", ".xls"):
                result = import_xlsx(self._path)
            elif suffix in (".csv", ".txt"):
                result = import_csv(self._path)
            elif suffix == ".xml":
                result = import_tally_xml(self._path)
            else:
                messagebox.showerror("Unsupported", f"File type '{suffix}' not supported.")
                return
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            return

        self._import_result = result
        self._render(result)

    def _render(self, result):
        msgs = result.errors + result.warnings
        self._msg.configure(state="normal")
        self._msg.delete("1.0", "end")
        if msgs:
            self._msg.insert("end", "\n".join(msgs))
        self._msg.configure(state="disabled")

        grid_rows = []
        for i, row in enumerate(result.rows):
            grid_rows.append({
                "iid": str(i),
                "tag": "alt" if i % 2 else "",
                "values": [
                    row["ledger_name"], row["group_name"] or "",
                    f"{row['cy_debit']:,.2f}" if row["cy_debit"] else "—",
                    f"{row['cy_credit']:,.2f}" if row["cy_credit"] else "—",
                    f"{row['cy_net']:,.2f}"  if row["cy_net"]  else "—",
                    f"{row['py_net']:,.2f}"  if row["py_net"]  else "—",
                    row["source"],
                ],
            })
        self._grid.load_rows(grid_rows)
        n = len(result.rows)
        self._count_var.set(f"{n} ledger(s) detected  |  "
                            f"{'⚠ ' + str(len(result.warnings)) + ' warning(s)' if result.warnings else '✅ No warnings'}")
        self._status_var.set(
            f"Preview ready — {n} rows from '{self._path.name}'. "
            "Review and click Confirm.")

    def _confirm(self):
        if not self._import_result or not self._import_result.rows:
            messagebox.showerror("No Data", "No data to import. Please import a file first.")
            return
        if self._import_result.errors:
            if not messagebox.askyesno("Errors", "Import has errors. Proceed anyway?"):
                return
        self._db.clear_raw_tb()
        self._db.insert_raw_tb_batch(self._import_result.rows)
        self._db.log("TB_IMPORTED", f"{len(self._import_result.rows)} rows from {self._path.name}")
        messagebox.showinfo("Imported",
                            f"✅ {len(self._import_result.rows)} ledgers imported successfully.")
        if self._on_complete:
            self._on_complete()

    def _clear(self):
        self._import_result = None
        self._path = None
        self._path_var.set("")
        self._grid.load_rows([])
        self._count_var.set("")
        self._status_var.set("Select a file to import Trial Balance data.")
        self._msg.configure(state="normal")
        self._msg.delete("1.0", "end")
        self._msg.configure(state="disabled")
