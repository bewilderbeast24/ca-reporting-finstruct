"""Working Trial Balance review grid."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME as T
from gui.theme import primary_btn, secondary_btn, label
from core.wtb_engine import build_wtb_lines, aggregate_by_code, validate_balance
from gui.fs_grid_view import EditableGrid


class WTBView(ttk.Frame):
    def __init__(self, parent, db, on_proceed: callable = None, on_back: callable = None):
        super().__init__(parent)
        self._db = db
        self._on_proceed = on_proceed
        self._on_back = on_back
        self._build()
        self._load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        label(top, "4.  Working Trial Balance / Mapped TB", style="Sec.TLabel").pack(side="left")
        
        primary_btn(top, "✔ Proceed to PPE →", command=self._proceed).pack(side="right", padx=4)
        secondary_btn(top, "Validate F9", command=self._validate).pack(side="right", padx=4)
        secondary_btn(top, "← Back to Mapping", command=self._back).pack(side="right", padx=4)

        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var,
                  style="Muted.TLabel").pack(fill="x", padx=8)

        cols = [
            ("group",   "Group",            160, "w",      120, False),
            ("heading", "Heading",          200, "w",      150, False),
            ("ledger",  "Ledger Name",      220, "w",      180, False),
            ("code",    "Code",              70, "center",  60, False),
            ("cy",      "CY Net ₹",         120, "e",      100, False),
            ("py",      "PY Net ₹",         120, "e",      100, False),
            ("fs_tag",  "BS/PL/IE",          60, "center",  50, False),
        ]
        self._grid = EditableGrid(self, columns=cols,
                                  on_cell_change=None,
                                  editable_cols={"cy","py"})
        self._grid.pack(fill="both", expand=True, padx=8, pady=4)

        # Adjustment entries sub-view
        adj_frame = ttk.LabelFrame(self, text="Adjustment Entries")
        adj_frame.pack(fill="x", padx=8, pady=4)

        adj_top = ttk.Frame(adj_frame)
        adj_top.pack(fill="x", padx=6, pady=2)
        secondary_btn(adj_top, "➕ Add Adjustment Entry", command=self._add_adj).pack(side="left", padx=2)
        secondary_btn(adj_top, "🗑 Delete Selected Entry", command=self._delete_adj).pack(side="left", padx=4)

        tree_frame = ttk.Frame(adj_frame)
        tree_frame.pack(fill="x", expand=True, padx=6, pady=4)

        adj_cols = [
            ("id", "Entry ID", 110, "w",       90, False),
            ("ledger", "Ledger Name", 200, "w", 150, False),
            ("code", "Code", 70, "center",     60, False),
            ("dr", "Debit (₹)", 100, "e",      80, False),
            ("cr", "Credit (₹)", 100, "e",     80, False),
            ("narration", "Narration", 260, "w", 160, False),
        ]
        self._adj_tree = ttk.Treeview(tree_frame, columns=[c[0] for c in adj_cols], show="headings", height=4)
        for cid, chdr, cw, ca, cmw, cst in adj_cols:
            self._adj_tree.heading(cid, text=chdr)
            self._adj_tree.column(cid, width=cw, minwidth=cmw, anchor=ca, stretch=cst)
        adj_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._adj_tree.yview)
        self._adj_tree.configure(yscrollcommand=adj_vsb.set)
        self._adj_tree.pack(side="left", fill="x", expand=True)
        adj_vsb.pack(side="left", fill="y")

    def _load(self):
        try:
            wtb_rows = self._db.get_wtb()
            raw_rows = self._db.get_raw_tb()

            # Validate WTB has data
            if not raw_rows:
                self._grid.load_rows([])
                self._status_var.set("⚠ No Trial Balance data found. Please import TB first (Step 2).")
                for item in self._adj_tree.get_children():
                    self._adj_tree.delete(item)
                return

            lines    = build_wtb_lines(wtb_rows, raw_rows)
            from core.master_db import get_lookup_map
            lm = get_lookup_map()
            grid_rows = []
            seen_iids = set()
            for i, ln in enumerate(lines):
                e = lm.get(ln.mapping_code)
                group   = e.group    if e else (ln.group_name or "")
                heading = e.heading  if e else ""
                fs_tag  = e.fs_tag   if e else ""
                cy_s = f"{ln.cy_net:,.2f}" if ln.cy_net else "—"
                py_s = f"{ln.py_net:,.2f}" if ln.py_net else "—"
                tag = "alt" if i % 2 else ""
                row_iid = str(ln.wtb_id) if ln.wtb_id else f"r_{ln.raw_tb_id}"
                if row_iid in seen_iids:
                    row_iid = f"r_{ln.raw_tb_id}_{i}"
                seen_iids.add(row_iid)
                grid_rows.append({
                    "iid": row_iid,
                    "tag": tag,
                    "values": [group, heading, ln.ledger_name,
                               ln.mapping_code, cy_s, py_s, fs_tag],
                })
            self._grid.load_rows(grid_rows)

            # Show adjustments in treeview
            for item in self._adj_tree.get_children():
                self._adj_tree.delete(item)
            adjs = self._db.get_adjustments()
            for row in adjs:
                a = dict(row) if hasattr(row, "keys") else row
                dr = f"{a['dr_amount']:,.2f}" if a.get("dr_amount") else "—"
                cr = f"{a['cr_amount']:,.2f}" if a.get("cr_amount") else "—"
                self._adj_tree.insert("", "end", iid=str(a.get("id", "")), values=(
                    a.get("adj_id", ""), a.get("ledger_name", ""), a.get("mapping_code", "") or "",
                    dr, cr, a.get("narration", "") or ""
                ))

            # Balance
            totals = aggregate_by_code(lines)
            et = self._db.get_meta("entity_type") or "COMPANY"
            r  = validate_balance(totals, et)
            unmapped = sum(1 for ln in lines if not ln.mapping_code)
            unmapped_msg = f"  |  ⚠ {unmapped} unmapped" if unmapped else ""
            if r.ok:
                self._status_var.set(
                    f"✅ {len(lines)} ledgers  |  Balance Sheet balances  |  "
                    f"Total mapped codes: {len(totals)}{unmapped_msg}")
            else:
                self._status_var.set("⚠ " + " | ".join(r.errors + r.warnings) + unmapped_msg)
        except Exception as e:
            import traceback
            err_msg = f"Failed to load Working Trial Balance: {str(e)}"
            self._status_var.set(f"❌ {err_msg}")
            messagebox.showerror("System Error", 
                                f"{err_msg}\n\nTechnical details:\n{traceback.format_exc()}")

    def _validate(self):
        wtb_rows = self._db.get_wtb()
        raw_rows = self._db.get_raw_tb()
        lines    = build_wtb_lines(wtb_rows, raw_rows)
        totals   = aggregate_by_code(lines)
        et = self._db.get_meta("entity_type") or "COMPANY"
        r  = validate_balance(totals, et)
        if r.ok:
            messagebox.showinfo("✅ Balanced", "Balance Sheet balances correctly!")
        else:
            messagebox.showerror("Imbalance", "\n".join(r.errors + r.warnings))

    def _add_adj(self):
        AdjDialog(self, self._db, on_save=self._load)

    def _delete_adj(self):
        sel = self._adj_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select an adjustment entry to delete.")
            return
        adj_db_id = sel[0]
        if messagebox.askyesno("Delete", "Delete selected adjustment entry?"):
            self._db.delete_adjustment(adj_db_id)
            self._load()

    def _proceed(self):
        if self._on_proceed:
            self._on_proceed()

    def _back(self):
        if self._on_back:
            self._on_back()


class AdjDialog(tk.Toplevel):
    def __init__(self, parent, db, on_save: callable = None):
        super().__init__(parent)
        self._db = db
        self._on_save = on_save
        self.title("Add Adjustment Entry")
        self.geometry("520x350")
        self.grab_set()
        self.configure(bg=T["bg"])
        self._build()

    def _build(self):
        g = ttk.Frame(self, padding=16)
        g.pack(fill="both", expand=True)
        g.columnconfigure(1, weight=1)

        from core.master_db import get_lookup_map
        lm = get_lookup_map()
        code_choices = [f"{c} — {e.lookup_name}" for c, e in sorted(lm.items())]

        fields = [
            ("adj_id",    "Entry ID (auto)", False),
            ("ledger",    "Ledger Name",      False),
            ("code",      "Mapping Code",     True),
            ("dr",        "Debit Amount (₹)",  False),
            ("cr",        "Credit Amount (₹)", False),
            ("narration", "Narration",         False),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        import datetime
        adj_id = f"AJE-{datetime.datetime.now().strftime('%d%m%H%M')}"
        for i, (k, lbl, is_combo) in enumerate(fields):
            ttk.Label(g, text=lbl).grid(row=i, column=0, sticky="w", pady=4, padx=4)
            var = tk.StringVar(value=adj_id if k == "adj_id" else "")
            self._vars[k] = var
            if is_combo:
                cb = ttk.Combobox(g, textvariable=var, values=code_choices, width=34)
                cb.grid(row=i, column=1, sticky="ew", pady=4, padx=4)
            else:
                ttk.Entry(g, textvariable=var, width=36).grid(
                    row=i, column=1, sticky="ew", pady=4, padx=4)

        btn = ttk.Frame(g)
        btn.grid(row=len(fields), column=0, columnspan=2, pady=12)
        primary_btn(btn, "Save Entry", command=self._save).pack(side="left", padx=8)
        secondary_btn(btn, "Cancel", command=self.destroy).pack(side="left")

    def _save(self):
        v = {k: var.get().strip() for k, var in self._vars.items()}
        if not v["ledger"] or not v["code"]:
            messagebox.showerror("Error", "Ledger and Code are required."); return
        code = v["code"].split(" — ")[0].strip()
        try:
            dr = float(v["dr"] or 0)
            cr = float(v["cr"] or 0)
        except ValueError:
            messagebox.showerror("Error", "Dr/Cr must be numeric."); return
        self._db.add_adjustment(v["adj_id"], v["ledger"], code,
                                dr, cr, v["narration"])
        self.destroy()
        if self._on_save:
            self._on_save()
