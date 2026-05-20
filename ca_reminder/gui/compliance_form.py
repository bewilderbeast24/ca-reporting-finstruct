"""
Compliances tab — Apple-style clean UI.

• Sortable table of all compliance types
• Add / Edit / Toggle active
• Import from CSV / XLSX with preview
• Download templates
"""

import calendar as cal
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from ca_reminder.config import COMPLIANCE_CATEGORIES, COMPLIANCE_FREQUENCIES
from ca_reminder.core.importer import (
    openpyxl_available,
    read_compliances,
    save_compliance_template_csv,
    save_compliance_template_xlsx,
)
from ca_reminder.data.database import Database
from ca_reminder.gui import theme as T
from ca_reminder.gui.client_form import ImportPreviewDialog


class CompliancesTab(tk.Frame):

    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, bg=T.BG, **kwargs)
        self.db = db
        self._show_inactive = tk.BooleanVar(value=False)
        self._build()
        self.refresh()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Page title
        hdr = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Compliances", font=T.F_HEADING,
                 fg=T.TEXT, bg=T.BG).pack(side="left")

        # Toolbar
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=T.PAD_L, pady=(0, T.PAD_S))

        T.btn(bar, "+ Add",           self._add,    style="primary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Edit",            self._edit,   style="secondary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Toggle Active",   self._toggle, style="secondary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Delete",          self._delete, style="danger").pack(side="left", padx=(0, 20))

        T.btn(bar, "↓ Import CSV/XLSX",   self._import,        style="ghost").pack(side="left", padx=(0, 6))
        T.btn(bar, "Export CSV",          self._export_csv,    style="ghost").pack(side="left", padx=(0, 6))
        T.btn(bar, "Template CSV",        self._dl_csv,        style="ghost").pack(side="left", padx=(0, 6))
        if openpyxl_available():
            T.btn(bar, "Template XLSX",   self._dl_xlsx,       style="ghost").pack(side="left", padx=(0, 6))

        ttk.Checkbutton(
            bar, text="Show inactive",
            variable=self._show_inactive,
            command=self.refresh,
        ).pack(side="right")

        T.divider(self).pack(fill="x", padx=T.PAD_L)

        # Main card
        card = T.card(self)
        card.pack(fill="both", expand=True, padx=T.PAD_L, pady=T.PAD)

        cols = ("name", "category", "frequency", "due_day",
                "due_month", "adv_days", "status")
        self._tree = ttk.Treeview(card, columns=cols, show="headings",
                                   style="Treeview")
        for col, hdr_txt, w, anch in [
            ("name",      "Compliance Name",  240, "w"),
            ("category",  "Category",         130, "w"),
            ("frequency", "Frequency",          90, "center"),
            ("due_day",   "Due Day",            60, "center"),
            ("due_month", "Due Month",          75, "center"),
            ("adv_days",  "Remind (days)",      90, "center"),
            ("status",    "Status",             70, "center"),
        ]:
            self._tree.heading(col, text=hdr_txt,
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, anchor=anch, minwidth=40)

        self._tree.tag_configure("odd",      background=T.BG)
        self._tree.tag_configure("even",     background=T.BG_ALT)
        self._tree.tag_configure("inactive", foreground=T.TEXT_LIGHT)

        vsb = ttk.Scrollbar(card, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True, padx=1, pady=1)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._edit())

        # Description strip
        T.divider(self).pack(fill="x", padx=T.PAD_L)
        desc_row = tk.Frame(self, bg=T.BG_ALT, padx=T.PAD_L, pady=T.PAD_S)
        desc_row.pack(fill="x")
        tk.Label(desc_row, text="Description:", font=T.F_CAPTION,
                 fg=T.TEXT_SEC, bg=T.BG_ALT).pack(side="left")
        self._desc_var = tk.StringVar(value="Select a compliance to view details.")
        tk.Label(desc_row, textvariable=self._desc_var, font=T.F_CAPTION,
                 fg=T.TEXT, bg=T.BG_ALT).pack(side="left", padx=8)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        active_only = not self._show_inactive.get()
        for i, c in enumerate(self.db.get_all_compliances(active_only=active_only)):
            month_str = cal.month_abbr[c["due_month"]] if c.get("due_month") else "—"
            status    = "Active" if c["active"] else "Inactive"
            parity    = "odd" if i % 2 == 0 else "even"
            tags      = (str(c["id"]), parity)
            if not c["active"]:
                tags += ("inactive",)
            self._tree.insert(
                "", "end",
                values=(
                    c["name"], c["category"], c["frequency"],
                    c.get("due_day") or "—", month_str,
                    c.get("advance_reminder_days", 7), status,
                ),
                tags=tags,
            )

    def _on_select(self, *_) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        comp = self.db.get_compliance(cid)
        self._desc_var.set(comp.get("description", "") or "No description.")

    def _sort(self, col: str) -> None:
        items = [(self._tree.set(k, col), k)
                 for k in self._tree.get_children("")]
        items.sort()
        for idx, (_, k) in enumerate(items):
            self._tree.move(k, "", idx)

    def _selected_id(self) -> Optional[int]:
        sel = self._tree.selection()
        return int(self._tree.item(sel[0])["tags"][0]) if sel else None

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add(self) -> None:
        dlg = ComplianceDialog(self, self.db)
        if dlg.result:
            self.db.save_compliance(dlg.result)
            self.refresh()

    def _edit(self) -> None:
        cid = self._selected_id()
        if cid is None:
            messagebox.showinfo("Select",
                                "Select a compliance first.", parent=self)
            return
        dlg = ComplianceDialog(self, self.db, compliance=self.db.get_compliance(cid))
        if dlg.result:
            self.db.save_compliance({**dlg.result, "id": cid})
            self.refresh()

    def _toggle(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        comp = self.db.get_compliance(cid)
        self.db.toggle_compliance_active(cid, not bool(comp["active"]))
        self.refresh()

    def _delete(self) -> None:
        cid = self._selected_id()
        if cid is None:
            messagebox.showinfo("Select", "Select a compliance first.", parent=self)
            return
        comp = self.db.get_compliance(cid)
        if not messagebox.askyesno(
            "Delete Compliance",
            f"Permanently delete '{comp['name']}'?\n\n"
            "This also removes all client assignments for this compliance.\n"
            "This cannot be undone.",
            icon="warning", parent=self,
        ):
            return
        self.db.delete_compliance(cid)
        self.refresh()

    # ── Import / Export ───────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        """Export all current compliances (actual data) to a CSV file."""
        path = filedialog.asksaveasfilename(
            title="Export Compliances",
            initialfile="compliances_export.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            parent=self,
        )
        if not path:
            return
        compliances = self.db.get_all_compliances(active_only=False)
        if not compliances:
            messagebox.showinfo("Nothing to Export",
                                "No compliances found to export.", parent=self)
            return
        columns = ["name", "description", "category", "frequency",
                   "due_day", "due_month", "advance_reminder_days", "active"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                w.writeheader()
                w.writerows(compliances)
            messagebox.showinfo("Exported",
                                f"Exported {len(compliances)} compliance(s) to:\n{path}",
                                parent=self)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self)

    # ── Import ────────────────────────────────────────────────────────────────

    def _import(self) -> None:
        ftypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        if openpyxl_available():
            ftypes.insert(0, ("Excel files", "*.xlsx"))
        path = filedialog.askopenfilename(
            title="Import Compliances", filetypes=ftypes, parent=self)
        if not path:
            return
        try:
            rows, warnings = read_compliances(path)
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc), parent=self)
            return

        dlg = ImportPreviewDialog(
            self, rows, warnings,
            columns=["name", "category", "frequency",
                     "due_day", "due_month", "advance_reminder_days"],
            title="Preview — Compliance Import",
        )
        if not dlg.confirmed:
            return

        saved, skipped = 0, 0
        for row in rows:
            try:
                self.db.save_compliance(row)
                saved += 1
            except Exception:
                skipped += 1

        self.refresh()
        messagebox.showinfo(
            "Import Complete",
            f"Imported {saved} compliance(s).  Skipped: {skipped}.",
            parent=self,
        )

    def _dl_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Compliance Template",
            initialfile="compliance_template.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            parent=self,
        )
        if path:
            save_compliance_template_csv(path)
            messagebox.showinfo("Saved", f"Template saved to:\n{path}", parent=self)

    def _dl_xlsx(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Compliance Template (Excel)",
            initialfile="compliance_template.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            parent=self,
        )
        if path:
            try:
                save_compliance_template_xlsx(path)
                messagebox.showinfo("Saved", f"Template saved to:\n{path}",
                                    parent=self)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=self)


# ── Compliance Add/Edit Dialog ────────────────────────────────────────────────

class ComplianceDialog(tk.Toplevel):

    def __init__(self, parent, db: Database,
                 compliance: Optional[dict] = None):
        super().__init__(parent)
        self.db = db
        self.result: Optional[dict] = None
        self.title("Edit Compliance" if compliance else "Add Compliance")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if compliance:
            self._fill(compliance)
        self.wait_window()

    def _build(self) -> None:
        tk.Label(self, text="Compliance Definition",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG,
                 padx=T.PAD_L, pady=T.PAD).pack(anchor="w")
        T.divider(self).pack(fill="x")

        form = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD_L)
        form.pack(fill="both", expand=True)

        left = tk.Frame(form, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, T.PAD_L))
        right = tk.Frame(form, bg=T.BG)
        right.pack(side="left", fill="both", expand=True)

        def _lbl(parent, text):
            tk.Label(parent, text=text, font=T.F_CAPTION,
                     fg=T.TEXT_SEC, bg=T.BG, anchor="w").pack(
                fill="x", pady=(T.PAD_S, 2))

        # Left col
        _lbl(left, "Name *")
        self._name = T.entry(left, width=30)
        self._name.pack(fill="x")

        _lbl(left, "Description")
        self._desc = T.entry(left, width=30)
        self._desc.pack(fill="x")

        _lbl(left, "Category *")
        self._cat_var = tk.StringVar(value=COMPLIANCE_CATEGORIES[0])
        ttk.Combobox(left, textvariable=self._cat_var,
                     values=COMPLIANCE_CATEGORIES,
                     state="readonly", font=T.F_BODY).pack(fill="x")

        _lbl(left, "Frequency *")
        self._freq_var = tk.StringVar(value="Monthly")
        ttk.Combobox(left, textvariable=self._freq_var,
                     values=COMPLIANCE_FREQUENCIES,
                     state="readonly", font=T.F_BODY).pack(fill="x")

        # Right col
        _lbl(right, "Due Day  (1–31)")
        self._due_day = T.entry(right, width=10)
        self._due_day.pack(anchor="w")
        tk.Label(right, text="Day of month compliance is due.",
                 font=T.F_CAPTION, fg=T.TEXT_LIGHT,
                 bg=T.BG).pack(anchor="w")

        _lbl(right, "Due Month  (for Annual)")
        months = [""] + [cal.month_name[m] for m in range(1, 13)]
        self._due_month_var = tk.StringVar(value="")
        ttk.Combobox(right, textvariable=self._due_month_var,
                     values=months, state="readonly",
                     font=T.F_BODY, width=16).pack(anchor="w")

        _lbl(right, "Remind N days before")
        self._adv = T.entry(right, width=10)
        self._adv.insert(0, "7")
        self._adv.pack(anchor="w")

        T.divider(self).pack(fill="x")
        btn_row = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        btn_row.pack(fill="x")
        T.btn(btn_row, "Save",   self._save,   style="primary").pack(side="right", padx=(6, 0))
        T.btn(btn_row, "Cancel", self.destroy, style="secondary").pack(side="right")

    def _fill(self, c: dict) -> None:
        self._name.insert(0, c.get("name", ""))
        self._desc.insert(0, c.get("description", ""))
        self._cat_var.set(c.get("category", COMPLIANCE_CATEGORIES[0]))
        self._freq_var.set(c.get("frequency", "Monthly"))
        if c.get("due_day"):
            self._due_day.insert(0, str(c["due_day"]))
        if c.get("due_month"):
            self._due_month_var.set(cal.month_name[c["due_month"]])
        self._adv.delete(0, "end")
        self._adv.insert(0, str(c.get("advance_reminder_days", 7)))

    def _save(self) -> None:
        name = self._name.get().strip()
        if not name:
            messagebox.showwarning("Required",
                                   "Compliance name is required.", parent=self)
            return

        due_day = None
        if self._due_day.get().strip():
            try:
                due_day = int(self._due_day.get().strip())
                if not 1 <= due_day <= 31:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid",
                                     "Due Day must be 1–31.", parent=self)
                return

        due_month = None
        dm = self._due_month_var.get()
        if dm:
            due_month = list(cal.month_name).index(dm)

        try:
            adv = int(self._adv.get().strip() or "7")
        except ValueError:
            adv = 7

        self.result = {
            "name":                  name,
            "description":           self._desc.get().strip(),
            "category":              self._cat_var.get(),
            "frequency":             self._freq_var.get(),
            "due_day":               due_day,
            "due_month":             due_month,
            "advance_reminder_days": adv,
        }
        self.destroy()
