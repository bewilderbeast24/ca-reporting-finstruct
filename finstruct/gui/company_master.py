"""Entity Master form — all entity types."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from ..config import THEME as T
from ..gui.theme import label, entry, card, primary_btn, secondary_btn
from ..core.entity_types import EntityType, ENTITY_LABELS, AOP_SUBTYPES, TRUST_SUBTYPES
from ..core.validator import validate_cin, validate_fy, validate_pan


class CompanyMasterForm(ttk.Frame):
    def __init__(self, parent, db, on_save: callable = None):
        super().__init__(parent)
        self._db    = db
        self._on_save = on_save
        self._vars: dict[str, tk.StringVar] = {}
        self.configure(style="TFrame")
        self._build()
        self._load()

    def _field(self, parent, row: int, key: str, label_text: str, width: int = 40,
               required: bool = False) -> ttk.Entry:
        lbl = "*" + label_text if required else label_text
        ttk.Label(parent, text=lbl, style="TLabel").grid(
            row=row, column=0, sticky="w", padx=6, pady=3)
        var = tk.StringVar()
        self._vars[key] = var
        e = ttk.Entry(parent, textvariable=var, width=width)
        e.grid(row=row, column=1, sticky="ew", padx=6, pady=3)
        return e

    def _combo(self, parent, row: int, key: str, label_text: str,
               values: list) -> ttk.Combobox:
        ttk.Label(parent, text=label_text, style="TLabel").grid(
            row=row, column=0, sticky="w", padx=6, pady=3)
        var = tk.StringVar()
        self._vars[key] = var
        cb = ttk.Combobox(parent, textvariable=var, values=values,
                          state="readonly", width=38)
        cb.grid(row=row, column=1, sticky="ew", padx=6, pady=3)
        return cb

    def _build(self):
        entity_type = self._db.get_meta("entity_type") or "COMPANY"

        # Scrollable canvas
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        r = 0
        # ── Entity Info ─────────────────────────────────────────────────
        ttk.Label(inner, text="Entity Information",
                  style="Sec.TLabel").grid(row=r, column=0, columnspan=2,
                                           sticky="ew", pady=(8, 4), padx=6)
        r += 1
        self._field(inner, r, "entity_name", "Entity / Company Name", required=True); r += 1
        self._field(inner, r, "financial_year", "Financial Year (YYYY-YY)", required=True); r += 1
        self._field(inner, r, "pan", "PAN"); r += 1
        self._field(inner, r, "address", "Registered / Principal Office", width=50); r += 1

        if entity_type == "COMPANY":
            self._field(inner, r, "cin",  "CIN (21 chars)"); r += 1
            self._field(inner, r, "date_of_incorp", "Date of Incorporation"); r += 1
            self._combo(inner, r, "entity_subtype", "Company Subtype",
                        ["Regular Company", "Small Company", "OPC", "Dormant"]); r += 1
        elif entity_type == "LLP":
            self._field(inner, r, "llpin", "LLPIN"); r += 1
            self._field(inner, r, "date_of_reg", "Date of Registration"); r += 1
        elif entity_type in ("PROP",):
            self._field(inner, r, "prop_name", "Proprietor Name"); r += 1
        elif entity_type == "PART":
            self._field(inner, r, "partner1_name", "Partner 1 Name"); r += 1
            self._field(inner, r, "partner1_ratio", "Partner 1 P/L Ratio (%)"); r += 1
            self._field(inner, r, "partner2_name", "Partner 2 Name"); r += 1
            self._field(inner, r, "partner2_ratio", "Partner 2 P/L Ratio (%)"); r += 1
        elif entity_type == "AOP":
            self._combo(inner, r, "entity_subtype", "AOP Subtype", AOP_SUBTYPES); r += 1
            self._field(inner, r, "reg_no", "Registration No."); r += 1
            self._field(inner, r, "president_name", "President / Chairperson"); r += 1
            self._field(inner, r, "secretary_name", "Honorary Secretary"); r += 1
            self._field(inner, r, "treasurer_name", "Treasurer"); r += 1
        elif entity_type in ("TRUST", "SEC8"):
            self._field(inner, r, "trust_deed_date", "Trust Deed / Reg Date"); r += 1
            self._field(inner, r, "reg_no", "Registration No."); r += 1

        ttk.Separator(inner, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=8, padx=6)
        r += 1

        # ── Directors / Signatories ──────────────────────────────────────
        if entity_type in ("COMPANY", "SEC8"):
            ttk.Label(inner, text="Directors & KMP",
                      style="Sec.TLabel").grid(row=r, column=0, columnspan=2,
                                               sticky="ew", pady=(4, 2), padx=6)
            r += 1
            for i in range(1, 3):
                self._field(inner, r, f"dir{i}_name",  f"Director {i} Name"); r += 1
                self._field(inner, r, f"dir{i}_desig", f"Director {i} Designation"); r += 1
                self._field(inner, r, f"dir{i}_din",   f"Director {i} DIN"); r += 1
            self._field(inner, r, "cfo_name", "CFO Name"); r += 1
            self._field(inner, r, "cs_name",  "Company Secretary Name"); r += 1
            self._field(inner, r, "cs_memno", "CS Membership No."); r += 1
            ttk.Separator(inner, orient="horizontal").grid(
                row=r, column=0, columnspan=2, sticky="ew", pady=8, padx=6)
            r += 1

        # ── Auditor Block ────────────────────────────────────────────────
        ttk.Label(inner, text="Auditor Details",
                  style="Sec.TLabel").grid(row=r, column=0, columnspan=2,
                                           sticky="ew", pady=(4, 2), padx=6)
        r += 1
        self._field(inner, r, "auditor_firm",    "Auditor Firm Name"); r += 1
        self._field(inner, r, "auditor_frn",     "Firm Reg No (FRN)"); r += 1
        self._field(inner, r, "auditor_partner", "Partner Name"); r += 1
        self._field(inner, r, "auditor_mrn",     "Membership No (MRN)"); r += 1
        self._field(inner, r, "signing_place",   "Signing Place"); r += 1
        self._field(inner, r, "signing_date",    "Signing Date (DD-Mon-YYYY)"); r += 1
        r += 1

        # ── Buttons ──────────────────────────────────────────────────────
        btn_frame = ttk.Frame(inner)
        btn_frame.grid(row=r, column=0, columnspan=2, sticky="ew", padx=6, pady=10)
        primary_btn(btn_frame, "💾  Save", command=self._save).pack(side="left", padx=4)
        secondary_btn(btn_frame, "↺  Reset", command=self._load).pack(side="left", padx=4)

        inner.columnconfigure(1, weight=1)

    def _load(self):
        data = self._db.get_all_entity()
        for key, var in self._vars.items():
            var.set(data.get(key, ""))

    def _save(self):
        data = {k: v.get().strip() for k, v in self._vars.items()}

        errors = []
        if not data.get("entity_name"):
            errors.append("Entity Name is mandatory.")
        if data.get("financial_year") and not validate_fy(data["financial_year"]):
            errors.append("Financial Year must be YYYY-YY format (e.g. 2024-25).")
        if data.get("cin") and not validate_cin(data["cin"]):
            errors.append("CIN must be exactly 21 characters.")
        if data.get("pan") and not validate_pan(data["pan"]):
            errors.append("PAN format invalid (e.g. ABCDE1234F).")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        self._db.save_entity_batch(data)
        if data.get("financial_year"):
            self._db.set_meta("financial_year", data["financial_year"])
        self._db.log("ENTITY_MASTER_SAVED", "")
        messagebox.showinfo("Saved", "Entity master saved successfully.")
        if self._on_save:
            self._on_save(data)
