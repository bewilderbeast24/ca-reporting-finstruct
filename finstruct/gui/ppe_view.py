"""PPE Register GUI — asset grid + depreciation computation."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from ..config import THEME as T, PPE_CATEGORIES
from ..core.ppe_engine import recalc_asset, summarize_ppe
from ..gui.theme import primary_btn, secondary_btn, label
from .fs_grid_view import EditableGrid


class PPEView(ttk.Frame):
    def __init__(self, parent, db, on_dep_posted: callable = None):
        super().__init__(parent)
        self._db          = db
        self._on_dep_posted = on_dep_posted
        self._build()
        self._load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        label(top, "5.  PPE / Fixed Asset Register", style="Sec.TLabel").pack(side="left")
        primary_btn(top, "+ Add Asset", command=self._add_asset).pack(side="left", padx=8)
        secondary_btn(top, "Recalculate All", command=self._recalc_all).pack(side="left", padx=4)
        secondary_btn(top, "Post Depreciation to WTB", command=self._post_dep).pack(side="left", padx=4)
        secondary_btn(top, "Delete Selected", command=self._delete_asset).pack(side="left", padx=4)

        cols = [
            ("asset",    "Asset Description",   200, "w"),
            ("cat",      "Category",             140, "w"),
            ("method",   "Method",                60, "center"),
            ("life",     "Life (Yrs)",             65, "center"),
            ("gross_op", "Gross Blk Op",          100, "e"),
            ("adds",     "Additions",              100, "e"),
            ("disp",     "Disposals",              90, "e"),
            ("gross_cl", "Gross Blk Cl",           100, "e"),
            ("dep_op",   "Acc Dep Op",             100, "e"),
            ("dep_ch",   "Dep Charge",             100, "e"),
            ("dep_cl",   "Acc Dep Cl",             100, "e"),
            ("nbv_cy",   "Net Block CY",           100, "e"),
            ("nbv_py",   "Net Block PY",           100, "e"),
            ("it_dep",   "IT Dep",                  80, "e"),
        ]
        self._grid = EditableGrid(
            self, columns=cols,
            on_cell_change=self._on_change,
            editable_cols={"asset","cat","method","life","gross_op",
                           "adds","disp","dep_op","dep_ch","dep_cl","nbv_py","it_dep"}
        )
        self._grid.pack(fill="both", expand=True, padx=8, pady=4)

        # Totals bar
        self._tot_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._tot_var,
                  style="Muted.TLabel").pack(fill="x", padx=8, pady=2)

    def _load(self):
        rows_db = self._db.get_ppe()
        self._assets = []
        grid_rows = []
        for i, a in enumerate(rows_db):
            d = dict(a)
            r = recalc_asset(d)
            self._assets.append(d)
            grid_rows.append(self._make_row(r, i))
        self._grid.load_rows(grid_rows)
        self._refresh_totals()

    def _make_row(self, a: dict, i: int) -> dict:
        def f(k): return f"{float(a.get(k) or 0):,.2f}"
        return {
            "iid":    str(a.get("id", i)),
            "tag":    "alt" if i % 2 else "",
            "values": [
                a.get("asset_name",""), a.get("category",""), a.get("method","SLM"),
                a.get("useful_life_yrs","10"),
                f("gross_op"), f("additions"), f("disposals"), f("gross_cl"),
                f("dep_op"), f("dep_charge"), f("dep_cl"), f("nbv_cy"),
                f("nbv_py"), f("it_dep"),
            ]
        }

    def _refresh_totals(self):
        tot = summarize_ppe(self._assets)
        self._tot_var.set(
            f"Total Net Block CY: ₹{tot['nbv_cy']:,.2f}  |  "
            f"Total Net Block PY: ₹{tot['nbv_py']:,.2f}  |  "
            f"Total Dep Charge: ₹{tot['dep_charge']:,.2f}  |  "
            f"Total IT Dep: ₹{tot['it_dep']:,.2f}"
        )

    def _add_asset(self):
        new = {"asset_name": "New Asset", "category": PPE_CATEGORIES[0],
               "method": "SLM", "useful_life_yrs": 10}
        self._db.upsert_ppe(new)
        self._load()

    def _delete_asset(self):
        iid = self._grid.get_selected_iid()
        if not iid:
            messagebox.showinfo("Select Row", "Please select an asset to delete.")
            return
        if messagebox.askyesno("Delete", "Delete selected asset?"):
            self._db.delete_ppe(int(iid))
            self._load()

    def _recalc_all(self):
        rows = self._grid.get_all_rows()
        for i, row in enumerate(rows):
            if i >= len(self._assets):
                break
            a = self._assets[i]
            a["asset_name"]     = row[0]
            a["category"]       = row[1]
            a["method"]         = row[2]
            a["useful_life_yrs"]= int(row[3] or 10)
            for j, key in enumerate(["gross_op","additions","disposals","dep_op"], start=4):
                try:
                    a[key] = float(str(row[j]).replace(",",""))
                except (ValueError, IndexError):
                    a[key] = 0.0
            r = recalc_asset(a)
            self._assets[i] = r
            self._db.upsert_ppe(r)
        self._load()

    def _post_dep(self):
        tot = summarize_ppe(self._assets)
        dep = tot["dep_charge"]
        if dep == 0:
            messagebox.showinfo("No Depreciation", "No depreciation calculated yet.")
            return
        adj_id = f"AJE-DEP-{__import__('datetime').datetime.now().strftime('%d%m%H%M')}"
        self._db.add_adjustment(adj_id, "Depreciation & Amortisation Expense",
                                "NP008", dep, 0, "Depreciation per FA Register")
        self._db.add_adjustment(adj_id + "b", "Accumulated Depreciation",
                                "AS002", 0, dep, "Depreciation per FA Register")
        self._db.log("DEP_POSTED", f"₹{dep:,.2f}")
        messagebox.showinfo("Posted",
                            f"✅ Depreciation entry ₹{dep:,.2f} posted.\nEntry ID: {adj_id}")
        if self._on_dep_posted:
            self._on_dep_posted(dep)

    def _on_change(self, iid: str, col_id: str, new_val: str):
        pass  # recalc on "Recalculate All" button
