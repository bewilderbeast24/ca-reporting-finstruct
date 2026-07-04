"""Financial Statement generation engine — all 8 entity types.

Ported from Engine_FS.gs, NCE_PROP, NCE_PART, NCE_AOP, NCE_NPO.
Produces structured FS line data; GUI and export layers render it.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Literal

from core.master_db import get_lookup_map, MappingEntry


RowType = Literal["HEADER", "SECTION", "DATA", "SUBTOTAL", "TOTAL", "GRAND", "TEXT", "BLANK"]


@dataclass
class FSLine:
    label: str
    cy: float
    py: float
    note: int | None
    indent: int
    row_type: RowType
    code: str = ""


@dataclass
class FSDocument:
    entity_type: str
    fy: str
    entity_master: dict
    divisor: int
    bs: list[FSLine]    = field(default_factory=list)
    pl: list[FSLine]    = field(default_factory=list)
    ie: list[FSLine]    = field(default_factory=list)
    rp: list[FSLine]    = field(default_factory=list)
    cf: list[FSLine]    = field(default_factory=list)
    notes: dict[int, list[FSLine]] = field(default_factory=dict)
    is_balanced: bool   = True
    balance_diff_cy: float = 0.0


def _r(v: float, div: int) -> float:
    return round(v / div, 2) if div else v


def _line(label, cy, py, note=None, indent=0, row_type: RowType = "DATA", code="") -> FSLine:
    return FSLine(label, cy, py, note, indent, row_type, code)


def _sec(label) -> FSLine:
    return FSLine(label, 0, 0, None, 0, "SECTION")


def _hdr(label) -> FSLine:
    return FSLine(label, 0, 0, None, 0, "HEADER")


def _tot(label, cy, py, note=None) -> FSLine:
    return FSLine(label, cy, py, note, 0, "TOTAL")


def _grand(label, cy, py) -> FSLine:
    return FSLine(label, cy, py, None, 0, "GRAND")


def _blank() -> FSLine:
    return FSLine("", 0, 0, None, 0, "BLANK")


class FSEngine:
    def __init__(self, entity_type: str, totals: dict[str, tuple[float, float]],
                 entity_master: dict, fy: str, divisor: int = 1):
        self._etype   = entity_type
        self._totals  = totals         # {code: (cy_net, py_net)}
        self._master  = entity_master
        self._fy      = fy
        self._div     = divisor
        self._lookup  = get_lookup_map()
        
        # Pre-filter master entries for current entity type for faster metadata lookups
        from core.master_db import get_master
        self._master_entries = get_master([self._etype])

    def _cy(self, code: str) -> float:
        v = self._totals.get(code, (0.0, 0.0))[0]
        val = _r(v, self._div)
        entry = self._lookup.get(code)
        if entry and entry.sign == "DR_POSITIVE":
            return -val
        return val

    def _py(self, code: str) -> float:
        v = self._totals.get(code, (0.0, 0.0))[1]
        val = _r(v, self._div)
        entry = self._lookup.get(code)
        if entry and entry.sign == "DR_POSITIVE":
            return -val
        return val

    def _sum_cy(self, codes: list[str]) -> float:
        return round(sum(self._cy(c) for c in codes), 2)

    def _sum_py(self, codes: list[str]) -> float:
        return round(sum(self._py(c) for c in codes), 2)

    def _get_meta_sum(self, group: str | None = None, heading: str | None = None, 
                      fs_tag: str | None = None) -> tuple[float, float]:
        """Aggregate totals by group or heading metadata."""
        cy, py = 0.0, 0.0
        for entry in self._master_entries:
            if fs_tag and entry.fs_tag != fs_tag:
                continue
            if group and entry.group != group:
                continue
            if heading and entry.heading != heading:
                continue
            cy += self._cy(entry.code)
            py += self._py(entry.code)
        return round(cy, 2), round(py, 2)

    def _render_generic(self, fs_tag: str, header_label: str) -> list[FSLine]:
        """
        Build a report dynamically by traversing the MASTER hierarchy
        filtered by entity type and fs_tag (BS, PL, IE, etc).
        """
        # 1. Filter entries for this report
        report_entries = [e for e in self._master_entries if e.fs_tag == fs_tag]
        if not report_entries:
            return []

        lines: list[FSLine] = [_hdr(header_label), _blank()]
        
        # 2. Group by (Group -> Heading)
        # We preserve order from MASTER list
        groups: dict[str, dict[str, list[MappingEntry]]] = {}
        ordered_groups: list[str] = []
        ordered_headings: dict[str, list[str]] = {}

        for e in report_entries:
            if e.group not in groups:
                groups[e.group] = {}
                ordered_groups.append(e.group)
                ordered_headings[e.group] = []
            if e.heading not in groups[e.group]:
                groups[e.group][e.heading] = []
                ordered_headings[e.group].append(e.heading)
            groups[e.group][e.heading].append(e)

        # 3. Render Tree
        for group_name in ordered_groups:
            lines.append(_sec(group_name))
            group_cy, group_py = 0.0, 0.0
            
            for head_name in ordered_headings[group_name]:
                entries = groups[group_name][head_name]
                
                # Sum entries in this heading
                head_cy = sum(self._cy(e.code) for e in entries)
                head_py = sum(self._py(e.code) for e in entries)
                
                # Use note number from first entry if available
                note = next((e.note_number for e in entries if e.note_number), None)
                
                lines.append(_line(f"    {head_name}", head_cy, head_py, note=note, indent=1))
                
                group_cy += head_cy
                group_py += head_py
            
            lines.append(_tot(f"Sub-total — {group_name}", group_cy, group_py))
            lines.append(_blank())

        # 4. Grand Total
        total_cy = sum(line.cy for line in lines if line.row_type == "TOTAL")
        total_py = sum(line.py for line in lines if line.row_type == "TOTAL")
        
        # In BS, we often have two Grand Totals (Equity/Liab and Assets)
        # For now, we'll just put a single Grand Total at the bottom
        # unless it's a specific report type we want to handle specially.
        lines.append(_grand("TOTAL", total_cy, total_py))
        
        return lines

    def generate(self, include_cf: bool = True) -> FSDocument:
        doc = FSDocument(self._etype, self._fy, self._master, self._div)
        
        # BS is always BS tag
        doc.bs = self._render_generic("BS", "BALANCE SHEET")
        
        # Decide between PL or IE based on entity type
        if self._etype in ("COMPANY", "SEC8", "LLP", "PROP", "PART", "AOP"):
            # AOP might have IE in master, let's check
            ie_entries = [e for e in self._master_entries if e.fs_tag == "IE"]
            if ie_entries:
                doc.ie = self._render_generic("IE", "INCOME AND EXPENDITURE ACCOUNT")
            else:
                doc.pl = self._render_generic("PL", "STATEMENT OF PROFIT AND LOSS")
        elif self._etype == "TRUST":
            doc.ie = self._render_generic("IE", "INCOME AND EXPENDITURE ACCOUNT")

        # Receipts & Payments
        doc.rp = self._render_generic("RP", "RECEIPT AND PAYMENT ACCOUNT")
        
        if include_cf and self._etype in ("COMPANY", "SEC8"):
            doc.cf = self._company_cf() # CF is still special/hardcoded due to logic complexity

        self._check_balance(doc)
        return doc

    def _check_balance(self, doc: FSDocument):
        """Perform a heuristic balance check on the generated document."""
        if not doc.bs:
            return
            
        tot_l = 0.0
        tot_a = 0.0
        for line in doc.bs:
            label_up = line.label.upper()
            if "TOTAL" in label_up or line.row_type == "GRAND":
                # Heuristic: the last GRAND/TOTAL for each side
                if "ASSET" in label_up:
                    tot_a = line.cy
                elif any(kw in label_up for kw in ["LIABILIT", "EQUITY", "FUNDS"]):
                    tot_l = line.cy
        
        diff = round(tot_l - tot_a, 2)
        if abs(diff) > 0.5:
            doc.is_balanced = False
            doc.balance_diff_cy = diff
            doc.bs.append(_line(f"⚠ BS imbalance: {diff:,.2f}", 0, 0, row_type="TEXT"))

    # ─── COMPANY BALANCE SHEET (Schedule III Part I) ──────────────────────────

    def _nce_pl(self, prefixes: list[str]) -> list[FSLine]:
        lines = [_hdr("PROFIT AND LOSS ACCOUNT"), _blank()]
        rev_cy = self._cy("NC_IN001"); rev_py = self._py("NC_IN001")
        lines.append(_line("I.   Gross Revenue from Operations", rev_cy, rev_py, note=15, indent=1))
        oi_cy  = self._cy("NC_IN002"); oi_py  = self._py("NC_IN002")
        lines.append(_line("II.  Other Income", oi_cy, oi_py, note=16, indent=1))
        tot_i_cy = rev_cy + oi_cy; tot_i_py = rev_py + oi_py
        lines.append(_tot("III. Total Income", tot_i_cy, tot_i_py))
        lines.append(_blank())

        lines.append(_sec("IV.  Expenses:"))
        cog_cy = self._cy("NC_EX003") + self._cy("NC_EX004") - self._cy("NC_IN005")
        cog_py = self._py("NC_EX003") + self._py("NC_EX004") - self._py("NC_IN005")
        lines.append(_line("     Cost of Goods / Material", cog_cy, cog_py, note=17, indent=2))
        emp_cy = self._cy("NC_EX006"); emp_py = self._py("NC_EX006")
        lines.append(_line("     Employee Expenses", emp_cy, emp_py, note=18, indent=2))
        fin_cy = self._cy("NC_EX007"); fin_py = self._py("NC_EX007")
        lines.append(_line("     Finance Costs", fin_cy, fin_py, note=19, indent=2))
        dep_cy = self._cy("NC_EX008"); dep_py = self._py("NC_EX008")
        lines.append(_line("     Depreciation", dep_cy, dep_py, note=20, indent=2))
        oe_cy  = self._cy("NC_EX009"); oe_py  = self._py("NC_EX009")
        lines.append(_line("     Administrative & Other Expenses", oe_cy, oe_py, note=21, indent=2))
        tot_e_cy = cog_cy + emp_cy + fin_cy + dep_cy + oe_cy
        tot_e_py = cog_py + emp_py + fin_py + dep_py + oe_py
        lines.append(_tot("     Total Expenses", tot_e_cy, tot_e_py))
        lines.append(_blank())
        net_cy = tot_i_cy - tot_e_cy; net_py = tot_i_py - tot_e_py
        label = "V.   Net Profit / (Loss) for the year" if net_cy >= 0 else "V.   Net Loss for the year"
        lines.append(_grand(label, net_cy, net_py))
        return lines

    # ─── LLP BS ───────────────────────────────────────────────────────────

    def _trust_ie(self) -> list[FSLine]:
        lines = [_hdr("INCOME AND EXPENDITURE ACCOUNT"), _blank()]
        lines.append(_sec("INCOME"))
        don_cy = self._cy("TR_IN001") + self._cy("TR_IN002"); don_py = self._py("TR_IN001") + self._py("TR_IN002")
        lines.append(_line("I.   Donations & Grants", don_cy, don_py, note=9, indent=1))
        act_cy = self._cy("TR_IN003"); act_py = self._py("TR_IN003")
        lines.append(_line("II.  Income from Activities", act_cy, act_py, note=10, indent=1))
        oi_cy  = self._cy("TR_IN004"); oi_py  = self._py("TR_IN004")
        lines.append(_line("III. Interest & Investment Income", oi_cy, oi_py, note=11, indent=1))
        tot_i_cy = don_cy + act_cy + oi_cy; tot_i_py = don_py + act_py + oi_py
        lines.append(_grand("TOTAL INCOME (I)", tot_i_cy, tot_i_py))
        lines.append(_blank())
        lines.append(_sec("EXPENDITURE"))
        prog_cy = self._cy("TR_EX001"); prog_py = self._py("TR_EX001")
        lines.append(_line("IV.  Programme & Project Expenses", prog_cy, prog_py, note=12, indent=1))
        adm_cy = self._cy("TR_EX002") + self._cy("TR_EX003"); adm_py = self._py("TR_EX002") + self._py("TR_EX003")
        lines.append(_line("V.   Administrative Expenses", adm_cy, adm_py, note=13, indent=1))
        dep_cy = self._cy("TR_EX004"); dep_py = self._py("TR_EX004")
        lines.append(_line("VI.  Depreciation", dep_cy, dep_py, note=14, indent=1))
        tot_e_cy = prog_cy + adm_cy + dep_cy; tot_e_py = prog_py + adm_py + dep_py
        lines.append(_grand("TOTAL EXPENDITURE (II)", tot_e_cy, tot_e_py))
        sur_cy = tot_i_cy - tot_e_cy; sur_py = tot_i_py - tot_e_py
        label = "SURPLUS FOR THE YEAR" if sur_cy >= 0 else "DEFICIT FOR THE YEAR"
        lines.append(_grand(label, abs(sur_cy), abs(sur_py)))
        return lines

    def _company_cf(self) -> list[FSLine]:
        lines = [_hdr("CASH FLOW STATEMENT"), _blank()]
        lines.append(_line("(Prepared using the Indirect Method as per AS 3)", 0, 0,
                           row_type="TEXT"))
        lines.append(_blank())

        # ── Recalculate PBT from P&L codes ──────────────────────────────────
        rev_cy = self._sum_cy(["CO_IN001","CO_IN002","CO_IN003"]) - self._cy("CO_EX004")
        rev_py = self._sum_py(["CO_IN001","CO_IN002","CO_IN003"]) - self._py("CO_EX004")
        oi_cy  = self._sum_cy(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        oi_py  = self._sum_py(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        tot_rev_cy = rev_cy + oi_cy
        tot_rev_py = rev_py + oi_py

        cmc_cy = self._cy("CO_EX010") + self._cy("CO_EX011")
        cmc_py = self._py("CO_EX010") + self._py("CO_EX011")
        pur_cy = self._cy("CO_EX012"); pur_py = self._py("CO_EX012")
        inv_ch_cy = self._sum_cy(["CO_EX013","CO_EX014"]) - self._sum_cy(["CO_IN015","CO_IN016"])
        inv_ch_py = self._sum_py(["CO_EX013","CO_EX014"]) - self._sum_py(["CO_IN015","CO_IN016"])
        emp_cy = self._sum_cy(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        emp_py = self._sum_py(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        fin_cy = self._sum_cy(["CO_EX022","CO_EX023","CO_EX024"])
        fin_py = self._sum_py(["CO_EX022","CO_EX023","CO_EX024"])
        dep_cy = self._cy("CO_EX025") + self._cy("CO_EX026")
        dep_py = self._py("CO_EX025") + self._py("CO_EX026")
        oe_cy  = self._sum_cy([f"PL{i:03d}" for i in range(27, 40)])
        oe_py  = self._sum_py([f"PL{i:03d}" for i in range(27, 40)])
        tot_exp_cy = cmc_cy + pur_cy + inv_ch_cy + emp_cy + fin_cy + dep_cy + oe_cy
        tot_exp_py = cmc_py + pur_py + inv_ch_py + emp_py + fin_py + dep_py + oe_py

        pbt_cy = tot_rev_cy - tot_exp_cy
        pbt_py = tot_rev_py - tot_exp_py

        # CO_IN005 = Interest Income; reclassify from operating to investing
        int_inc_cy = self._cy("CO_IN005"); int_inc_py = self._py("CO_IN005")

        # ── A. OPERATING ACTIVITIES ──────────────────────────────────────────
        lines.append(_sec("A.  CASH FLOW FROM OPERATING ACTIVITIES"))
        lines.append(_line("Net Profit / (Loss) before Tax", pbt_cy, pbt_py, indent=1))
        lines.append(_blank())
        lines.append(_line("Adjustments for:", 0, 0, row_type="SECTION", indent=1))
        lines.append(_line("  Add: Depreciation & Amortisation", dep_cy, dep_py, indent=2))
        lines.append(_line("  Add: Finance Costs", fin_cy, fin_py, indent=2))
        lines.append(_line("  Less: Interest Income (moved to Investing)", -int_inc_cy, -int_inc_py, indent=2))

        adj_cy = dep_cy + fin_cy - int_inc_cy
        adj_py = dep_py + fin_py - int_inc_py
        lines.append(_tot("  Total Adjustments", adj_cy, adj_py))
        lines.append(_blank())

        # Working capital changes — asset increases = cash outflow (negative)
        tr_cy  = self._cy("CO_AS020") + self._cy("CO_AS021") - self._cy("CO_AS022")
        tr_py  = self._py("CO_AS020") + self._py("CO_AS021") - self._py("CO_AS022")
        inv_ca_cy = self._sum_cy(["CO_AS015","CO_AS016","CO_AS017","CO_AS018","CO_AS019"])
        inv_ca_py = self._sum_py(["CO_AS015","CO_AS016","CO_AS017","CO_AS018","CO_AS019"])
        stla_cy = self._sum_cy(["CO_AS027","CO_AS028","CO_AS029","CO_AS030"])
        stla_py = self._sum_py(["CO_AS027","CO_AS028","CO_AS029","CO_AS030"])
        oca_cy  = self._cy("CO_AS031") + self._cy("CO_AS032") + self._cy("CO_AS033")
        oca_py  = self._py("CO_AS031") + self._py("CO_AS032") + self._py("CO_AS033")

        tp_cy   = self._cy("CO_EL025") + self._cy("CO_EL026")
        tp_py   = self._py("CO_EL025") + self._py("CO_EL026")
        ocl_cy  = self._sum_cy(["CO_EL027","CO_EL028","CO_EL029","CO_EL030","CO_EL031"])
        ocl_py  = self._sum_py(["CO_EL027","CO_EL028","CO_EL029","CO_EL030","CO_EL031"])
        stp_cy  = self._sum_cy(["CO_EL032","CO_EL033","CO_EL034"])
        stp_py  = self._sum_py(["CO_EL032","CO_EL033","CO_EL034"])

        d_tr_cy  = -(tr_cy - tr_py);    d_tr_py  = -(tr_py - 0)
        d_inv_cy = -(inv_ca_cy - inv_ca_py); d_inv_py = -(inv_ca_py - 0)
        d_stla_cy= -(stla_cy - stla_py); d_stla_py= -(stla_py - 0)
        d_oca_cy = -(oca_cy - oca_py);  d_oca_py = -(oca_py - 0)
        d_tp_cy  = tp_cy - tp_py;       d_tp_py  = tp_py - 0
        d_ocl_cy = ocl_cy - ocl_py;     d_ocl_py = ocl_py - 0
        d_stp_cy = stp_cy - stp_py;     d_stp_py = stp_py - 0

        wc_cy = d_tr_cy + d_inv_cy + d_stla_cy + d_oca_cy + d_tp_cy + d_ocl_cy + d_stp_cy
        wc_py = d_tr_py + d_inv_py + d_stla_py + d_oca_py + d_tp_py + d_ocl_py + d_stp_py

        lines.append(_line("Changes in Working Capital:", 0, 0, row_type="SECTION", indent=1))
        lines.append(_line("  (Increase)/Decrease in Trade Receivables",    d_tr_cy,  d_tr_py,  indent=2))
        lines.append(_line("  (Increase)/Decrease in Inventories",          d_inv_cy, d_inv_py, indent=2))
        lines.append(_line("  (Increase)/Decrease in Loans & Advances",     d_stla_cy,d_stla_py,indent=2))
        lines.append(_line("  (Increase)/Decrease in Other Current Assets", d_oca_cy, d_oca_py, indent=2))
        lines.append(_line("  Increase/(Decrease) in Trade Payables",       d_tp_cy,  d_tp_py,  indent=2))
        lines.append(_line("  Increase/(Decrease) in Other Current Liab.",  d_ocl_cy, d_ocl_py, indent=2))
        lines.append(_line("  Increase/(Decrease) in Short-term Provisions",d_stp_cy, d_stp_py, indent=2))
        lines.append(_tot("  Net Working Capital Changes", wc_cy, wc_py))
        lines.append(_blank())

        tax_cy = self._cy("CO_EX040"); tax_py = self._py("CO_EX040")
        lines.append(_line("Less: Direct Taxes Paid (Net of Refunds)", -tax_cy, -tax_py, indent=1))
        cf_op_cy = round(pbt_cy + adj_cy + wc_cy - tax_cy, 2)
        cf_op_py = round(pbt_py + adj_py + wc_py - tax_py, 2)
        lines.append(_grand("Net Cash from/(used in) Operating Activities (A)", cf_op_cy, cf_op_py))
        lines.append(_blank())

        # ── B. INVESTING ACTIVITIES ──────────────────────────────────────────
        lines.append(_sec("B.  CASH FLOW FROM INVESTING ACTIVITIES"))

        # Capex: increase in gross fixed assets = outflow
        ppe_gross_cy = self._cy("CO_AS001") + self._cy("CO_AS004")
        ppe_gross_py = self._py("CO_AS001") + self._py("CO_AS004")
        capex_cy = -(ppe_gross_cy - ppe_gross_py)
        capex_py = -(ppe_gross_py - 0)

        nci_cy = self._sum_cy(["CO_AS006","CO_AS007","CO_AS008"])
        nci_py = self._sum_py(["CO_AS006","CO_AS007","CO_AS008"])
        d_invest_cy = -(nci_cy - nci_py)
        d_invest_py = -(nci_py - 0)

        lines.append(_line("Purchase of Fixed Assets (including CWIP)", capex_cy, capex_py, indent=1))
        lines.append(_line("Purchase/(Sale) of Investments (Net)",       d_invest_cy, d_invest_py, indent=1))
        lines.append(_line("Interest Received",                          int_inc_cy, int_inc_py, indent=1))

        cf_inv_cy = round(capex_cy + d_invest_cy + int_inc_cy, 2)
        cf_inv_py = round(capex_py + d_invest_py + int_inc_py, 2)
        lines.append(_grand("Net Cash from/(used in) Investing Activities (B)", cf_inv_cy, cf_inv_py))
        lines.append(_blank())

        # ── C. FINANCING ACTIVITIES ──────────────────────────────────────────
        lines.append(_sec("C.  CASH FLOW FROM FINANCING ACTIVITIES"))

        ltb_cy = self._sum_cy(["CO_EL010","CO_EL011","CO_EL012","CO_EL013","CO_EL014","CO_EL015"])
        ltb_py = self._sum_py(["CO_EL010","CO_EL011","CO_EL012","CO_EL013","CO_EL014","CO_EL015"])
        stb_cy = self._sum_cy(["CO_EL020","CO_EL021","CO_EL022","CO_EL023","CO_EL024"])
        stb_py = self._sum_py(["CO_EL020","CO_EL021","CO_EL022","CO_EL023","CO_EL024"])
        d_ltb_cy = ltb_cy - ltb_py
        d_stb_cy = stb_cy - stb_py
        div_cy  = self._cy("CO_EL008"); div_py = self._py("CO_EL008")

        lines.append(_line("Proceeds from/(Repayment of) Long-term Borrowings (Net)",   d_ltb_cy, 0, indent=1))
        lines.append(_line("Proceeds from/(Repayment of) Short-term Borrowings (Net)",  d_stb_cy, 0, indent=1))
        lines.append(_line("Finance Costs Paid",                                         -fin_cy,  -fin_py, indent=1))
        lines.append(_line("Dividends Paid",                                             -div_cy,  -div_py, indent=1))

        cf_fin_cy = round(d_ltb_cy + d_stb_cy - fin_cy - div_cy, 2)
        cf_fin_py = round(-fin_py - div_py, 2)
        lines.append(_grand("Net Cash from/(used in) Financing Activities (C)", cf_fin_cy, cf_fin_py))
        lines.append(_blank())

        # ── RECONCILIATION ───────────────────────────────────────────────────
        net_cf_cy = round(cf_op_cy + cf_inv_cy + cf_fin_cy, 2)
        net_cf_py = round(cf_op_py + cf_inv_py + cf_fin_py, 2)
        lines.append(_grand("Net Increase/(Decrease) in Cash (A+B+C)", net_cf_cy, net_cf_py))

        cash_cl_cy  = self._sum_cy(["CO_AS023","CO_AS024","CO_AS025","CO_AS026"])
        cash_op_val = self._sum_py(["CO_AS023","CO_AS024","CO_AS025","CO_AS026"])
        lines.append(_line("Add: Opening Cash & Cash Equivalents", cash_op_val, 0, indent=1))
        lines.append(_grand("Closing Cash & Cash Equivalents", cash_cl_cy, 0))

        diff = round(net_cf_cy - (cash_cl_cy - cash_op_val), 2)
        if abs(diff) > 0.5:
            lines.append(_line(
                f"⚠ CF reconciliation gap: {diff:,.2f} — check disposal proceeds & other adjustments",
                0, 0, row_type="TEXT"
            ))
        return lines
