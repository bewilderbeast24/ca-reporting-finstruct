"""
Clients tab — Apple-style clean UI.

• List clients in a sortable table
• Right panel: encrypted detail view + compliance assignments
• Import from CSV / XLSX with live preview
• Download CSV / XLSX template
"""

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from ca_reminder.core.importer import (
    openpyxl_available,
    read_clients,
    save_client_template_csv,
    save_client_template_xlsx,
)
from ca_reminder.data.database import Database
from ca_reminder.gui import theme as T


class ClientsTab(tk.Frame):

    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, bg=T.BG, **kwargs)
        self.db = db
        self._build()
        self.refresh()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Page title row
        hdr = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Clients", font=T.F_HEADING,
                 fg=T.TEXT, bg=T.BG).pack(side="left")

        # Toolbar
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=T.PAD_L, pady=(0, T.PAD_S))

        T.btn(bar, "+ Add Client",   self._add,    style="primary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Edit",           self._edit,   style="secondary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Deactivate",     self._delete, style="secondary").pack(side="left", padx=(0, 6))
        T.btn(bar, "Erase (DPDP)",   self._hard_delete, style="danger").pack(side="left", padx=(0, 20))

        T.btn(bar, "↓ Import CSV/XLSX",  self._import,           style="ghost").pack(side="left", padx=(0, 6))
        T.btn(bar, "Template CSV",        self._download_csv,     style="ghost").pack(side="left", padx=(0, 6))
        if openpyxl_available():
            T.btn(bar, "Template XLSX", self._download_xlsx, style="ghost").pack(side="left", padx=(0, 6))

        T.divider(self).pack(fill="x", padx=T.PAD_L)

        # Main split pane
        pane = tk.PanedWindow(self, orient="horizontal", bg=T.BG,
                              sashwidth=1, sashpad=0,
                              sashrelief="flat", relief="flat", bd=0)
        pane.pack(fill="both", expand=True, padx=T.PAD_L, pady=T.PAD)

        # ── Left: client list ─────────────────────────────────────────────────
        left = tk.Frame(pane, bg=T.BG)
        pane.add(left, width=460)

        cols = ("code", "name", "email", "consent")
        self._tree = ttk.Treeview(left, columns=cols, show="headings",
                                  style="Treeview")
        for col, hdr_txt, w, anch in [
            ("code",    "Code",    80,  "w"),
            ("name",    "Name",   160,  "w"),
            ("email",   "Email",  190,  "w"),
            ("consent", "✓",       40, "center"),
        ]:
            self._tree.heading(col, text=hdr_txt,
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, anchor=anch, minwidth=40)

        self._tree.tag_configure("odd",        background=T.BG)
        self._tree.tag_configure("even",       background=T.BG_ALT)
        self._tree.tag_configure("no_consent", foreground=T.ERROR)

        vsb = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Right: details + assignments ──────────────────────────────────────
        right = tk.Frame(pane, bg=T.BG)
        pane.add(right)

        # Detail card
        T.section_header(right, "Details").pack(fill="x", pady=(0, T.PAD_S))
        self._detail_frame = T.card(right)
        self._detail_frame.pack(fill="x", pady=(0, T.PAD))
        self._detail_vars: dict[str, tk.StringVar] = {}
        for label_text, key in [
            ("Name",    "name"),
            ("Email",   "email"),
            ("Phone",   "phone"),
            ("PAN",     "pan"),
            ("GSTIN",   "gstin"),
            ("Consent", "consent_given"),
        ]:
            row = tk.Frame(self._detail_frame, bg=T.BG)
            row.pack(fill="x", padx=T.PAD, pady=3)
            tk.Label(row, text=label_text + ":", font=T.F_CAPTION,
                     fg=T.TEXT_SEC, bg=T.BG, width=8, anchor="e").pack(side="left")
            var = tk.StringVar()
            self._detail_vars[key] = var
            tk.Label(row, textvariable=var, font=T.F_BODY,
                     fg=T.TEXT, bg=T.BG, anchor="w").pack(side="left", padx=8)

        # Compliance Assignments — sub-frame fills all remaining right-panel space
        assign_frame = tk.Frame(right, bg=T.BG)
        assign_frame.pack(fill="both", expand=True)

        T.section_header(assign_frame, "Compliance Assignments").pack(
            fill="x", pady=(T.PAD, T.PAD_S))

        # ── Pack button + hint at BOTTOM first so they are always visible ─────
        ab = tk.Frame(assign_frame, bg=T.BG)
        ab.pack(fill="x", side="bottom", pady=(T.PAD_S, 0))
        T.btn(ab, "Manage Compliances…", self._manage_assignments,
              style="secondary").pack(side="left")

        tk.Label(
            assign_frame,
            text="Reminders sent only for compliances assigned here.  "
                 "Select a client → click 'Manage Compliances…'",
            font=T.F_CAPTION, fg=T.TEXT_LIGHT, bg=T.BG, justify="left",
        ).pack(side="bottom", anchor="w", pady=(2, 0))

        # ── Treeview fills the remaining (middle) space ───────────────────────
        a_cols = ("name", "category", "frequency", "due")
        self._assign_tree = ttk.Treeview(assign_frame, columns=a_cols,
                                          show="headings", style="Treeview")
        for col, hdr_txt, w in [
            ("name",      "Compliance", 200),
            ("category",  "Category",  110),
            ("frequency", "Frequency",  90),
            ("due",       "Due Day",    65),
        ]:
            self._assign_tree.heading(col, text=hdr_txt)
            self._assign_tree.column(col, width=w, anchor="w")

        avsb = ttk.Scrollbar(assign_frame, orient="vertical",
                             command=self._assign_tree.yview)
        self._assign_tree.configure(yscrollcommand=avsb.set)
        avsb.pack(side="right", fill="y")
        self._assign_tree.pack(fill="both", expand=True)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        for i, c in enumerate(self.db.get_all_clients()):
            consent = "✓" if c.get("consent_given") else "✗"
            parity  = "odd" if i % 2 == 0 else "even"
            tags    = (str(c["id"]), parity)
            if not c.get("consent_given"):
                tags += ("no_consent",)
            self._tree.insert(
                "", "end",
                values=(c.get("client_code", ""), c["name"],
                        c["email"], consent),
                tags=tags,
            )

    def _refresh_assignments(self, client_id: int) -> None:
        for row in self._assign_tree.get_children():
            self._assign_tree.delete(row)
        for a in self.db.get_client_compliances(client_id):
            due = a.get("custom_due_day") or a.get("due_day") or "—"
            self._assign_tree.insert(
                "", "end",
                values=(a["name"], a["category"], a["frequency"], due),
                tags=(str(a["compliance_id"]),),
            )

    # ── Selection ─────────────────────────────────────────────────────────────

    def _selected_id(self) -> Optional[int]:
        sel = self._tree.selection()
        return int(self._tree.item(sel[0])["tags"][0]) if sel else None

    def _on_select(self, *_) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        c = self.db.get_client(cid)
        if not c:
            return
        self._detail_vars["name"].set(c["name"])
        self._detail_vars["email"].set(c["email"])
        self._detail_vars["phone"].set(c.get("phone") or "—")
        self._detail_vars["pan"].set(c.get("pan") or "—")
        self._detail_vars["gstin"].set(c.get("gstin") or "—")
        self._detail_vars["consent_given"].set(
            "Yes ✓" if c.get("consent_given") else "No ✗")
        self._refresh_assignments(cid)

    def _sort(self, col: str) -> None:
        items = [(self._tree.set(k, col), k)
                 for k in self._tree.get_children("")]
        items.sort()
        for idx, (_, k) in enumerate(items):
            self._tree.move(k, "", idx)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add(self) -> None:
        dlg = ClientDialog(self, self.db)
        if dlg.result:
            try:
                self.db.save_client(dlg.result)
                self.refresh()
            except Exception as exc:
                messagebox.showerror(
                    "Save Failed",
                    f"Could not save client:\n\n{exc}",
                    parent=self,
                )

    def _edit(self) -> None:
        cid = self._selected_id()
        if cid is None:
            messagebox.showinfo("Select Client",
                                "Select a client first.", parent=self)
            return
        dlg = ClientDialog(self, self.db, client=self.db.get_client(cid))
        if dlg.result:
            try:
                self.db.save_client({**dlg.result, "id": cid})
                self.refresh()
            except Exception as exc:
                messagebox.showerror(
                    "Save Failed",
                    f"Could not save client:\n\n{exc}",
                    parent=self,
                )

    def _delete(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        if messagebox.askyesno(
            "Deactivate",
            "Deactivate this client?\n"
            "Their data is kept but reminders stop.\n"
            "Use 'Erase (DPDP)' to permanently delete.",
            parent=self,
        ):
            self.db.soft_delete_client(cid)
            self.refresh()

    def _hard_delete(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        c    = self.db.get_client(cid)
        name = c["name"] if c else "this client"
        if messagebox.askyesno(
            "Permanent Erasure",
            f"Permanently delete ALL data for '{name}'?\n\n"
            "Satisfies DPDP Act right-to-erasure. Cannot be undone.",
            icon="warning", parent=self,
        ):
            self.db.hard_delete_client(cid)
            self.refresh()

    # ── Import ────────────────────────────────────────────────────────────────

    def _import(self) -> None:
        ftypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        if openpyxl_available():
            ftypes.insert(0, ("Excel files", "*.xlsx"))
        path = filedialog.askopenfilename(
            title="Import Clients",
            filetypes=ftypes,
            parent=self,
        )
        if not path:
            return
        try:
            rows, warnings = read_clients(path)
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc), parent=self)
            return

        dlg = ImportPreviewDialog(self, rows, warnings,
                                  columns=["client_code", "name", "email",
                                           "phone", "pan", "gstin",
                                           "consent_given", "notes"],
                                  title="Preview — Client Import")
        if not dlg.confirmed:
            return

        saved, skipped = 0, 0
        for row in rows:
            try:
                self.db.save_client(row)
                saved += 1
            except Exception:
                skipped += 1

        self.refresh()
        messagebox.showinfo(
            "Import Complete",
            f"Imported {saved} client(s).  Skipped: {skipped}.",
            parent=self,
        )

    def _download_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Client Template",
            initialfile="client_template.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            parent=self,
        )
        if path:
            save_client_template_csv(path)
            messagebox.showinfo("Saved", f"Template saved to:\n{path}", parent=self)

    def _download_xlsx(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Client Template (Excel)",
            initialfile="client_template.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            parent=self,
        )
        if path:
            try:
                save_client_template_xlsx(path)
                messagebox.showinfo("Saved", f"Template saved to:\n{path}",
                                    parent=self)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=self)

    # ── Assignments ───────────────────────────────────────────────────────────

    def _manage_assignments(self) -> None:
        cid = self._selected_id()
        if cid is None:
            messagebox.showinfo("Select Client",
                                "Select a client first.", parent=self)
            return
        c = self.db.get_client(cid)
        ManageAssignmentsDialog(
            self, self.db, cid,
            c["name"] if c else "Client",
        )
        # Refresh the summary treeview after dialog closes
        self._refresh_assignments(cid)


# ── Client Add/Edit Dialog ────────────────────────────────────────────────────

class ClientDialog(tk.Toplevel):

    def __init__(self, parent, db: Database, client: Optional[dict] = None):
        super().__init__(parent)
        self.db = db
        self.result: Optional[dict] = None
        self.title("Edit Client" if client else "Add Client")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if client:
            self._fill(client)
        self.wait_window()

    def _build(self) -> None:
        tk.Label(self, text="Client Information",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG,
                 padx=T.PAD_L, pady=T.PAD).pack(anchor="w")
        T.divider(self).pack(fill="x")

        form = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD_L)
        form.pack(fill="both", expand=True)

        self._entries: dict[str, tk.Entry] = {}
        self._consent_var = tk.BooleanVar()

        # Two-column layout
        left_col = tk.Frame(form, bg=T.BG)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, T.PAD_L))
        right_col = tk.Frame(form, bg=T.BG)
        right_col.pack(side="left", fill="both", expand=True)

        def _field(parent, label_text, key, show=""):
            tk.Label(parent, text=label_text,
                     font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG,
                     anchor="w").pack(fill="x", pady=(T.PAD_S, 2))
            e = T.entry(parent, width=30, show=show)
            e.pack(fill="x")
            self._entries[key] = e

        _field(left_col, "Full Name *",    "name")
        _field(left_col, "Email Address *", "email")
        _field(left_col, "Phone",           "phone")
        _field(left_col, "Notes",           "notes")

        _field(right_col, "Client Code",   "client_code")
        _field(right_col, "PAN",           "pan")
        _field(right_col, "GSTIN",         "gstin")

        # Consent
        consent_row = tk.Frame(right_col, bg=T.BG)
        consent_row.pack(fill="x", pady=(T.PAD, 0))
        ttk.Checkbutton(
            consent_row,
            text="Client has given consent (DPDP Act)",
            variable=self._consent_var,
        ).pack(anchor="w")
        tk.Label(
            right_col,
            text="Reminders sent only to consenting clients.",
            font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG,
        ).pack(anchor="w", pady=(2, 0))

        T.divider(self).pack(fill="x")
        btn_row = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        btn_row.pack(fill="x")
        T.btn(btn_row, "Save",   self._save,    style="primary").pack(side="right", padx=(6, 0))
        T.btn(btn_row, "Cancel", self.destroy,  style="secondary").pack(side="right")

    def _fill(self, c: dict) -> None:
        for key, entry in self._entries.items():
            entry.insert(0, c.get(key, "") or "")
        self._consent_var.set(bool(c.get("consent_given")))

    def _save(self) -> None:
        if not self._entries["name"].get().strip() or \
           not self._entries["email"].get().strip():
            messagebox.showwarning("Required",
                                   "Name and Email are required.", parent=self)
            return
        self.result = {k: e.get().strip() for k, e in self._entries.items()}
        self.result["consent_given"] = self._consent_var.get()
        if self.result["consent_given"]:
            self.result["consent_date"] = date.today().isoformat()
        self.destroy()


# ── Manage Assignments Dialog ─────────────────────────────────────────────────

class ManageAssignmentsDialog(tk.Toplevel):
    """
    Consolidated Add / Edit / Remove dialog for one client's compliance assignments.

    Left panel  — compliances currently assigned to this client
                  buttons: Edit Selected · Remove
    Right panel — available compliances not yet assigned
                  buttons: ← Add Selected  (or double-click to add)
    Bottom strip — shared Custom Due Day + Notes fields used for both Add and Edit
    """

    def __init__(self, parent, db: Database,
                 client_id: int, client_name: str) -> None:
        super().__init__(parent)
        self.db        = db
        self.client_id = client_id
        self._edit_id: Optional[int] = None

        self.title(f"Compliance Assignments — {client_name}")
        self.configure(bg=T.BG)
        self.resizable(True, True)
        self.geometry("860x520")
        self.minsize(700, 420)
        self.grab_set()
        self._build()
        self._reload()
        self.wait_window()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        tk.Label(self, text="Manage Compliance Assignments",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG,
                 padx=T.PAD_L, pady=T.PAD).pack(anchor="w")
        T.divider(self).pack(fill="x")

        # ── Two treeview panels ───────────────────────────────────────────────
        panels = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        panels.pack(fill="both", expand=True)

        # Left — assigned
        left = tk.Frame(panels, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, T.PAD))

        tk.Label(left, text="Assigned to this client",
                 font=T.F_LABEL, fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w", pady=(0, 4))

        a_cols = ("name", "category", "due", "notes")
        self._a_tree = ttk.Treeview(left, columns=a_cols, show="headings",
                                     height=10, style="Treeview")
        for col, hdr, w, anch in [
            ("name",     "Compliance", 195, "w"),
            ("category", "Category",  110, "w"),
            ("due",      "Due Day",    65, "center"),
            ("notes",    "Notes",     120, "w"),
        ]:
            self._a_tree.heading(col, text=hdr)
            self._a_tree.column(col, width=w, anchor=anch, minwidth=40)
        self._a_tree.bind("<<TreeviewSelect>>", self._on_assigned_select)

        avsb = ttk.Scrollbar(left, orient="vertical", command=self._a_tree.yview)
        self._a_tree.configure(yscrollcommand=avsb.set)
        avsb.pack(side="right", fill="y")
        self._a_tree.pack(fill="both", expand=True)

        a_btns = tk.Frame(left, bg=T.BG)
        a_btns.pack(fill="x", pady=(T.PAD_S, 0))
        T.btn(a_btns, "Edit Selected", self._start_edit,
              style="secondary").pack(side="left", padx=(0, 6))
        T.btn(a_btns, "Remove",        self._remove,
              style="danger").pack(side="left")

        # Vertical separator
        T.divider(panels, orient="vertical").pack(
            side="left", fill="y", padx=(0, T.PAD))

        # Right — available
        right = tk.Frame(panels, bg=T.BG)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="Available to add",
                 font=T.F_LABEL, fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w", pady=(0, 4))

        u_cols = ("category", "name")
        self._u_tree = ttk.Treeview(right, columns=u_cols, show="headings",
                                     height=10, style="Treeview")
        for col, hdr, w in [
            ("category", "Category",   120),
            ("name",     "Compliance", 210),
        ]:
            self._u_tree.heading(col, text=hdr)
            self._u_tree.column(col, width=w, anchor="w", minwidth=40)
        self._u_tree.bind("<Double-1>", lambda _: self._add_selected())

        uvsb = ttk.Scrollbar(right, orient="vertical", command=self._u_tree.yview)
        self._u_tree.configure(yscrollcommand=uvsb.set)
        uvsb.pack(side="right", fill="y")
        self._u_tree.pack(fill="both", expand=True)

        u_btns = tk.Frame(right, bg=T.BG)
        u_btns.pack(fill="x", pady=(T.PAD_S, 0))
        T.btn(u_btns, "← Add Selected", self._add_selected,
              style="primary").pack(side="left")
        tk.Label(u_btns, text="or double-click",
                 font=T.F_CAPTION, fg=T.TEXT_LIGHT, bg=T.BG).pack(
            side="left", padx=8)

        # ── Edit / Add strip ──────────────────────────────────────────────────
        T.divider(self).pack(fill="x", padx=T.PAD_L, pady=(T.PAD_S, 0))

        strip = tk.Frame(self, bg=T.BG_ALT, padx=T.PAD_L, pady=T.PAD_S)
        strip.pack(fill="x")

        self._hint_lbl = tk.Label(
            strip,
            text="To ADD: select from the right panel → click '← Add Selected'.  "
                 "To EDIT: select from the left panel → click 'Edit Selected'.",
            font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG_ALT, justify="left",
        )
        self._hint_lbl.pack(anchor="w", pady=(0, T.PAD_S))

        fields = tk.Frame(strip, bg=T.BG_ALT)
        fields.pack(fill="x")

        tk.Label(fields, text="Custom Due Day (1–31):",
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG_ALT).pack(side="left")
        self._due_e = T.entry(fields, width=6)
        self._due_e.pack(side="left", padx=(6, T.PAD_L))

        tk.Label(fields, text="Notes:",
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG_ALT).pack(side="left")
        self._notes_e = T.entry(fields, width=38)
        self._notes_e.pack(side="left", padx=(6, T.PAD_L))

        self._save_btn = T.btn(fields, "Save Edit", self._save_edit,
                               style="secondary")
        self._save_btn.pack(side="left")
        self._save_btn.configure(state="disabled")

        self._status_lbl = tk.Label(
            strip, text="", font=T.F_CAPTION, fg=T.SUCCESS, bg=T.BG_ALT)
        self._status_lbl.pack(anchor="w", pady=(T.PAD_S, 0))

        # ── Footer ────────────────────────────────────────────────────────────
        T.divider(self).pack(fill="x", padx=T.PAD_L)
        foot = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        foot.pack(fill="x")
        T.btn(foot, "Done", self.destroy, style="primary").pack(side="right")

    # ── Data refresh ─────────────────────────────────────────────────────────

    def _reload(self) -> None:
        for row in self._a_tree.get_children():
            self._a_tree.delete(row)
        for a in self.db.get_client_compliances(self.client_id):
            due   = a.get("custom_due_day") or a.get("due_day") or "—"
            notes = a.get("notes", "") or ""
            self._a_tree.insert("", "end",
                                values=(a["name"], a["category"], due, notes),
                                tags=(str(a["compliance_id"]),))

        for row in self._u_tree.get_children():
            self._u_tree.delete(row)
        for c in self.db.get_unassigned_compliances(self.client_id):
            self._u_tree.insert("", "end",
                                values=(c["category"], c["name"]),
                                tags=(str(c["id"]),))
        self._reset_strip()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_assigned_select(self, *_) -> None:
        # Clear any status message when the user starts a new selection
        self._status_lbl.configure(text="")

    def _set_status(self, msg: str, ok: bool = True) -> None:
        self._status_lbl.configure(
            text=msg, fg=T.SUCCESS if ok else T.ERROR)

    def _start_edit(self) -> None:
        sel = self._a_tree.selection()
        if not sel:
            messagebox.showinfo("Select",
                                "Select an assigned compliance to edit.", parent=self)
            return
        comp_id   = int(self._a_tree.item(sel[0])["tags"][0])
        comp_name = self._a_tree.item(sel[0])["values"][0]
        assignments = self.db.get_client_compliances(self.client_id)
        a = next((x for x in assignments if x["compliance_id"] == comp_id), {})

        self._edit_id = comp_id
        self._hint_lbl.configure(
            text=f"Editing: {comp_name}  — update the fields below, then click Save Edit.",
            fg=T.ACCENT,
        )
        self._due_e.delete(0, "end")
        if a.get("custom_due_day"):
            self._due_e.insert(0, str(a["custom_due_day"]))
        self._notes_e.delete(0, "end")
        self._notes_e.insert(0, a.get("notes", "") or "")
        self._save_btn.configure(state="normal")

    def _save_edit(self) -> None:
        if not self._edit_id:
            return
        custom, ok = self._parse_due()
        if not ok:
            return
        self.db.assign_compliance(self.client_id, self._edit_id,
                                  custom, self._notes_e.get().strip())
        self._reload()
        self._set_status("Changes saved ✓")

    def _add_selected(self) -> None:
        sel = self._u_tree.selection()
        if not sel:
            messagebox.showinfo(
                "Select Compliance",
                "Click on a compliance in the right panel ('Available to add'), "
                "then click '← Add Selected'.",
                parent=self)
            return
        comp_name = self._u_tree.item(sel[0])["values"][1]
        comp_id   = int(self._u_tree.item(sel[0])["tags"][0])
        custom, ok = self._parse_due()
        if not ok:
            return
        self.db.assign_compliance(self.client_id, comp_id,
                                  custom, self._notes_e.get().strip())
        self._reload()
        self._set_status(f"'{comp_name}' added ✓")

    def _remove(self) -> None:
        sel = self._a_tree.selection()
        if not sel:
            messagebox.showinfo(
                "Select Compliance",
                "Click on a compliance in the left panel ('Assigned to this client'), "
                "then click 'Remove'.",
                parent=self)
            return
        comp_id = int(self._a_tree.item(sel[0])["tags"][0])
        name    = self._a_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Remove Assignment",
                               f"Remove '{name}' from this client?",
                               parent=self):
            self.db.remove_assignment(self.client_id, comp_id)
            self._reload()
            self._set_status(f"'{name}' removed ✓")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _reset_strip(self) -> None:
        self._edit_id = None
        self._hint_lbl.configure(
            text="To ADD: select from the right panel → click '← Add Selected'.  "
                 "To EDIT: select from the left panel → click 'Edit Selected'.",
            fg=T.TEXT_SEC,
        )
        self._due_e.delete(0, "end")
        self._notes_e.delete(0, "end")
        self._save_btn.configure(state="disabled")

    def _parse_due(self) -> tuple[Optional[int], bool]:
        raw = self._due_e.get().strip()
        if not raw:
            return None, True
        try:
            day = int(raw)
            if not 1 <= day <= 31:
                raise ValueError
            return day, True
        except ValueError:
            messagebox.showerror("Invalid Due Day",
                                 "Custom Due Day must be a number 1–31.",
                                 parent=self)
            return None, False


# ── Import Preview Dialog ─────────────────────────────────────────────────────

class ImportPreviewDialog(tk.Toplevel):
    """Show a preview table of rows to be imported and let user confirm."""

    def __init__(self, parent, rows: list[dict], warnings: list[str],
                 columns: list[str], title: str = "Import Preview"):
        super().__init__(parent)
        self.confirmed = False
        self.title(title)
        self.configure(bg=T.BG)
        self.grab_set()
        self._build(rows, warnings, columns)
        self.wait_window()

    def _build(self, rows, warnings, columns) -> None:
        tk.Label(self, text=f"{len(rows)} row(s) ready to import",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG,
                 padx=T.PAD_L, pady=T.PAD).pack(anchor="w")
        T.divider(self).pack(fill="x")

        # Warnings
        if warnings:
            warn_frame = tk.Frame(self, bg="#FFF8E1", padx=T.PAD_L, pady=T.PAD_S)
            warn_frame.pack(fill="x")
            tk.Label(warn_frame,
                     text=f"⚠  {len(warnings)} row(s) skipped:",
                     font=T.F_CAPTION, fg=T.WARNING, bg="#FFF8E1").pack(anchor="w")
            for w in warnings[:5]:
                tk.Label(warn_frame, text=f"  {w}",
                         font=T.F_CAPTION, fg=T.TEXT_SEC, bg="#FFF8E1").pack(anchor="w")

        # Preview table (first 8 rows)
        preview_rows = rows[:8]
        card = T.card(self)
        card.pack(fill="both", expand=True, padx=T.PAD_L,
                  pady=T.PAD, ipadx=2, ipady=2)

        tree = ttk.Treeview(card, columns=columns, show="headings", height=min(len(preview_rows), 8))
        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=110, anchor="w")
        for row in preview_rows:
            tree.insert("", "end", values=[row.get(c, "") for c in columns])

        hsb = ttk.Scrollbar(card, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        if len(rows) > 8:
            tk.Label(self,
                     text=f"  … and {len(rows) - 8} more row(s) not shown.",
                     font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w",
                                                                       padx=T.PAD_L)

        T.divider(self).pack(fill="x", pady=(T.PAD, 0))
        btn_row = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        btn_row.pack(fill="x")
        T.btn(btn_row, f"Import {len(rows)} row(s)", self._confirm,
              style="primary").pack(side="right", padx=(6, 0))
        T.btn(btn_row, "Cancel", self.destroy,
              style="secondary").pack(side="right")

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()
