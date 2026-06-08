"""Notes to Accounts generator — ported from Engine_Notes.gs."""

from __future__ import annotations
from dataclasses import dataclass, field
from core.fs_engine import FSLine, _line, _sec, _hdr, _tot, _grand, _blank


@dataclass
class Note:
    number: int
    title: str
    lines: list[FSLine] = field(default_factory=list)


def _dl(label, cy, py, indent=1, note=None) -> FSLine:
    return _line(label, cy, py, note, indent, "DATA")


def _tl(label, cy, py) -> FSLine:
    return _tot(label, cy, py)


def _hl(label) -> FSLine:
    return _line(label, 0, 0, indent=0, row_type="SECTION")


class NotesEngine:
    def __init__(self, totals: dict[str, tuple[float, float]], entity_type: str,
                 ppe_data: list | None = None, divisor: int = 1,
                 entity_master: dict | None = None):
        self._t      = totals
        self._etype  = entity_type
        self._ppe    = ppe_data or []
        self._div    = divisor
        self._em     = entity_master or {}

    def _cy(self, code: str) -> float:
        v = self._t.get(code, (0.0, 0.0))[0]
        return round(v / self._div, 2) if self._div else v

    def _py(self, code: str) -> float:
        v = self._t.get(code, (0.0, 0.0))[1]
        return round(v / self._div, 2) if self._div else v

    def _sum_cy(self, codes: list[str]) -> float:
        return round(sum(self._cy(c) for c in codes), 2)

    def _sum_py(self, codes: list[str]) -> float:
        return round(sum(self._py(c) for c in codes), 2)

    def generate_all(self) -> list[Note]:
        """Generate notes WITHOUT renumbering — preserves FS line ↔ note number links."""
        if self._etype in ("COMPANY", "SEC8"):
            return self._company_notes()
        elif self._etype in ("PROP", "PART", "LLP"):
            return self._nce_notes()
        elif self._etype in ("AOP",):
            return self._aop_notes()
        elif self._etype in ("TRUST",):
            return self._trust_notes()
        return []

    def generate_dynamic(self, doc=None) -> tuple[list[Note], dict[int, int]]:
        """xlsm-style: skip empty notes + renumber sequentially.

        Returns (notes, old_to_new_map). If `doc` is given, mutates its FSLines
        to remap each `.note` attribute via the mapping so labels stay in sync.

        Notes 1 & 2 are reserved (Accounting Policies / General Info).
        """
        raw_notes = self.generate_all()
        kept: list[Note] = []
        mapping: dict[int, int] = {}
        next_num = 3
        for note in raw_notes:
            if note.number in (1, 2):
                mapping[note.number] = note.number
                kept.append(note)
                continue
            has_data = any(
                (abs(getattr(line, "cy", 0) or 0) > 0.005 or
                 abs(getattr(line, "py", 0) or 0) > 0.005)
                for line in note.lines
            )
            if not has_data:
                title_lower = note.title.lower()
                placeholder_keep = any(k in title_lower for k in (
                    "related party", "contingent", "events after",
                    "earnings per share", "accounting polic", "general info",
                ))
                if not placeholder_keep:
                    continue
            old_no = note.number
            mapping[old_no] = next_num
            note.number = next_num
            next_num += 1
            kept.append(note)
        if doc is not None:
            for section in ("bs", "pl", "ie", "rp", "cf"):
                lines = getattr(doc, section, None) or []
                for line in lines:
                    if line.note is None:
                        continue
                    if line.note in mapping:
                        line.note = mapping[line.note]
                    else:
                        # Note was dropped (had no data) — clear stale reference
                        line.note = None
        return kept, mapping

    # ─── Company Notes ─────────────────────────────────────────────────────

    def _company_notes(self) -> list[Note]:
        notes = []

        # Note 1: Accounting Policies
        n1 = Note(1, "Significant Accounting Policies")
        n1.lines = [
            _line("1.1 Basis of preparation", 0, 0, row_type="TEXT", indent=1),
            _line("These financial statements have been prepared in accordance with the Generally "
                  "Accepted Accounting Principles in India (Indian GAAP) / Indian Accounting "
                  "Standards (Ind AS), as applicable, under the historical cost convention on "
                  "accrual basis.", 0, 0, row_type="TEXT", indent=2),
            _blank(),
            _line("1.2 Property, Plant & Equipment", 0, 0, row_type="TEXT", indent=1),
            _line("PPE is stated at cost less accumulated depreciation. Depreciation is provided "
                  "on Straight Line / Written Down Value method at rates prescribed under Schedule II "
                  "of the Companies Act, 2013.", 0, 0, row_type="TEXT", indent=2),
            _blank(),
            _line("1.3 Inventories", 0, 0, row_type="TEXT", indent=1),
            _line("Inventories are valued at the lower of cost and net realisable value. "
                  "Cost is determined on FIFO / Weighted Average basis.", 0, 0, row_type="TEXT", indent=2),
            _blank(),
            _line("1.4 Revenue Recognition", 0, 0, row_type="TEXT", indent=1),
            _line("Revenue from sale of goods is recognised when the significant risks and rewards "
                  "of ownership of goods are transferred to the buyer. Revenue from services is "
                  "recognised as per the terms of the contract.", 0, 0, row_type="TEXT", indent=2),
            _blank(),
            _line("1.5 Taxation", 0, 0, row_type="TEXT", indent=1),
            _line("Current tax is determined as the amount of tax payable in respect of taxable "
                  "income for the year. Deferred tax is recognised on timing differences.", 0, 0, row_type="TEXT", indent=2),
        ]
        notes.append(n1)

        # Note 2: General Information
        n2 = Note(2, "General Information")
        n2.lines = [
            _line("[Company was incorporated on __ / __/ ____. CIN: __________. "
                  "Registered Office: _______. The Company is primarily engaged in ______.]",
                  0, 0, row_type="TEXT", indent=1),
        ]
        notes.append(n2)

        # Note 3: Share Capital
        n3 = Note(3, "Share Capital")
        eq_cy = self._cy("CO_EL001"); eq_py = self._py("CO_EL001")
        pref_cy = self._cy("CO_EL002"); pref_py = self._py("CO_EL002")
        n3.lines = [
            _hl("Authorised:"),
            _dl("[X] Equity Shares of ₹10/- each", 0, 0),
            _hl("Issued, Subscribed & Paid-up:"),
            _dl("Equity Shares of ₹10/- each fully paid up", eq_cy, eq_py),
            _dl("Preference Shares", pref_cy, pref_py),
            _tl("Total", eq_cy + pref_cy, eq_py + pref_py),
            _blank(),
            _line("Movement in Share Capital:", 0, 0, row_type="TEXT", indent=0),
            _dl("Opening Balance", eq_py, 0),
            _dl("Add: Issued during the year", eq_cy - eq_py, 0),
            _tl("Closing Balance", eq_cy, eq_py),
        ]
        notes.append(n3)

        # Note 4: Reserves & Surplus
        n4 = Note(4, "Reserves and Surplus")
        cr_cy = self._cy("CO_EL003"); cr_py = self._py("CO_EL003")
        crr_cy= self._cy("CO_EL004"); crr_py= self._py("CO_EL004")
        spr_cy= self._cy("CO_EL005"); spr_py= self._py("CO_EL005")
        gr_cy = self._cy("CO_EL006"); gr_py = self._py("CO_EL006")
        re_cy = self._cy("CO_EL007"); re_py = self._py("CO_EL007")
        tot_cy= cr_cy+crr_cy+spr_cy+gr_cy+re_cy
        tot_py= cr_py+crr_py+spr_py+gr_py+re_py
        n4.lines = [
            _dl("Capital Reserve", cr_cy, cr_py),
            _dl("Capital Redemption Reserve", crr_cy, crr_py),
            _dl("Securities Premium Reserve", spr_cy, spr_py),
            _dl("General Reserve", gr_cy, gr_py),
            _dl("Retained Earnings / Surplus in P&L", re_cy, re_py),
            _tl("Total", tot_cy, tot_py),
        ]
        notes.append(n4)

        # Note 5: Long-Term Borrowings
        n5 = Note(5, "Long-Term Borrowings")
        ltb_codes = ["CO_EL010","CO_EL011","CO_EL012","CO_EL013","CO_EL014","CO_EL015"]
        n5.lines = [
            _dl("Term Loans from Banks (Secured)", self._cy("CO_EL010"), self._py("CO_EL010")),
            _dl("Term Loans from Financial Institutions", self._cy("CO_EL011"), self._py("CO_EL011")),
            _dl("Bonds / Debentures", self._cy("CO_EL012"), self._py("CO_EL012")),
            _dl("Deposits", self._cy("CO_EL013"), self._py("CO_EL013")),
            _dl("Loans from Related Parties", self._cy("CO_EL014"), self._py("CO_EL014")),
            _dl("Other Long-term Borrowings", self._cy("CO_EL015"), self._py("CO_EL015")),
            _tl("Total", self._sum_cy(ltb_codes), self._sum_py(ltb_codes)),
        ]
        notes.append(n5)

        # Note 6: Other Long-term Liabilities
        n6 = Note(6, "Other Long-term Liabilities")
        n6.lines = [
            _dl("Advance from Customers (long-term)", self._cy("CO_EL017"), self._py("CO_EL017")),
            _tl("Total", self._cy("CO_EL017"), self._py("CO_EL017")),
        ]
        notes.append(n6)

        # Note 7: Long-term Provisions
        n7 = Note(7, "Long-term Provisions")
        ltp_cy = self._cy("CO_EL018") + self._cy("CO_EL019")
        ltp_py = self._py("CO_EL018") + self._py("CO_EL019")
        n7.lines = [
            _dl("Provision for Employee Benefits (Gratuity / Leave)", self._cy("CO_EL018"), self._py("CO_EL018")),
            _dl("Other Long-term Provisions", self._cy("CO_EL019"), self._py("CO_EL019")),
            _tl("Total", ltp_cy, ltp_py),
        ]
        notes.append(n7)

        # Note 8: Short-Term Borrowings
        n8 = Note(8, "Short-Term Borrowings")
        stb_codes = ["CO_EL020","CO_EL021","CO_EL022","CO_EL023","CO_EL024"]
        n8.lines = [
            _dl("Cash Credit / Overdraft from Banks", self._cy("CO_EL020"), self._py("CO_EL020")),
            _dl("Short-term Loans from Banks", self._cy("CO_EL021"), self._py("CO_EL021")),
            _dl("Current Maturities of Long-term Debt", self._cy("CO_EL022"), self._py("CO_EL022")),
            _dl("Loans from Directors / Related Parties", self._cy("CO_EL023"), self._py("CO_EL023")),
            _dl("Other Short-term Borrowings", self._cy("CO_EL024"), self._py("CO_EL024")),
            _tl("Total", self._sum_cy(stb_codes), self._sum_py(stb_codes)),
        ]
        notes.append(n8)

        # Note 9: Trade Payables
        n9 = Note(9, "Trade Payables")
        n9.lines = [
            _dl("Trade Payables – MSME", self._cy("CO_EL025"), self._py("CO_EL025")),
            _dl("Trade Payables – Others", self._cy("CO_EL026"), self._py("CO_EL026")),
            _tl("Total", self._cy("CO_EL025")+self._cy("CO_EL026"), self._py("CO_EL025")+self._py("CO_EL026")),
            _blank(),
            _line("Ageing Schedule — Trade Payables:", 0, 0, row_type="TEXT"),
            _line("(Outstanding for following periods from due date of payment)", 0, 0, row_type="TEXT"),
        ]
        notes.append(n9)

        # Note 10: Other Current Liabilities
        n10 = Note(10, "Other Current Liabilities")
        ocl_codes = ["CO_EL027","CO_EL028","CO_EL029","CO_EL030","CO_EL031"]
        n10.lines = [
            _dl("Current Maturities of Finance Lease Obligations", self._cy("CO_EL027"), self._py("CO_EL027")),
            _dl("Interest Accrued but Not Due on Borrowings", self._cy("CO_EL028"), self._py("CO_EL028")),
            _dl("Unpaid Dividends", self._cy("CO_EL029"), self._py("CO_EL029")),
            _dl("Advance from Customers (current)", self._cy("CO_EL030"), self._py("CO_EL030")),
            _dl("Other Payables (statutory dues, salary payable, etc.)", self._cy("CO_EL031"), self._py("CO_EL031")),
            _tl("Total", self._sum_cy(ocl_codes), self._sum_py(ocl_codes)),
        ]
        notes.append(n10)

        # Note 11: Short-term Provisions
        n11 = Note(11, "Short-term Provisions")
        stp_codes = ["CO_EL032","CO_EL033","CO_EL034"]
        n11.lines = [
            _dl("Provision for Income Tax (Net of Advance Tax)", self._cy("CO_EL032"), self._py("CO_EL032")),
            _dl("Provision for Employee Benefits", self._cy("CO_EL033"), self._py("CO_EL033")),
            _dl("Other Short-term Provisions", self._cy("CO_EL034"), self._py("CO_EL034")),
            _tl("Total", self._sum_cy(stp_codes), self._sum_py(stp_codes)),
        ]
        notes.append(n11)

        # Note 12: PPE Schedule
        n12 = Note(12, "Property, Plant and Equipment")
        if self._ppe:
            n12.lines = self._ppe_note_lines()
        else:
            n12.lines = [_line("(Refer PPE Register — complete asset register data)", 0, 0, row_type="TEXT")]
        notes.append(n12)

        # Note 13: Non-Current Investments
        n13 = Note(13, "Non-Current Investments")
        nci_codes = ["CO_AS006","CO_AS007","CO_AS008"]
        n13.lines = [
            _dl("Investment in Subsidiaries / Associates (at cost)", self._cy("CO_AS006"), self._py("CO_AS006")),
            _dl("Investment in Equity Instruments (others)", self._cy("CO_AS007"), self._py("CO_AS007")),
            _dl("Investment in Government Securities / Bonds", self._cy("CO_AS008"), self._py("CO_AS008")),
            _tl("Total", self._sum_cy(nci_codes), self._sum_py(nci_codes)),
        ]
        notes.append(n13)

        # Note 14: Long-term Loans & Advances
        n14 = Note(14, "Long-term Loans and Advances")
        ltla_codes = ["CO_AS010","CO_AS011","CO_AS012"]
        n14.lines = [
            _dl("Capital Advances (unsecured, considered good)", self._cy("CO_AS010"), self._py("CO_AS010")),
            _dl("Security Deposits", self._cy("CO_AS011"), self._py("CO_AS011")),
            _dl("Other Long-term Loans & Advances", self._cy("CO_AS012"), self._py("CO_AS012")),
            _tl("Total", self._sum_cy(ltla_codes), self._sum_py(ltla_codes)),
        ]
        notes.append(n14)

        # Note 15: Other Non-Current Assets
        n15 = Note(15, "Other Non-Current Assets")
        n15.lines = [
            _dl("Long-term Trade Receivables (considered good)", self._cy("CO_AS013"), self._py("CO_AS013")),
            _dl("Unamortised Expenses / Miscellaneous Expenditure", self._cy("CO_AS014"), self._py("CO_AS014")),
            _tl("Total", self._cy("CO_AS013")+self._cy("CO_AS014"), self._py("CO_AS013")+self._py("CO_AS014")),
        ]
        notes.append(n15)

        # Note 16: Inventories
        n16 = Note(16, "Inventories")
        inv_codes = ["CO_AS015","CO_AS016","CO_AS017","CO_AS018","CO_AS019"]
        n16.lines = [
            _dl("Raw Materials", self._cy("CO_AS015"), self._py("CO_AS015")),
            _dl("Work-in-Progress", self._cy("CO_AS016"), self._py("CO_AS016")),
            _dl("Finished Goods", self._cy("CO_AS017"), self._py("CO_AS017")),
            _dl("Stock-in-Trade", self._cy("CO_AS018"), self._py("CO_AS018")),
            _dl("Stores, Spares & Packing Material", self._cy("CO_AS019"), self._py("CO_AS019")),
            _tl("Total", self._sum_cy(inv_codes), self._sum_py(inv_codes)),
        ]
        notes.append(n16)

        # Note 17: Trade Receivables
        n17 = Note(17, "Trade Receivables")
        tr_cy = self._cy("CO_AS020") + self._cy("CO_AS021") - self._cy("CO_AS022")
        tr_py = self._py("CO_AS020") + self._py("CO_AS021") - self._py("CO_AS022")
        n17.lines = [
            _dl("Outstanding > 6 months", self._cy("CO_AS020"), self._py("CO_AS020")),
            _dl("Outstanding ≤ 6 months", self._cy("CO_AS021"), self._py("CO_AS021")),
            _dl("Less: Provision for Doubtful Debts", self._cy("CO_AS022"), self._py("CO_AS022")),
            _tl("Total", tr_cy, tr_py),
            _blank(),
            _line("Ageing Schedule — Trade Receivables:", 0, 0, row_type="TEXT"),
        ]
        notes.append(n17)

        # Note 18: Cash & Equivalents
        n18 = Note(18, "Cash and Cash Equivalents")
        cash_cy = self._sum_cy(["CO_AS023","CO_AS024","CO_AS025","CO_AS026"])
        cash_py = self._sum_py(["CO_AS023","CO_AS024","CO_AS025","CO_AS026"])
        n18.lines = [
            _dl("Cash in Hand", self._cy("CO_AS023"), self._py("CO_AS023")),
            _dl("Balances with Banks – Current A/c", self._cy("CO_AS024"), self._py("CO_AS024")),
            _dl("Balances with Banks – Savings A/c", self._cy("CO_AS025"), self._py("CO_AS025")),
            _dl("Fixed Deposits (maturity < 3 months)", self._cy("CO_AS026"), self._py("CO_AS026")),
            _tl("Total", cash_cy, cash_py),
        ]
        notes.append(n18)

        # Note 19: Short-term Loans & Advances
        n19 = Note(19, "Short-term Loans and Advances")
        stla_codes = ["CO_AS027","CO_AS028","CO_AS029","CO_AS030"]
        n19.lines = [
            _dl("Advance to Suppliers (considered good)", self._cy("CO_AS027"), self._py("CO_AS027")),
            _dl("Advance Tax / TDS Receivable (Net)", self._cy("CO_AS028"), self._py("CO_AS028")),
            _dl("Balance with Customs / Excise Authorities", self._cy("CO_AS029"), self._py("CO_AS029")),
            _dl("Other Short-term Loans & Advances", self._cy("CO_AS030"), self._py("CO_AS030")),
            _tl("Total", self._sum_cy(stla_codes), self._sum_py(stla_codes)),
        ]
        notes.append(n19)

        # Note 20: Other Current Assets
        n20 = Note(20, "Other Current Assets")
        n20.lines = [
            _dl("Interest Accrued on Deposits / Investments", self._cy("CO_AS031"), self._py("CO_AS031")),
            _dl("Prepaid Expenses", self._cy("CO_AS032"), self._py("CO_AS032")),
            _dl("Other Current Assets", self._cy("CO_AS033"), self._py("CO_AS033")),
            _tl("Total", self._cy("CO_AS031")+self._cy("CO_AS032")+self._cy("CO_AS033"),
                          self._py("CO_AS031")+self._py("CO_AS032")+self._py("CO_AS033")),
        ]
        notes.append(n20)

        # Note 21: Revenue from Operations
        n21 = Note(21, "Revenue from Operations")
        rev_codes = ["CO_IN001","CO_IN002","CO_IN003"]
        n21.lines = [
            _dl("Sale of Products", self._cy("CO_IN001"), self._py("CO_IN001")),
            _dl("Sale of Services", self._cy("CO_IN002"), self._py("CO_IN002")),
            _dl("Other Operating Revenue", self._cy("CO_IN003"), self._py("CO_IN003")),
            _dl("Less: GST / Excise Duty (if applicable)", self._cy("CO_EX004"), self._py("CO_EX004")),
            _tl("Total", self._sum_cy(rev_codes) - self._cy("CO_EX004"),
                          self._sum_py(rev_codes) - self._py("CO_EX004")),
        ]
        notes.append(n21)

        # Note 22: Other Income  (CO_IN005=Interest, CO_IN006=Dividend, CO_IN007=Profit on Sale)
        n22 = Note(22, "Other Income")
        oi_codes = ["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"]
        n22.lines = [
            _dl("Interest Income", self._cy("CO_IN005"), self._py("CO_IN005")),
            _dl("Dividend Income", self._cy("CO_IN006"), self._py("CO_IN006")),
            _dl("Profit on Sale of Assets", self._cy("CO_IN007"), self._py("CO_IN007")),
            _dl("Rental Income", self._cy("CO_IN008"), self._py("CO_IN008")),
            _dl("Miscellaneous / Other Income", self._cy("CO_IN009"), self._py("CO_IN009")),
            _tl("Total", self._sum_cy(oi_codes), self._sum_py(oi_codes)),
        ]
        notes.append(n22)

        # Note 23: Cost of Materials Consumed
        n23 = Note(23, "Cost of Materials Consumed")
        cl_cy = self._cy("CO_AS015"); cl_py = self._py("CO_AS015")
        n23.lines = [
            _dl("Opening Stock of Raw Materials", self._cy("CO_EX010"), self._py("CO_EX010")),
            _dl("Add: Purchases during the year", self._cy("CO_EX011"), self._py("CO_EX011")),
            _dl("Less: Closing Stock of Raw Materials", cl_cy, cl_py),
            _tl("Cost of Materials Consumed",
                self._cy("CO_EX010") + self._cy("CO_EX011") - cl_cy,
                self._py("CO_EX010") + self._py("CO_EX011") - cl_py),
        ]
        notes.append(n23)

        # Note 24: Purchases of Stock-in-Trade
        n24 = Note(24, "Purchases of Stock-in-Trade")
        n24.lines = [
            _dl("Purchases of Stock-in-Trade", self._cy("CO_EX012"), self._py("CO_EX012")),
            _tl("Total", self._cy("CO_EX012"), self._py("CO_EX012")),
        ]
        notes.append(n24)

        # Note 25: Changes in Inventories
        n25 = Note(25, "Changes in Inventories of Finished Goods, WIP & Stock-in-Trade")
        ch_cy = self._sum_cy(["CO_EX013","CO_EX014"]) - self._sum_cy(["CO_IN015","CO_IN016"])
        ch_py = self._sum_py(["CO_EX013","CO_EX014"]) - self._sum_py(["CO_IN015","CO_IN016"])
        n25.lines = [
            _hl("Opening Stocks:"),
            _dl("Finished Goods", self._cy("CO_EX013"), self._py("CO_EX013")),
            _dl("Work-in-Progress", self._cy("CO_EX014"), self._py("CO_EX014")),
            _hl("Less: Closing Stocks:"),
            _dl("Finished Goods", self._cy("CO_IN015"), self._py("CO_IN015")),
            _dl("Work-in-Progress", self._cy("CO_IN016"), self._py("CO_IN016")),
            _tl("Net Change in Inventories", ch_cy, ch_py),
        ]
        notes.append(n25)

        # Note 26: Employee Benefit Expenses
        n26 = Note(26, "Employee Benefit Expenses")
        emp_codes = ["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"]
        n26.lines = [
            _dl("Salaries & Wages", self._cy("CO_EX017"), self._py("CO_EX017")),
            _dl("Bonus", self._cy("CO_EX018"), self._py("CO_EX018")),
            _dl("PF / ESI Contributions", self._cy("CO_EX019"), self._py("CO_EX019")),
            _dl("Gratuity", self._cy("CO_EX020"), self._py("CO_EX020")),
            _dl("Staff Welfare", self._cy("CO_EX021"), self._py("CO_EX021")),
            _tl("Total", self._sum_cy(emp_codes), self._sum_py(emp_codes)),
        ]
        notes.append(n26)

        # Note 27: Finance Costs
        n27 = Note(27, "Finance Costs")
        fin_codes = ["CO_EX022","CO_EX023","CO_EX024"]
        n27.lines = [
            _dl("Interest on Term Loans", self._cy("CO_EX022"), self._py("CO_EX022")),
            _dl("Interest on Working Capital Facilities", self._cy("CO_EX023"), self._py("CO_EX023")),
            _dl("Bank Charges & Other Finance Costs", self._cy("CO_EX024"), self._py("CO_EX024")),
            _tl("Total", self._sum_cy(fin_codes), self._sum_py(fin_codes)),
        ]
        notes.append(n27)

        # Note 28: Depreciation & Amortisation
        n28 = Note(28, "Depreciation and Amortisation Expense")
        dep_cy = self._cy("CO_EX025") + self._cy("CO_EX026")
        dep_py = self._py("CO_EX025") + self._py("CO_EX026")
        n28.lines = [
            _dl("Depreciation on Tangible Assets", self._cy("CO_EX025"), self._py("CO_EX025")),
            _dl("Amortisation of Intangible Assets", self._cy("CO_EX026"), self._py("CO_EX026")),
            _tl("Total", dep_cy, dep_py),
        ]
        notes.append(n28)

        # Note 29: Other Expenses
        n29 = Note(29, "Other Expenses")
        oe_codes = [f"PL{i:03d}" for i in range(27, 40)]
        labels = [
            "Power & Fuel", "Rent", "Repairs & Maintenance", "Insurance",
            "Printing & Stationery", "Travelling & Conveyance", "Communication",
            "Professional & Legal Fees", "Audit Fees", "Advertisement",
            "GST / Taxes & Duties", "Bad Debts Written Off", "Miscellaneous Expenses",
        ]
        n29.lines = [_dl(lbl, self._cy(c), self._py(c)) for lbl, c in zip(labels, oe_codes)]
        n29.lines.append(_tl("Total", self._sum_cy(oe_codes), self._sum_py(oe_codes)))
        notes.append(n29)

        # Note 30: Related Party Disclosures (placeholder)
        n30 = Note(30, "Related Party Disclosures")
        n30.lines = [
            _line("As required by AS 18, the Company's related party transactions are disclosed below.",
                  0, 0, row_type="TEXT", indent=1),
            _blank(),
            _line("Key Managerial Personnel (KMP):", 0, 0, row_type="SECTION"),
            _line("[List names, designations and relationships of KMP]", 0, 0, row_type="TEXT", indent=1),
            _blank(),
            _line("Transactions with Related Parties:", 0, 0, row_type="SECTION"),
            _line("[List nature and amount of each material transaction with related parties during the year]",
                  0, 0, row_type="TEXT", indent=1),
            _blank(),
            _line("Outstanding Balances:", 0, 0, row_type="SECTION"),
            _line("[List balances due to/from related parties as at year end]",
                  0, 0, row_type="TEXT", indent=1),
        ]
        notes.append(n30)

        # Note 31: Contingent Liabilities & Commitments (placeholder)
        n31 = Note(31, "Contingent Liabilities and Commitments")
        n31.lines = [
            _line("Contingent Liabilities (not provided for):", 0, 0, row_type="SECTION"),
            _line("(i) Claims against the Company not acknowledged as debts: ₹ NIL / [amount]",
                  0, 0, row_type="TEXT", indent=1),
            _line("(ii) Guarantees: ₹ NIL / [amount]", 0, 0, row_type="TEXT", indent=1),
            _line("(iii) Other money for which the Company is contingently liable: ₹ NIL / [amount]",
                  0, 0, row_type="TEXT", indent=1),
            _blank(),
            _line("Capital Commitments:", 0, 0, row_type="SECTION"),
            _line("Estimated amount of contracts remaining to be executed on capital account "
                  "(net of advances): ₹ NIL / [amount]", 0, 0, row_type="TEXT", indent=1),
        ]
        notes.append(n31)

        # Note 32: Events after the Balance Sheet Date (placeholder)
        n32 = Note(32, "Events After the Reporting Period")
        n32.lines = [
            _line("No material events have occurred after the Balance Sheet date that require "
                  "disclosure or adjustment in these financial statements. / [Describe any material "
                  "subsequent events and their financial impact]",
                  0, 0, row_type="TEXT", indent=1),
        ]
        notes.append(n32)

        # Note 33: Earnings Per Share (auto-calculated from P&L totals)
        n33 = Note(33, "Earnings Per Share")
        pat_cy    = self._calc_pat()
        paid_up   = float(self._em.get("paid_up_capital") or 0)
        face_val  = float(self._em.get("face_value_per_share") or 10)
        shares    = int(paid_up / face_val) if face_val > 0 else 0
        beps      = round(pat_cy / shares, 2) if shares > 0 else 0.0
        n33.lines = [
            _line("Calculation of EPS (Basic and Diluted):", 0, 0, row_type="SECTION"),
            _dl("Net Profit/(Loss) after Tax (₹)", pat_cy, 0),
            _dl("Weighted Average Equity Shares (Nos.)", float(shares), 0),
            _dl("Face Value per Share (₹)", face_val, 0),
            _dl("Basic / Diluted EPS (₹)", beps, 0),
        ]
        notes.append(n33)

        return notes

    def _calc_pat(self) -> float:
        """Derive PAT from P&L totals (mirrors FSEngine._company_pl logic)."""
        rev  = self._sum_cy(["CO_IN001","CO_IN002","CO_IN003"]) - self._cy("CO_EX004")
        oi   = self._sum_cy(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        cmc  = self._cy("CO_EX010") + self._cy("CO_EX011")
        pur  = self._cy("CO_EX012")
        inv  = self._sum_cy(["CO_EX013","CO_EX014"]) - self._sum_cy(["CO_IN015","CO_IN016"])
        emp  = self._sum_cy(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        fin  = self._sum_cy(["CO_EX022","CO_EX023","CO_EX024"])
        dep  = self._cy("CO_EX025") + self._cy("CO_EX026")
        oe   = self._sum_cy([f"PL{i:03d}" for i in range(27, 40)])
        pbt  = rev + oi - cmc - pur - inv - emp - fin - dep - oe
        tax  = self._cy("CO_EX040") + self._cy("CO_EX041")
        return round(pbt - tax, 2)

    def _ppe_note_lines(self) -> list[FSLine]:
        lines = []
        tot_gross_op = tot_add = tot_dis = tot_gross_cl = 0.0
        tot_dep_op = tot_dep_ch = tot_dep_dis = tot_dep_cl = tot_nbv_cy = tot_nbv_py = 0.0
        for raw_asset in self._ppe:
            asset = dict(raw_asset) if not isinstance(raw_asset, dict) else raw_asset
            gross_op = float(asset.get("gross_op", 0))
            additions= float(asset.get("additions", 0))
            disposals= float(asset.get("disposals", 0))
            gross_cl = gross_op + additions - disposals
            dep_op   = float(asset.get("dep_op", 0))
            dep_ch   = float(asset.get("dep_charge", 0))
            dep_dis  = float(asset.get("dep_disposal", 0))
            dep_cl   = dep_op + dep_ch - dep_dis
            nbv_cy   = gross_cl - dep_cl
            nbv_py   = float(asset.get("nbv_py", 0))
            lines.append(_dl(
                asset.get("asset_name", ""), nbv_cy, nbv_py
            ))
            tot_gross_op += gross_op; tot_add += additions; tot_dis += disposals
            tot_gross_cl += gross_cl
            tot_dep_op += dep_op; tot_dep_ch += dep_ch; tot_dep_dis += dep_dis
            tot_dep_cl += dep_cl; tot_nbv_cy += nbv_cy; tot_nbv_py += nbv_py
        lines.append(_tl("TOTAL NET BLOCK", tot_nbv_cy, tot_nbv_py))
        return lines

    def _nce_notes(self) -> list[Note]:
        notes = []
        n1 = Note(1, "Capital Account")
        n1.lines = [
            _dl("Opening Capital Balance", 0, 0),
            _dl("Add: Net Profit for the year (as per P&L)", 0, 0),
            _dl("Less: Drawings during the year", 0, 0),
            _tl("Closing Capital Balance", 0, 0),
        ]
        notes.append(n1)
        n2 = Note(2, "Significant Accounting Policies")
        n2.lines = [_line("These accounts have been prepared on accrual basis in accordance with "
                          "the ICAI Format for Non-Corporate Entities.", 0, 0, row_type="TEXT", indent=1)]
        notes.append(n2)
        return notes

    def _aop_notes(self) -> list[Note]:
        notes = []
        n1 = Note(1, "Members' Capital / Corpus Fund")
        n1.lines = [
            _dl("Opening Balance", self._py("AO_EL001"), 0),
            _dl("Add: Surplus for the year", 0, 0),
            _tl("Closing Balance", self._cy("AO_EL001"), self._py("AO_EL001")),
        ]
        notes.append(n1)
        return notes

    def _trust_notes(self) -> list[Note]:
        notes = []
        n1 = Note(1, "Corpus Fund")
        corp_cy = self._cy("TR_EL001") + self._cy("TR_EL002")
        corp_py = self._py("TR_EL001") + self._py("TR_EL002")
        n1.lines = [
            _dl("Opening Corpus Balance", corp_py, 0),
            _dl("Add: Corpus donations received during the year", 0, 0),
            _dl("Add: Surplus transferred from I&E", 0, 0),
            _tl("Closing Corpus Balance", corp_cy, corp_py),
        ]
        notes.append(n1)
        return notes
