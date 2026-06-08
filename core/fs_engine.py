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
        return _r(v, self._div)

    def _py(self, code: str) -> float:
        v = self._totals.get(code, (0.0, 0.0))[1]
        return _r(v, self._div)

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

    def _evaluate_formula(self, formula: str) -> tuple[float, float]:
        """
        Evaluate basic formulas like 'GROUP:Name', 'HEADING:Name' or simple additions.
        This is a simplified evaluator for declarative schemas.
        """
        if not formula:
            return 0.0, 0.0
        
        # Split by + and - but keep the operators
        # Pattern: GROUP:xxx | HEADING:xxx | code
        parts = re.split(r'(\s*[\+\-]\s*)', formula)
        
        total_cy, total_py = 0.0, 0.0
        current_op = '+'
        
        for part in parts:
            part = part.strip()
            if not part: continue
            if part in ('+', '-'):
                current_op = part
                continue
            
            cy, py = 0.0, 0.0
            if part.startswith("GROUP:"):
                cy, py = self._get_meta_sum(group=part[6:])
            elif part.startswith("HEADING:"):
                cy, py = self._get_meta_sum(heading=part[8:])
            elif part in self._lookup:
                cy, py = self._cy(part), self._py(part)
            
            if current_op == '+':
                total_cy += cy
                total_py += py
            else:
                total_cy -= cy
                total_py -= py
        
        return round(total_cy, 2), round(total_py, 2)

    def _render_schema(self, schema: dict) -> list[FSLine]:
        """Render a report based on a declarative schema dictionary."""
        lines: list[FSLine] = []
        for item in schema.get("layout", []):
            itype = item.get("type")
            label = item.get("label", "")
            indent = item.get("indent", 0)
            note = item.get("note")
            
            if itype == "HEADER":
                lines.append(_hdr(label))
            elif itype == "SECTION":
                lines.append(_sec(label))
            elif itype == "BLANK":
                lines.append(_blank())
            elif itype == "TEXT":
                lines.append(_line(label, 0, 0, row_type="TEXT"))
            else:
                cy, py = 0.0, 0.0
                if "formula" in item:
                    cy, py = self._evaluate_formula(item["formula"])
                elif "heading" in item:
                    cy, py = self._get_meta_sum(heading=item["heading"])
                elif "group" in item:
                    cy, py = self._get_meta_sum(group=item["group"])
                elif "code" in item:
                    cy, py = self._cy(item["code"]), self._py(item["code"])
                elif "codes" in item:
                    cy, py = self._sum_cy(item["codes"]), self._sum_py(item["codes"])
                
                if itype == "TOTAL":
                    lines.append(_tot(label, cy, py, note=note))
                elif itype == "GRAND":
                    lines.append(_grand(label, cy, py))
                else:
                    lines.append(_line(label, cy, py, note=note, indent=indent, row_type=itype))
        return lines

    def generate(self, include_cf: bool = True) -> FSDocument:
        from core.fs_layouts import (
            COMPANY_BS_SCHEMA, LLP_BS_SCHEMA, COMPANY_PL_SCHEMA,
            AOP_RP_SCHEMA
        )
        doc = FSDocument(self._etype, self._fy, self._master, self._div)
        
        if self._etype in ("COMPANY", "SEC8"):
            doc.bs = self._render_schema(COMPANY_BS_SCHEMA)
            if self._etype == "SEC8":
                doc.ie = self._sec8_ie()
            else:
                doc.pl = self._render_schema(COMPANY_PL_SCHEMA)
            if include_cf:
                doc.cf = self._company_cf()
        elif self._etype == "LLP":
            doc.bs = self._render_schema(LLP_BS_SCHEMA)
            doc.pl = self._llp_pl()
        elif self._etype == "PROP":
            doc.bs = self._nce_bs()
            doc.pl = self._nce_pl(["NC", "NP"])
        elif self._etype == "PART":
            doc.bs = self._nce_bs()
            doc.pl = self._nce_pl(["NC", "NP"])
        elif self._etype == "AOP":
            doc.bs = self._aop_bs()
            doc.ie = self._aop_ie()
            doc.rp = self._render_schema(AOP_RP_SCHEMA)
        elif self._etype == "TRUST":
            doc.bs = self._trust_bs()
            doc.ie = self._trust_ie()
            doc.rp = self._render_schema(AOP_RP_SCHEMA)

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

    def _company_pl(self) -> list[FSLine]:
        lines: list[FSLine] = [_hdr("STATEMENT OF PROFIT AND LOSS"), _blank()]

        rev_cy = self._sum_cy(["CO_IN001","CO_IN002","CO_IN003"]) - self._cy("CO_EX004")
        rev_py = self._sum_py(["CO_IN001","CO_IN002","CO_IN003"]) - self._py("CO_EX004")
        lines.append(_line("I.   Revenue from Operations", rev_cy, rev_py, note=21, indent=1))
        oi_cy = self._sum_cy(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        oi_py = self._sum_py(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        lines.append(_line("II.  Other Income", oi_cy, oi_py, note=22, indent=1))
        tot_rev_cy = rev_cy + oi_cy
        tot_rev_py = rev_py + oi_py
        lines.append(_tot("III. Total Revenue (I + II)", tot_rev_cy, tot_rev_py))
        lines.append(_blank())

        lines.append(_line("IV.  Expenses:", 0, 0, row_type="SECTION"))
        cmc_cy = self._cy("CO_EX010") + self._cy("CO_EX011")
        cmc_py = self._py("CO_EX010") + self._py("CO_EX011")
        lines.append(_line("     Cost of Materials Consumed", cmc_cy, cmc_py, note=23, indent=2))
        pur_cy = self._cy("CO_EX012"); pur_py = self._py("CO_EX012")
        lines.append(_line("     Purchases of Stock-in-Trade", pur_cy, pur_py, note=24, indent=2))
        inv_ch_cy = self._sum_cy(["CO_EX013","CO_EX014"]) - self._sum_cy(["CO_IN015","CO_IN016"])
        inv_ch_py = self._sum_py(["CO_EX013","CO_EX014"]) - self._sum_py(["CO_IN015","CO_IN016"])
        lines.append(_line("     Changes in Inventories", inv_ch_cy, inv_ch_py, note=25, indent=2))
        emp_cy = self._sum_cy(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        emp_py = self._sum_py(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        lines.append(_line("     Employee Benefit Expenses", emp_cy, emp_py, note=26, indent=2))
        fin_cy = self._sum_cy(["CO_EX022","CO_EX023","CO_EX024"])
        fin_py = self._sum_py(["CO_EX022","CO_EX023","CO_EX024"])
        lines.append(_line("     Finance Costs", fin_cy, fin_py, note=27, indent=2))
        dep_cy = self._cy("CO_EX025") + self._cy("CO_EX026")
        dep_py = self._py("CO_EX025") + self._py("CO_EX026")
        lines.append(_line("     Depreciation & Amortisation", dep_cy, dep_py, note=28, indent=2))
        oe_cy = self._sum_cy([f"PL{i:03d}" for i in range(27,40)])
        oe_py = self._sum_py([f"PL{i:03d}" for i in range(27,40)])
        lines.append(_line("     Other Expenses", oe_cy, oe_py, note=29, indent=2))
        tot_exp_cy = cmc_cy + pur_cy + inv_ch_cy + emp_cy + fin_cy + dep_cy + oe_cy
        tot_exp_py = cmc_py + pur_py + inv_ch_py + emp_py + fin_py + dep_py + oe_py
        lines.append(_tot("     Total Expenses (IV)", tot_exp_cy, tot_exp_py))
        lines.append(_blank())

        pbt_cy = tot_rev_cy - tot_exp_cy
        pbt_py = tot_rev_py - tot_exp_py
        lines.append(_grand("V.   Profit/(Loss) before Tax (III – IV)", pbt_cy, pbt_py))
        tax_cy = self._cy("CO_EX040") + self._cy("CO_EX041")
        tax_py = self._py("CO_EX040") + self._py("CO_EX041")
        lines.append(_line("VI.  Tax Expense", tax_cy, tax_py, indent=1))
        pat_cy = pbt_cy - tax_cy
        pat_py = pbt_py - tax_py
        lines.append(_grand("VII. Profit/(Loss) after Tax (V – VI)", pat_cy, pat_py))
        return lines

    # ─── NCE BALANCE SHEET (Prop / Part / LLP) ────────────────────────────

    def _nce_bs(self) -> list[FSLine]:
        lines = [_hdr("BALANCE SHEET"), _blank()]

        lines.append(_sec("FUNDS & LIABILITIES"))
        cap_cy = self._sum_cy(["NC_EL001","NC_EL002"]) - self._cy("NC_AS003")
        cap_py = self._sum_py(["NC_EL001","NC_EL002"]) - self._py("NC_AS003")
        lines.append(_line("I.   Capital Account", cap_cy, cap_py, note=1, indent=1))
        res_cy = self._cy("NC_EL004"); res_py = self._py("NC_EL004")
        lines.append(_line("II.  Reserves & Surplus", res_cy, res_py, note=2, indent=1))
        sl_cy = self._cy("NC_EL005");  sl_py = self._py("NC_EL005")
        lines.append(_line("III. Secured Loans", sl_cy, sl_py, note=3, indent=1))
        ul_cy = self._cy("NC_EL006");  ul_py = self._py("NC_EL006")
        lines.append(_line("IV.  Unsecured Loans", ul_cy, ul_py, note=4, indent=1))
        tp_cy = self._cy("NC_EL007");  tp_py = self._py("NC_EL007")
        ocl_cy= self._sum_cy(["NC_EL008","NC_EL009","NC_EL010"]); ocl_py = self._sum_py(["NC_EL008","NC_EL009","NC_EL010"])
        prov_cy = self._cy("NC_EL011"); prov_py = self._py("NC_EL011")
        cl_cy  = tp_cy + ocl_cy + prov_cy
        cl_py  = tp_py + ocl_py + prov_py
        lines.append(_line("V.   Current Liabilities & Provisions", cl_cy, cl_py, note=5, indent=1))
        tot_fl_cy = cap_cy + res_cy + sl_cy + ul_cy + cl_cy
        tot_fl_py = cap_py + res_py + sl_py + ul_py + cl_py
        lines.append(_grand("TOTAL — FUNDS & LIABILITIES", tot_fl_cy, tot_fl_py))
        lines.append(_blank())

        lines.append(_sec("ASSETS"))
        fa_gross_cy = self._cy("NC_AS012") + self._cy("NC_AS013")
        fa_gross_py = self._py("NC_AS012") + self._py("NC_AS013")
        lines.append(_line("I.   Fixed Assets (Net Block)", fa_gross_cy, fa_gross_py, note=8, indent=1))
        inv_cy = self._cy("NC_AS014"); inv_py = self._py("NC_AS014")
        lines.append(_line("II.  Investments", inv_cy, inv_py, note=9, indent=1))
        cash_cy = self._cy("NC_AS015") + self._cy("NC_AS016")
        cash_py = self._py("NC_AS015") + self._py("NC_AS016")
        lines.append(_line("III. Cash & Bank Balances", cash_cy, cash_py, note=10, indent=1))
        stock_cy = self._cy("NC_AS017"); stock_py = self._py("NC_AS017")
        lines.append(_line("IV.  Inventories", stock_cy, stock_py, note=11, indent=1))
        tr_cy = self._cy("NC_AS018");  tr_py = self._py("NC_AS018")
        lines.append(_line("V.   Trade Receivables (Debtors)", tr_cy, tr_py, note=12, indent=1))
        la_cy = self._cy("NC_AS019");  la_py = self._py("NC_AS019")
        lines.append(_line("VI.  Loans & Advances", la_cy, la_py, note=13, indent=1))
        oca_cy = self._cy("NC_AS020"); oca_py = self._py("NC_AS020")
        lines.append(_line("VII. Other Current Assets", oca_cy, oca_py, note=14, indent=1))
        tot_as_cy = fa_gross_cy + inv_cy + cash_cy + stock_cy + tr_cy + la_cy + oca_cy
        tot_as_py = fa_gross_py + inv_py + cash_py + stock_py + tr_py + la_py + oca_py
        lines.append(_grand("TOTAL — ASSETS", tot_as_cy, tot_as_py))
        return lines

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

    def _aop_bs(self) -> list[FSLine]:
        lines = [_hdr("BALANCE SHEET"), _blank()]
        lines.append(_sec("FUNDS & LIABILITIES"))
        cf_cy = self._cy("AO_EL001"); cf_py = self._py("AO_EL001")
        lines.append(_line("I.   Capital / Members' Fund", cf_cy, cf_py, note=1, indent=1))
        em_cy = self._cy("AO_EL002") + self._cy("AO_EL003"); em_py = self._py("AO_EL002") + self._py("AO_EL003")
        lines.append(_line("II.  Earmarked / Specific Funds", em_cy, em_py, note=2, indent=1))
        res_cy= self._cy("AO_EL004"); res_py = self._py("AO_EL004")
        lines.append(_line("III. Reserves & Surplus", res_cy, res_py, note=3, indent=1))
        sl_cy = self._cy("AO_EL005"); sl_py = self._py("AO_EL005")
        lines.append(_line("IV.  Secured Loans", sl_cy, sl_py, note=4, indent=1))
        dep_cy= self._cy("AO_EL006"); dep_py = self._py("AO_EL006")
        lines.append(_line("V.   Member Deposits (Refundable)", dep_cy, dep_py, note=5, indent=1))
        ocl_cy= self._cy("AO_EL007") + self._cy("AO_EL008"); ocl_py = self._py("AO_EL007") + self._py("AO_EL008")
        lines.append(_line("VI.  Other Current Liabilities", ocl_cy, ocl_py, note=6, indent=1))
        tot_fl_cy = cf_cy + em_cy + res_cy + sl_cy + dep_cy + ocl_cy
        tot_fl_py = cf_py + em_py + res_py + sl_py + dep_py + ocl_py
        lines.append(_grand("TOTAL (A)", tot_fl_cy, tot_fl_py))
        lines.append(_blank())
        lines.append(_sec("ASSETS"))
        fa_cy = self._cy("AO_AS009"); fa_py = self._py("AO_AS009")
        lines.append(_line("I.   Fixed Assets (Net Block)", fa_cy, fa_py, note=7, indent=1))
        inv_cy= self._cy("AO_AS010"); inv_py = self._py("AO_AS010")
        lines.append(_line("II.  Investments", inv_cy, inv_py, note=8, indent=1))
        cash_cy = self._cy("AO_AS011") + self._cy("AO_AS012"); cash_py = self._py("AO_AS011") + self._py("AO_AS012")
        lines.append(_line("III. Cash & Bank Balances", cash_cy, cash_py, note=9, indent=1))
        tr_cy = self._cy("AO_AS013"); tr_py = self._py("AO_AS013")
        lines.append(_line("IV.  Debtors (Maintenance Dues)", tr_cy, tr_py, note=10, indent=1))
        la_cy = self._cy("AO_AS014"); la_py = self._py("AO_AS014")
        lines.append(_line("V.   Loans & Advances", la_cy, la_py, note=11, indent=1))
        oca_cy= self._cy("AO_AS015"); oca_py = self._py("AO_AS015")
        lines.append(_line("VI.  Other Current Assets", oca_cy, oca_py, note=12, indent=1))
        tot_as_cy = fa_cy + inv_cy + cash_cy + tr_cy + la_cy + oca_cy
        tot_as_py = fa_py + inv_py + cash_py + tr_py + la_py + oca_py
        lines.append(_grand("TOTAL (B)", tot_as_cy, tot_as_py))
        return lines

    def _aop_ie(self) -> list[FSLine]:
        lines = [_hdr("INCOME AND EXPENDITURE ACCOUNT"), _blank()]
        lines.append(_sec("INCOME"))
        mi_cy = self._cy("AO_IN001"); mi_py = self._py("AO_IN001")
        lines.append(_line("I.   Maintenance Income", mi_cy, mi_py, note=13, indent=1))
        oi_cy = self._cy("AO_IN002") + self._cy("AO_IN003"); oi_py = self._py("AO_IN002") + self._py("AO_IN003")
        lines.append(_line("II.  Other Income", oi_cy, oi_py, note=14, indent=1))
        tot_i_cy = mi_cy + oi_cy; tot_i_py = mi_py + oi_py
        lines.append(_grand("TOTAL INCOME (I)", tot_i_cy, tot_i_py))
        lines.append(_blank())
        lines.append(_sec("EXPENDITURE"))
        est_cy = self._cy("AO_EX001"); est_py = self._py("AO_EX001")
        lines.append(_line("III. Establishment Expenses", est_cy, est_py, note=15, indent=1))
        me_cy  = self._cy("AO_EX002"); me_py  = self._py("AO_EX002")
        lines.append(_line("IV.  Maintenance Expenses", me_cy, me_py, note=16, indent=1))
        adm_cy = self._cy("AO_EX003"); adm_py = self._py("AO_EX003")
        lines.append(_line("V.   Administrative Expenses", adm_cy, adm_py, note=17, indent=1))
        dep_cy = self._cy("AO_EX004"); dep_py = self._py("AO_EX004")
        lines.append(_line("VI.  Depreciation", dep_cy, dep_py, note=18, indent=1))
        tot_e_cy = est_cy + me_cy + adm_cy + dep_cy
        tot_e_py = est_py + me_py + adm_py + dep_py
        lines.append(_grand("TOTAL EXPENDITURE (II)", tot_e_cy, tot_e_py))
        lines.append(_blank())
        sur_cy = tot_i_cy - tot_e_cy; sur_py = tot_i_py - tot_e_py
        label = "SURPLUS FOR THE YEAR (I–II)" if sur_cy >= 0 else "DEFICIT FOR THE YEAR (II–I)"
        lines.append(_grand(label, abs(sur_cy), abs(sur_py)))
        return lines

    def _trust_bs(self) -> list[FSLine]:
        lines = [_hdr("BALANCE SHEET"), _blank()]
        lines.append(_sec("CORPUS & LIABILITIES"))
        corp_cy = self._cy("TR_EL001") + self._cy("TR_EL002"); corp_py = self._py("TR_EL001") + self._py("TR_EL002")
        lines.append(_line("I.   Corpus Fund", corp_cy, corp_py, note=1, indent=1))
        em_cy = self._cy("TR_EL003") + self._cy("TR_EL004"); em_py = self._py("TR_EL003") + self._py("TR_EL004")
        lines.append(_line("II.  Earmarked Funds", em_cy, em_py, note=2, indent=1))
        loan_cy= self._cy("TR_EL005"); loan_py = self._py("TR_EL005")
        lines.append(_line("III. Loans & Liabilities", loan_cy, loan_py, note=3, indent=1))
        cl_cy  = self._cy("TR_EL006"); cl_py   = self._py("TR_EL006")
        lines.append(_line("IV.  Current Liabilities", cl_cy, cl_py, note=4, indent=1))
        tot_fl_cy = corp_cy + em_cy + loan_cy + cl_cy
        tot_fl_py = corp_py + em_py + loan_py + cl_py
        lines.append(_grand("TOTAL", tot_fl_cy, tot_fl_py))
        lines.append(_blank())
        lines.append(_sec("ASSETS"))
        fa_cy = self._cy("TR_AS007"); fa_py = self._py("TR_AS007")
        lines.append(_line("I.   Fixed Assets (Net Block)", fa_cy, fa_py, note=5, indent=1))
        inv_cy= self._cy("TR_AS008"); inv_py = self._py("TR_AS008")
        lines.append(_line("II.  Corpus Investments", inv_cy, inv_py, note=6, indent=1))
        cash_cy = self._cy("TR_AS009") + self._cy("TR_AS010"); cash_py = self._py("TR_AS009") + self._py("TR_AS010")
        lines.append(_line("III. Cash & Bank Balances", cash_cy, cash_py, note=7, indent=1))
        oca_cy = self._cy("TR_AS011"); oca_py = self._py("TR_AS011")
        lines.append(_line("IV.  Other Current Assets", oca_cy, oca_py, note=8, indent=1))
        tot_as_cy = fa_cy + inv_cy + cash_cy + oca_cy
        tot_as_py = fa_py + inv_py + cash_py + oca_py
        lines.append(_grand("TOTAL", tot_as_cy, tot_as_py))
        return lines

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

    def _trust_rp(self) -> list[FSLine]:
        lines = [_hdr("RECEIPT AND PAYMENT ACCOUNT"), _blank()]
        lines.append(_sec("RECEIPTS"))
        cash_op_cy = self._py("TR_AS009") + self._py("TR_AS010")
        lines.append(_line("Opening Balance (Cash & Bank)", cash_op_cy, 0, indent=1))
        don_cy = self._cy("TR_IN001") + self._cy("TR_IN002")
        lines.append(_line("Donations & Grants Received", don_cy, 0, indent=1))
        oi_cy = self._cy("TR_IN003") + self._cy("TR_IN004")
        lines.append(_line("Other Receipts", oi_cy, 0, indent=1))
        tot_rec = cash_op_cy + don_cy + oi_cy
        lines.append(_grand("TOTAL RECEIPTS", tot_rec, 0))
        lines.append(_blank())
        lines.append(_sec("PAYMENTS"))
        prog_cy = self._cy("TR_EX001"); adm_cy = self._cy("TR_EX002") + self._cy("TR_EX003")
        lines.append(_line("Programme Expenses Paid", prog_cy, 0, indent=1))
        lines.append(_line("Administrative Expenses Paid", adm_cy, 0, indent=1))
        cash_cl = self._cy("TR_AS009") + self._cy("TR_AS010")
        lines.append(_line("Closing Balance (Cash & Bank)", cash_cl, 0, indent=1))
        tot_pay = prog_cy + adm_cy + cash_cl
        lines.append(_grand("TOTAL PAYMENTS", tot_pay, 0))
        return lines

    # ─── SEC8 INCOME & EXPENDITURE (reads PL codes, I&E presentation) ────────

    def _sec8_ie(self) -> list[FSLine]:
        lines = [_hdr("INCOME AND EXPENDITURE ACCOUNT"), _blank()]
        lines.append(_sec("INCOME"))
        rev_cy = self._sum_cy(["CO_IN001","CO_IN002","CO_IN003"]) - self._cy("CO_EX004")
        rev_py = self._sum_py(["CO_IN001","CO_IN002","CO_IN003"]) - self._py("CO_EX004")
        lines.append(_line("I.   Income from Activities", rev_cy, rev_py, note=21, indent=1))
        oi_cy  = self._sum_cy(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        oi_py  = self._sum_py(["CO_IN005","CO_IN006","CO_IN007","CO_IN008","CO_IN009"])
        lines.append(_line("II.  Other Income", oi_cy, oi_py, note=22, indent=1))
        tot_i_cy = rev_cy + oi_cy; tot_i_py = rev_py + oi_py
        lines.append(_grand("TOTAL INCOME (I)", tot_i_cy, tot_i_py))
        lines.append(_blank())
        lines.append(_sec("EXPENDITURE"))
        emp_cy = self._sum_cy(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        emp_py = self._sum_py(["CO_EX017","CO_EX018","CO_EX019","CO_EX020","CO_EX021"])
        lines.append(_line("III. Programme / Staff Expenses", emp_cy, emp_py, note=26, indent=1))
        fin_cy = self._sum_cy(["CO_EX022","CO_EX023","CO_EX024"])
        fin_py = self._sum_py(["CO_EX022","CO_EX023","CO_EX024"])
        lines.append(_line("IV.  Finance Costs", fin_cy, fin_py, note=27, indent=1))
        dep_cy = self._cy("CO_EX025") + self._cy("CO_EX026")
        dep_py = self._py("CO_EX025") + self._py("CO_EX026")
        lines.append(_line("V.   Depreciation & Amortisation", dep_cy, dep_py, note=28, indent=1))
        oe_cy  = self._sum_cy([f"PL{i:03d}" for i in range(27, 40)])
        oe_py  = self._sum_py([f"PL{i:03d}" for i in range(27, 40)])
        lines.append(_line("VI.  Other Expenses", oe_cy, oe_py, note=29, indent=1))
        tot_e_cy = emp_cy + fin_cy + dep_cy + oe_cy
        tot_e_py = emp_py + fin_py + dep_py + oe_py
        lines.append(_grand("TOTAL EXPENDITURE (II)", tot_e_cy, tot_e_py))
        lines.append(_blank())
        sur_cy = tot_i_cy - tot_e_cy; sur_py = tot_i_py - tot_e_py
        lbl = "SURPLUS FOR THE YEAR (I–II)" if sur_cy >= 0 else "DEFICIT FOR THE YEAR (II–I)"
        lines.append(_grand(lbl, abs(sur_cy), abs(sur_py)))
        return lines

    # ─── LLP PROFIT & LOSS (LL_IN018–LL_EX027 codes) ────────────────────────────────

    def _llp_pl(self) -> list[FSLine]:
        lines = [_hdr("PROFIT AND LOSS ACCOUNT"), _blank()]
        rev_cy = self._cy("LL_IN018"); rev_py = self._py("LL_IN018")
        lines.append(_line("I.   Revenue from Operations", rev_cy, rev_py, note=14, indent=1))
        oi_cy  = self._cy("LL_IN019"); oi_py  = self._py("LL_IN019")
        lines.append(_line("II.  Other Income", oi_cy, oi_py, note=15, indent=1))
        tot_i_cy = rev_cy + oi_cy; tot_i_py = rev_py + oi_py
        lines.append(_tot("III. Total Income", tot_i_cy, tot_i_py))
        lines.append(_blank())
        lines.append(_sec("IV.  Expenses:"))
        cog_cy = self._cy("LL_EX020") + self._cy("LL_EX021")
        cog_py = self._py("LL_EX020") + self._py("LL_EX021")
        lines.append(_line("     Cost of Goods / Materials", cog_cy, cog_py, note=16, indent=2))
        emp_cy = self._cy("LL_EX022"); emp_py = self._py("LL_EX022")
        lines.append(_line("     Employee Expenses", emp_cy, emp_py, note=17, indent=2))
        rem_cy = self._cy("LL_EX023"); rem_py = self._py("LL_EX023")
        lines.append(_line("     Partners' Remuneration", rem_cy, rem_py, note=18, indent=2))
        fin_cy = self._cy("LL_EX024"); fin_py = self._py("LL_EX024")
        lines.append(_line("     Finance Costs", fin_cy, fin_py, note=19, indent=2))
        dep_cy = self._cy("LL_EX025"); dep_py = self._py("LL_EX025")
        lines.append(_line("     Depreciation & Amortisation", dep_cy, dep_py, note=20, indent=2))
        oe_cy  = self._cy("LL_EX026"); oe_py  = self._py("LL_EX026")
        lines.append(_line("     Administrative & Other Expenses", oe_cy, oe_py, note=21, indent=2))
        tax_cy = self._cy("LL_EX027"); tax_py = self._py("LL_EX027")
        lines.append(_line("     Provision for Tax", tax_cy, tax_py, indent=2))
        tot_e_cy = cog_cy + emp_cy + rem_cy + fin_cy + dep_cy + oe_cy + tax_cy
        tot_e_py = cog_py + emp_py + rem_py + fin_py + dep_py + oe_py + tax_py
        lines.append(_tot("     Total Expenses", tot_e_cy, tot_e_py))
        lines.append(_blank())
        net_cy = tot_i_cy - tot_e_cy; net_py = tot_i_py - tot_e_py
        lbl = "V.   Net Profit for the year" if net_cy >= 0 else "V.   Net Loss for the year"
        lines.append(_grand(lbl, net_cy, net_py))
        return lines

    # ─── CASH FLOW STATEMENT (Indirect Method — COMPANY / SEC8) ──────────────

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
