"""
Main application window — Apple-inspired clean design.

White background · dark text · accent blue · minimal chrome.
"""

import logging
import queue
import shutil
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from ca_reminder.config import APP_NAME, APP_VERSION, DB_PATH, DPDP_NOTICE, REMINDER_SEND_DAY
from ca_reminder.core.scheduler import check_and_send
from ca_reminder.data.database import Database
from ca_reminder.data.encryption import EncryptionManager
from ca_reminder.gui import theme as T
from ca_reminder.gui.client_form import ClientsTab
from ca_reminder.gui.compliance_form import CompliancesTab
from ca_reminder.gui.settings_form import SettingsForm

logger = logging.getLogger(__name__)


class MainWindow:
    """Root application window."""

    def __init__(self, root: tk.Tk, db: Database, enc: EncryptionManager) -> None:
        self.root = root
        self.db   = db
        self.enc  = enc
        self._q: queue.Queue = queue.Queue()
        self._sending = False

        T.configure_ttk_style()
        self._build()
        self._start_scheduler()

    # ── Window config ─────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.root.title(f"{APP_NAME}")
        self.root.geometry("1100x700")
        self.root.minsize(900, 580)
        self.root.configure(bg=T.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # ── Titlebar / nav strip ──────────────────────────────────────────────
        nav = tk.Frame(self.root, bg=T.BG, pady=0)
        nav.pack(fill="x")

        T.divider(nav).pack(fill="x")   # subtle top line

        inner_nav = tk.Frame(nav, bg=T.BG)
        inner_nav.pack(fill="x", padx=T.PAD_L, pady=10)

        tk.Label(inner_nav, text=APP_NAME,
                 font=T.F_SUBHEAD, fg=T.TEXT, bg=T.BG).pack(side="left")

        self._status_var = tk.StringVar(value="")
        tk.Label(inner_nav, textvariable=self._status_var,
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG).pack(side="left", padx=16)

        # Send Now button — top-right
        self._send_btn = T.btn(inner_nav, "Send Now", self._manual_send,
                               style="primary")
        self._send_btn.pack(side="right")
        
        self._resume_btn = T.btn(inner_nav, "Resume Unsent", self._resume_unsent)
        self._resume_btn.pack(side="right", padx=(0, 10))

        T.divider(nav).pack(fill="x")

        # ── Thin progress bar — packed between nav and notebook when active ──
        # Created here so it exists, but NOT packed yet; shown via pack(before=)
        self._pbar = ttk.Progressbar(self.root, mode="indeterminate",
                                     style="TProgressbar")

        # ── Notebook ──────────────────────────────────────────────────────────
        self._nb = ttk.Notebook(self.root, style="TNotebook")
        self._nb.pack(fill="both", expand=True)

        # Dashboard
        self._dash = tk.Frame(self._nb, bg=T.BG)
        self._nb.add(self._dash, text="  Dashboard  ")
        self._build_dashboard(self._dash)

        # Clients
        self._clients_tab = ClientsTab(self._nb, self.db)
        self._nb.add(self._clients_tab, text="  Clients  ")

        # Compliances
        self._comp_tab = CompliancesTab(self._nb, self.db)
        self._nb.add(self._comp_tab, text="  Compliances  ")

        # Email Setup
        self._settings_tab = SettingsForm(self._nb, self.db)
        self._nb.add(self._settings_tab, text="  Email Setup  ")

        # Activity Log
        self._log_frame = tk.Frame(self._nb, bg=T.BG)
        self._nb.add(self._log_frame, text="  Activity Log  ")
        self._build_log_tab(self._log_frame)

        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # ── Footer ────────────────────────────────────────────────────────────
        T.divider(self.root).pack(fill="x", side="bottom")
        footer = tk.Frame(self.root, bg=T.BG_ALT)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=f"Data encrypted · DPDP Act 2023 · Auto-send day: {REMINDER_SEND_DAY}st of month"
                 f"  ·  {APP_NAME} v{APP_VERSION}",
            font=T.F_CAPTION, fg=T.TEXT_LIGHT, bg=T.BG_ALT,
            padx=T.PAD_L, pady=6,
        ).pack(side="left")

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _build_dashboard(self, parent: tk.Frame) -> None:
        scroll_canvas = tk.Canvas(parent, bg=T.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        scroll_canvas.pack(fill="both", expand=True)

        body = tk.Frame(scroll_canvas, bg=T.BG)
        win = scroll_canvas.create_window((0, 0), window=body, anchor="nw")

        body.bind("<Configure>",
                  lambda _e: scroll_canvas.configure(
                      scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>",
                           lambda e: scroll_canvas.itemconfig(win, width=e.width))

        padx = T.PAD_L

        # ── Page title ────────────────────────────────────────────────────────
        top = tk.Frame(body, bg=T.BG, padx=padx, pady=T.PAD_L)
        top.pack(fill="x")

        today = date.today()
        tk.Label(top, text="Dashboard",
                 font=T.F_TITLE, fg=T.TEXT, bg=T.BG).pack(anchor="w")
        tk.Label(top, text=today.strftime("%A, %d %B %Y"),
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w")

        T.divider(body).pack(fill="x", padx=padx)

        # ── Stat cards ────────────────────────────────────────────────────────
        my   = today.strftime("%Y-%m")
        sent = self.db.already_sent_today(my)
        n_clients     = len(self.db.get_all_clients())
        n_compliances = len(self.db.get_all_compliances())

        cards_frame = tk.Frame(body, bg=T.BG, padx=padx, pady=T.PAD)
        cards_frame.pack(fill="x")

        stat_data = [
            ("Send Status",
             "Sent ✓" if sent else "Pending",
             T.SUCCESS if sent else T.WARNING,
             f"For {my}"),
            ("Auto-Send Day",
             f"{REMINDER_SEND_DAY}st",
             T.ACCENT,
             "of every month"),
            ("Active Clients",
             str(n_clients),
             T.TEXT,
             "with consent"),
            ("Compliance Types",
             str(n_compliances),
             T.TEXT,
             "active definitions"),
        ]
        for title, value, val_color, subtitle in stat_data:
            c = T.card(cards_frame, padx=20, pady=16)
            c.pack(side="left", padx=(0, 12))
            tk.Label(c, text=title, font=T.F_CAPTION,
                     fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w")
            tk.Label(c, text=value, font=T.font(24, "bold"),
                     fg=val_color, bg=T.BG).pack(anchor="w", pady=(4, 0))
            tk.Label(c, text=subtitle, font=T.F_CAPTION,
                     fg=T.TEXT_LIGHT, bg=T.BG).pack(anchor="w")

        T.divider(body).pack(fill="x", padx=padx, pady=(T.PAD, 0))

        # ── Action buttons ────────────────────────────────────────────────────
        action_row = tk.Frame(body, bg=T.BG, padx=padx, pady=T.PAD)
        action_row.pack(fill="x")
        T.btn(action_row, "Send Compliance Reminders Now",
              self._manual_send, style="primary").pack(side="left")
              
        T.btn(action_row, "Resume Unsent / Retry Failed",
              self._resume_unsent).pack(side="left", padx=(10, 0))
        tk.Label(
            action_row,
            text="Auto-send also fires on first launch each send day.",
            font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG,
        ).pack(side="left", padx=T.PAD)

        T.divider(body).pack(fill="x", padx=padx)

        # ── Database backup ───────────────────────────────────────────────────
        db_row = tk.Frame(body, bg=T.BG, padx=padx, pady=T.PAD_S)
        db_row.pack(fill="x")
        tk.Label(db_row, text="Database:",
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG).pack(side="left", padx=(0, 8))
        T.btn(db_row, "Backup", self._backup_db,
              style="ghost").pack(side="left", padx=(0, 6))
        T.btn(db_row, "Restore from Backup", self._restore_db,
              style="ghost").pack(side="left")
        tk.Label(db_row,
                 text="Backup saves a copy of your encrypted database file.",
                 font=T.F_CAPTION, fg=T.TEXT_LIGHT, bg=T.BG).pack(side="left", padx=(12, 0))

        T.divider(body).pack(fill="x", padx=padx)

        # ── Recent activity ───────────────────────────────────────────────────
        ra = tk.Frame(body, bg=T.BG, padx=padx, pady=T.PAD)
        ra.pack(fill="x")
        tk.Label(ra, text="Recent Activity",
                 font=T.F_SUBHEAD, fg=T.TEXT, bg=T.BG).pack(anchor="w")
        tk.Label(ra, text="Last 10 reminder dispatches",
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG).pack(anchor="w")

        log_card = T.card(body, padx=0, pady=0)
        log_card.pack(fill="x", padx=padx, pady=(0, T.PAD))

        self._dash_log = tk.Text(
            log_card, height=9, font=("Courier New", 11),
            bg=T.BG, fg=T.TEXT_SEC, relief="flat",
            state="disabled", padx=16, pady=12,
        )
        self._dash_log.pack(fill="x")
        self._refresh_dash_log()

        T.divider(body).pack(fill="x", padx=padx)

        # ── DPDP notice ───────────────────────────────────────────────────────
        notice_frame = tk.Frame(body, bg=T.BG_ALT, padx=padx, pady=T.PAD)
        notice_frame.pack(fill="x", padx=padx, pady=T.PAD)
        tk.Label(notice_frame, text="Data Privacy",
                 font=T.F_LABEL, fg=T.TEXT_SEC, bg=T.BG_ALT).pack(anchor="w")
        tk.Label(
            notice_frame, text=DPDP_NOTICE,
            font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG_ALT,
            wraplength=860, justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _refresh_dash_log(self) -> None:
        logs = self.db.get_recent_logs(limit=10)
        self._dash_log.configure(state="normal")
        self._dash_log.delete("1.0", "end")
        if not logs:
            self._dash_log.insert("end", "  No activity recorded yet.\n")
        for log in logs:
            ts     = log["sent_at"][:19].replace("T", " ")
            status = log["status"].upper()
            line = (
                f"  {ts}   {log['month_year']}   {status:<6}   "
                f"{log['client_name']:<28}   {log['compliance_count']} items\n"
            )
            self._dash_log.insert("end", line)
        self._dash_log.configure(state="disabled")

    # ── Activity Log tab ──────────────────────────────────────────────────────

    def _build_log_tab(self, parent: tk.Frame) -> None:
        # Header row
        hdr = tk.Frame(parent, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Activity Log",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG).pack(side="left")
        T.btn(hdr, "Refresh", self._refresh_log_tab,
              style="secondary").pack(side="right")

        T.divider(parent).pack(fill="x", padx=T.PAD_L)

        card = T.card(parent)
        card.pack(fill="both", expand=True, padx=T.PAD_L, pady=T.PAD)

        cols = ("sent_at", "month_year", "client", "status", "count", "error")
        self._log_tree = ttk.Treeview(card, columns=cols, show="headings",
                                      style="Treeview")
        for col, hdr_txt, w, anch in [
            ("sent_at",    "Sent At",      150, "w"),
            ("month_year", "Month",         70, "center"),
            ("client",     "Client",       180, "w"),
            ("status",     "Status",        75, "center"),
            ("count",      "Items",         55, "center"),
            ("error",      "Error",        320, "w"),
        ]:
            self._log_tree.heading(col, text=hdr_txt)
            self._log_tree.column(col, width=w, anchor=anch, minwidth=40)

        self._log_tree.tag_configure("sent",   foreground=T.SUCCESS)
        self._log_tree.tag_configure("failed", foreground=T.ERROR)

        vsb = ttk.Scrollbar(card, orient="vertical",
                             command=self._log_tree.yview)
        self._log_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_tree.pack(fill="both", expand=True, padx=1, pady=1)

    def _refresh_log_tab(self) -> None:
        for row in self._log_tree.get_children():
            self._log_tree.delete(row)
        for log in self.db.get_recent_logs():
            ts  = log["sent_at"][:19].replace("T", " ")
            tag = log["status"]
            self._log_tree.insert(
                "", "end",
                values=(ts, log["month_year"], log["client_name"],
                        log["status"].upper(), log["compliance_count"],
                        log.get("error_message", "")),
                tags=(tag,),
            )

    # ── Tab change ────────────────────────────────────────────────────────────

    def _on_tab_change(self, _event) -> None:
        tab = self._nb.tab(self._nb.select(), "text").strip()
        if "Activity" in tab:
            self._refresh_log_tab()
        elif "Dashboard" in tab:
            self._refresh_dash_log()

    # ── Scheduler ─────────────────────────────────────────────────────────────

    def _start_scheduler(self) -> None:
        threading.Thread(target=self._run_send,
                         kwargs={"force": False}, daemon=True).start()
        self.root.after(200, self._poll_q)

    def _run_send(self, force: bool = False, resume_unsent: bool = False) -> None:
        def prog(msg: str) -> None:
            self._q.put(("progress", msg))
        result = check_and_send(self.db, progress=prog, force=force, resume_unsent=resume_unsent)
        self._q.put(("done", result))

    def _poll_q(self) -> None:
        while not self._q.empty():
            kind, payload = self._q.get_nowait()
            if kind == "progress":
                self._status_var.set(payload)
                if not self._sending:
                    self._sending = True
                    # Insert pbar between nav strip and notebook
                    self._pbar.pack(fill="x", before=self._nb)
                    self._pbar.start(10)
            elif kind == "done":
                self._sending = False
                self._pbar.stop()
                self._pbar.pack_forget()
                self._on_done(payload)
        self.root.after(150, self._poll_q)

    def _on_done(self, result: dict) -> None:
        my = result["month_year"]
        if not result["triggered"]:
            if self.db.already_sent_today(my):
                self._status_var.set(f"Reminders sent for {my}.")
            else:
                self._status_var.set(
                    f"Next auto-send: {REMINDER_SEND_DAY}st of next month.")
            return

        s, f, sk = result["sent"], result["failed"], result["skipped"]
        self._status_var.set(
            f"{my}: {s} sent · {f} failed · {sk} skipped")
        self._refresh_dash_log()

        if s == 0 and f == 0:
            # Triggered but nothing to send — guide the user
            messagebox.showinfo(
                "Nothing to Send",
                "No emails were sent.\n\n"
                "Possible reasons:\n"
                "  • No clients have compliance assignments for this month\n"
                "  • No clients have 'Consent Given' ticked\n\n"
                "To fix:\n"
                "  1. Go to the Clients tab\n"
                "  2. Select a client\n"
                "  3. Click '+ Add Compliance' in the Compliance Assignments panel",
                parent=self.root,
            )
            return

        if f and result["errors"]:
            err_lines = "\n".join(f"  • {n}: {e}"
                                  for n, e in result["errors"][:5])
            messagebox.showwarning(
                "Some Emails Failed",
                f"{f} reminder(s) could not be sent:\n\n{err_lines}\n\n"
                "Check Activity Log for details.",
                parent=self.root,
            )
        elif s:
            messagebox.showinfo(
                "Reminders Sent",
                f"{s} compliance reminder(s) dispatched for {my}.",
                parent=self.root,
            )

    # ── Manual send ───────────────────────────────────────────────────────────

    def _manual_send(self) -> None:
        if self._sending:
            messagebox.showinfo(
                "In Progress", "A send job is already running.",
                parent=self.root)
            return
        if not self.db.get_active_email_account():
            messagebox.showwarning(
                "No Email Account",
                "Please configure an email account in Email Setup first.",
                parent=self.root)
            self._nb.select(self._settings_tab)
            return
        today = date.today()
        month_year = today.strftime("%Y-%m")
        
        if self.db.already_sent_today(month_year):
            msg = (
                f"Reminders for {today.strftime('%B %Y')} were ALREADY SENT today.\n\n"
                "Are you sure you want to send them AGAIN to all active clients?"
            )
            title = "Warning: Already Sent"
            icon = "warning"
        else:
            msg = (
                f"Send compliance reminders for {today.strftime('%B %Y')} "
                "to all active clients with consent?"
            )
            title = "Confirm Send"
            icon = "question"

        if not messagebox.askyesno(
            title,
            msg,
            icon=icon,
            parent=self.root,
        ):
            return
        threading.Thread(target=self._run_send,
                         kwargs={"force": True}, daemon=True).start()

    def _resume_unsent(self) -> None:
        if self._sending:
            messagebox.showinfo("In Progress", "A send job is already running.", parent=self.root)
            return
        if not self.db.get_active_email_account():
            messagebox.showwarning("No Email Account", "Please configure an email account in Email Setup first.", parent=self.root)
            self._nb.select(self._settings_tab)
            return
            
        today = date.today()
        msg = (
            f"Send compliance reminders for {today.strftime('%B %Y')} "
            "ONLY to clients who have NOT received them yet?\n\n"
            "(This is safe to use if the previous send failed or was interrupted)"
        )
        if not messagebox.askyesno("Resume Unsent", msg, icon="question", parent=self.root):
            return
            
        threading.Thread(target=self._run_send,
                         kwargs={"force": True, "resume_unsent": True}, daemon=True).start()

    def _on_closing(self) -> None:
        if self._sending:
            msg = (
                "Emails are currently being sent!\n\n"
                "Closing the app right now may result in duplicate emails being sent next time "
                "because the database logs might not complete in time.\n\n"
                "Are you sure you want to exit immediately?"
            )
            if not messagebox.askyesno("Warning: Sending in Progress", msg, icon="warning", parent=self.root):
                return
        self.root.destroy()

    # ── Database backup / restore ─────────────────────────────────────────────

    def _backup_db(self) -> None:
        today_str = date.today().strftime("%Y%m%d")
        path = filedialog.asksaveasfilename(
            title="Save Database Backup",
            initialfile=f"ca_compliance_backup_{today_str}.db",
            defaultextension=".db",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
            parent=self.root,
        )
        if not path:
            return
        try:
            shutil.copy2(str(DB_PATH), path)
            messagebox.showinfo(
                "Backup Saved",
                f"Database backed up to:\n{path}\n\n"
                "Keep this file safe — it contains your encrypted client data.",
                parent=self.root,
            )
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc), parent=self.root)

    def _restore_db(self) -> None:
        path = filedialog.askopenfilename(
            title="Restore Database from Backup",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
            parent=self.root,
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Confirm Restore",
            "Restore database from backup?\n\n"
            "This will REPLACE your current database with the backup.\n"
            "All changes made after the backup was created will be lost.\n\n"
            "The app will reload after restore.",
            icon="warning", parent=self.root,
        ):
            return
        try:
            self.db.close()
            shutil.copy2(path, str(DB_PATH))
            self.db.initialize()
            # Refresh all tabs
            self._clients_tab.refresh()
            self._comp_tab.refresh()
            self._refresh_dash_log()
            messagebox.showinfo(
                "Restore Complete",
                "Database restored successfully.",
                parent=self.root,
            )
        except Exception as exc:
            messagebox.showerror("Restore Failed", str(exc), parent=self.root)
            try:
                self.db.initialize()
            except Exception:
                pass
