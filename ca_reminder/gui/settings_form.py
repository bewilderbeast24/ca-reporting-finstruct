"""
Email Setup tab — Apple-style clean form.

Segmented provider selector · card layout · inline Test Connection.
Supports STARTTLS (port 587) and SSL (port 465) — auto-selects port
when the encryption mode changes.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from ca_reminder.config import EMAIL_PROVIDERS, SMTP_DEFAULT_PORTS, SMTP_ENCRYPTION_OPTIONS
from ca_reminder.core.mailer import test_smtp_connection
from ca_reminder.data.database import Database
from ca_reminder.gui import theme as T


class SettingsForm(tk.Frame):

    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, bg=T.BG, **kwargs)
        self.db = db
        self._account_id: Optional[int] = None
        self._provider_var = tk.StringVar(value="gmail")
        self._build()
        self._refresh_list()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Scroll wrapper
        canvas = tk.Canvas(self, bg=T.BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=T.BG)
        win  = canvas.create_window((0, 0), window=body, anchor="nw")

        body.bind("<Configure>",
                  lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))

        self._build_body(body)

    def _build_body(self, parent: tk.Frame) -> None:
        px = T.PAD_L

        # ── Page title ────────────────────────────────────────────────────────
        tk.Label(parent, text="Email Setup",
                 font=T.F_HEADING, fg=T.TEXT, bg=T.BG,
                 padx=px, pady=T.PAD).pack(anchor="w")
        tk.Label(parent,
                 text="Configure the outgoing email account used to send reminders.",
                 font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG,
                 padx=px).pack(anchor="w")
        T.divider(parent).pack(fill="x", padx=px, pady=T.PAD)

        # ── Provider selector (segmented-button style) ────────────────────────
        T.section_header(parent, "Email Provider").pack(
            fill="x", padx=px, pady=(0, T.PAD_S))

        seg = tk.Frame(parent, bg=T.BG, padx=px)
        seg.pack(anchor="w", pady=(0, T.PAD))
        self._prov_btns: dict[str, tk.Button] = {}
        for key, info in EMAIL_PROVIDERS.items():
            b = tk.Button(
                seg,
                text=info["name"],
                font=T.F_BODY,
                relief="solid", bd=1,
                padx=14, pady=6,
                cursor="hand2",
                command=lambda k=key: self._select_provider(k),
            )
            b.pack(side="left", padx=(0, 2))
            self._prov_btns[key] = b

        # ── Help / setup instructions ─────────────────────────────────────────
        self._help_var = tk.StringVar()
        self._help_lbl = tk.Label(
            parent, textvariable=self._help_var,
            font=T.F_CAPTION, fg=T.TEXT_SEC, bg=T.BG_ALT,
            justify="left", wraplength=700,
            padx=px, pady=T.PAD_S, anchor="nw",
        )
        self._help_lbl.pack(fill="x", padx=px, pady=(0, T.PAD))

        # ── Form card ─────────────────────────────────────────────────────────
        form_card = T.card(parent)
        form_card.pack(fill="x", padx=px, pady=(0, T.PAD),
                       ipadx=T.PAD, ipady=T.PAD)

        left  = tk.Frame(form_card, bg=T.BG)
        right = tk.Frame(form_card, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(T.PAD, T.PAD_L), pady=T.PAD)
        right.pack(side="left", fill="both", expand=True, padx=(0, T.PAD), pady=T.PAD)

        def _field(par, label_text, show=""):
            tk.Label(par, text=label_text, font=T.F_CAPTION,
                     fg=T.TEXT_SEC, bg=T.BG, anchor="w").pack(
                fill="x", pady=(T.PAD_S, 2))
            e = T.entry(par, width=34, show=show)
            e.pack(fill="x")
            return e

        # Left column — identity
        T.section_header(left, "Identity").pack(fill="x", pady=(0, T.PAD_S))
        self._display_name = _field(left, "Account Label")
        self._sender_name  = _field(left, "Sender Name  (appears in From:)")
        self._email_addr   = _field(left, "Email Address *")
        self._username     = _field(left, "SMTP Username  (usually same as email)")
        self._password     = _field(left, "App Password *", show="•")

        # Right column — SMTP server
        T.section_header(right, "SMTP Server").pack(fill="x", pady=(0, T.PAD_S))
        self._smtp_host = _field(right, "SMTP Host")
        self._smtp_port = _field(right, "SMTP Port")

        # Encryption dropdown (STARTTLS / SSL / None)
        tk.Label(right, text="Encryption", font=T.F_CAPTION,
                 fg=T.TEXT_SEC, bg=T.BG, anchor="w").pack(fill="x", pady=(T.PAD_S, 2))
        self._enc_var = tk.StringVar(value="STARTTLS")
        enc_cb = ttk.Combobox(
            right, textvariable=self._enc_var,
            values=SMTP_ENCRYPTION_OPTIONS,
            state="readonly", width=22, font=T.F_BODY,
        )
        enc_cb.pack(fill="x")
        enc_cb.bind("<<ComboboxSelected>>", self._on_enc_change)

        tk.Label(
            right,
            text="Port 587 → STARTTLS   |   Port 465 → SSL",
            font=T.F_CAPTION, fg=T.TEXT_LIGHT, bg=T.BG,
        ).pack(anchor="w", pady=(3, 0))

        # All form fields created — safe to set provider default
        self._select_provider("gmail")

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = tk.Frame(parent, bg=T.BG, padx=px)
        btn_row.pack(anchor="w", pady=(0, T.PAD_L))
        T.btn(btn_row, "Test Connection", self._test,  style="secondary").pack(side="left", padx=(0, 6))
        T.btn(btn_row, "Save Account",    self._save,  style="primary").pack(side="left", padx=(0, 6))
        T.btn(btn_row, "Clear",           self._clear, style="ghost").pack(side="left")

        # ── Saved accounts ────────────────────────────────────────────────────
        T.divider(parent).pack(fill="x", padx=px)
        T.section_header(parent, "Saved Accounts").pack(
            fill="x", padx=px, pady=(T.PAD, T.PAD_S))

        list_card = T.card(parent)
        list_card.pack(fill="x", padx=px, pady=(0, T.PAD),
                       ipadx=1, ipady=1)

        cols = ("display_name", "provider", "email_address", "encryption")
        self._acct_tree = ttk.Treeview(list_card, columns=cols,
                                        show="headings", height=4,
                                        style="Treeview")
        for col, hdr_txt, w in [
            ("display_name",  "Label",      170),
            ("provider",      "Provider",   130),
            ("email_address", "Email",      240),
            ("encryption",    "Encryption",  90),
        ]:
            self._acct_tree.heading(col, text=hdr_txt)
            self._acct_tree.column(col, width=w, anchor="w")

        vsb2 = ttk.Scrollbar(list_card, orient="vertical",
                              command=self._acct_tree.yview)
        self._acct_tree.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y")
        self._acct_tree.pack(fill="x", padx=1, pady=1)

        acct_btns = tk.Frame(parent, bg=T.BG, padx=px)
        acct_btns.pack(anchor="w", pady=(0, T.PAD))
        T.btn(acct_btns, "Load Selected",   self._load_selected,   style="secondary").pack(side="left", padx=(0, 6))
        T.btn(acct_btns, "Delete Selected", self._delete_selected, style="danger").pack(side="left")

    # ── Provider selector ─────────────────────────────────────────────────────

    def _select_provider(self, key: str) -> None:
        self._provider_var.set(key)
        for k, btn in self._prov_btns.items():
            if k == key:
                btn.configure(bg=T.ACCENT, fg="white",
                               activebackground=T.ACCENT_DARK,
                               activeforeground="white")
            else:
                btn.configure(bg=T.BG, fg=T.TEXT,
                               activebackground=T.BG_HOVER,
                               activeforeground=T.TEXT)

        preset = EMAIL_PROVIDERS.get(key, {})
        self._smtp_host.delete(0, "end")
        self._smtp_host.insert(0, preset.get("smtp_host", ""))

        # Set encryption first so port auto-fill is correct
        enc = preset.get("encryption", "STARTTLS")
        self._enc_var.set(enc)

        self._smtp_port.delete(0, "end")
        self._smtp_port.insert(0, str(preset.get("smtp_port", SMTP_DEFAULT_PORTS.get(enc, 587))))

        self._help_var.set(preset.get("help", ""))

    # ── Encryption change → auto-suggest port ─────────────────────────────────

    def _on_enc_change(self, _e=None) -> None:
        enc = self._enc_var.get()
        default_port = str(SMTP_DEFAULT_PORTS.get(enc, 587))
        current_port = self._smtp_port.get().strip()
        # Only auto-update if the port is still one of the standard defaults
        if current_port in ("587", "465", "25", ""):
            self._smtp_port.delete(0, "end")
            self._smtp_port.insert(0, default_port)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _test(self) -> None:
        acct = self._collect()
        if not acct:
            return
        ok, msg = test_smtp_connection(acct)
        if ok:
            messagebox.showinfo("Connection Test", msg, parent=self)
        else:
            messagebox.showerror("Connection Failed", msg, parent=self)

    def _save(self) -> None:
        acct = self._collect()
        if not acct:
            return
        if self._account_id:
            acct["id"] = self._account_id
        self.db.save_email_account(acct)
        self._account_id = None
        messagebox.showinfo("Saved",
                            "Email account saved successfully.", parent=self)
        self._refresh_list()

    def _clear(self) -> None:
        self._account_id = None
        for entry in (self._display_name, self._sender_name, self._email_addr,
                      self._username, self._password):
            entry.delete(0, "end")
        self._select_provider("gmail")

    def _load_selected(self) -> None:
        sel = self._acct_tree.selection()
        if not sel:
            return
        acct_id = int(self._acct_tree.item(sel[0])["tags"][0])
        acct    = next(
            (a for a in self.db.get_all_email_accounts() if a["id"] == acct_id),
            None,
        )
        if not acct:
            return
        self._account_id = acct_id
        self._fill(acct)

    def _delete_selected(self) -> None:
        sel = self._acct_tree.selection()
        if not sel:
            return
        if not messagebox.askyesno(
            "Delete Account",
            "Delete this email account?", parent=self
        ):
            return
        acct_id = int(self._acct_tree.item(sel[0])["tags"][0])
        self.db.delete_email_account(acct_id)
        self._refresh_list()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _collect(self) -> Optional[dict]:
        email    = self._email_addr.get().strip()
        password = self._password.get().strip()
        host     = self._smtp_host.get().strip()
        if not email or not password or not host:
            messagebox.showwarning(
                "Missing Fields",
                "Email, App Password, and SMTP Host are required.",
                parent=self,
            )
            return None
        try:
            port = int(self._smtp_port.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port",
                                 "SMTP port must be a number.", parent=self)
            return None
        enc = self._enc_var.get()
        return {
            "display_name":  self._display_name.get().strip() or email,
            "sender_name":   self._sender_name.get().strip(),
            "email_address": email,
            "username":      self._username.get().strip() or email,
            "password":      password,
            "provider":      self._provider_var.get(),
            "smtp_host":     host,
            "smtp_port":     port,
            "encryption":    enc,
            "use_tls":       enc == "STARTTLS",   # kept for back-compat
        }

    def _fill(self, acct: dict) -> None:
        self._select_provider(acct.get("provider", "gmail"))
        for entry, key in [
            (self._display_name, "display_name"),
            (self._sender_name,  "sender_name"),
            (self._email_addr,   "email_address"),
            (self._username,     "username"),
            (self._password,     "password"),
            (self._smtp_host,    "smtp_host"),
            (self._smtp_port,    "smtp_port"),
        ]:
            entry.delete(0, "end")
            entry.insert(0, str(acct.get(key, "")))
        enc = acct.get("encryption") or ("STARTTLS" if acct.get("use_tls", True) else "None")
        self._enc_var.set(enc)

    def _refresh_list(self) -> None:
        for row in self._acct_tree.get_children():
            self._acct_tree.delete(row)
        for acct in self.db.get_all_email_accounts():
            enc = acct.get("encryption") or ("STARTTLS" if acct.get("use_tls", True) else "None")
            self._acct_tree.insert(
                "", "end",
                values=(acct["display_name"],
                        acct["provider"],
                        acct["email_address"],
                        enc),
                tags=(str(acct["id"]),),
            )
