"""Declarative layouts for all Financial Statements.
Separates presentation structure from data aggregation logic.
"""

from typing import Literal, TypedDict, Union, List, Optional

LineType = Literal["HEADER", "SECTION", "SUBSECTION", "DATA", "TOTAL", "GRAND", "BLANK", "TEXT"]

class FSLineDef(TypedDict, total=False):
    type: LineType
    label: str
    indent: int
    group: Optional[str]      # If present, sum all codes in this master_db group
    heading: Optional[str]    # If present, sum all codes with this master_db heading
    code: Optional[str]       # Single code mapping
    codes: Optional[List[str]] # Multiple explicit codes
    formula: Optional[str]    # Custom calculation (e.g. "PPE_GROSS - PPE_DEP")
    note: Optional[int]
    fs_tag: Optional[str]     # Override default fs_tag (e.g. "BS", "PL")

class FSReportSchema(TypedDict):
    title: str
    layout: List[FSLineDef]

# --- COMPANY BALANCE SHEET (SCHEDULE III) ---
COMPANY_BS_SCHEMA: FSReportSchema = {
    "title": "BALANCE SHEET",
    "layout": [
        {"type": "HEADER", "label": "BALANCE SHEET"},
        {"type": "SECTION", "label": "I. EQUITY AND LIABILITIES"},
        
        # Shareholders' Funds
        {"type": "SUBSECTION", "label": "1. Shareholders' Funds", "indent": 1},
        {"type": "DATA", "label": "    (a) Share Capital", "heading": "Share Capital", "note": 3, "indent": 2},
        {"type": "DATA", "label": "    (b) Reserves & Surplus", "heading": "Reserves & Surplus", "note": 4, "indent": 2},
        {"type": "DATA", "label": "    (c) Money received against Share Warrants", "heading": "Share App Money Pending Allotment", "indent": 2},
        {"type": "TOTAL", "label": "    Sub-total — Shareholders' Funds (A)", "formula": "GROUP:Shareholders Funds"},
        
        # Non-Current Liabilities
        {"type": "SUBSECTION", "label": "2. Non-Current Liabilities", "indent": 1},
        {"type": "DATA", "label": "    (a) Long-term Borrowings", "heading": "Long Term Borrowings", "note": 5, "indent": 2},
        {"type": "DATA", "label": "    (b) Deferred Tax Liabilities (Net)", "heading": "Deferred Tax Liability", "indent": 2},
        {"type": "DATA", "label": "    (c) Other Long-term Liabilities", "heading": "Other Long Term Liabilities", "note": 6, "indent": 2},
        {"type": "DATA", "label": "    (d) Long-term Provisions", "heading": "Long Term Provisions", "note": 7, "indent": 2},
        {"type": "TOTAL", "label": "    Sub-total — Non-Current Liabilities (B)", "formula": "GROUP:Non-Current Liabilities"},
        
        # Current Liabilities
        {"type": "SUBSECTION", "label": "3. Current Liabilities", "indent": 1},
        {"type": "DATA", "label": "    (a) Short-term Borrowings", "heading": "Short Term Borrowings", "note": 8, "indent": 2},
        {"type": "DATA", "label": "    (b) Trade Payables", "heading": "Trade Payables", "note": 9, "indent": 2},
        {"type": "DATA", "label": "    (c) Other Current Liabilities", "heading": "Other Current Liabilities", "note": 10, "indent": 2},
        {"type": "DATA", "label": "    (d) Short-term Provisions", "heading": "Short Term Provisions", "note": 11, "indent": 2},
        {"type": "TOTAL", "label": "    Sub-total — Current Liabilities (C)", "formula": "GROUP:Current Liabilities"},
        
        {"type": "GRAND", "label": "TOTAL — EQUITY AND LIABILITIES (A+B+C)", "formula": "SECTION:I. EQUITY AND LIABILITIES"},

        {"type": "SECTION", "label": "II. ASSETS"},
        
        # Non-Current Assets
        {"type": "SUBSECTION", "label": "1. Non-Current Assets", "indent": 1},
        {"type": "DATA", "label": "    (a) Fixed Assets (Net Block)", "formula": "HEADING:Property Plant & Equipment + HEADING:Intangible Assets", "note": 12, "indent": 2},
        {"type": "DATA", "label": "    (b) Non-Current Investments", "heading": "Non-Current Investments", "note": 13, "indent": 2},
        {"type": "DATA", "label": "    (c) Deferred Tax Assets (Net)", "heading": "Deferred Tax Asset", "indent": 2},
        {"type": "DATA", "label": "    (d) Long-term Loans & Advances", "heading": "Long Term Loans & Advances", "note": 14, "indent": 2},
        {"type": "DATA", "label": "    (e) Other Non-Current Assets", "heading": "Other Non-Current Assets", "note": 15, "indent": 2},
        {"type": "TOTAL", "label": "    Sub-total — Non-Current Assets (D)", "formula": "GROUP:Non-Current Assets"},

        # Current Assets
        {"type": "SUBSECTION", "label": "2. Current Assets", "indent": 1},
        {"type": "DATA", "label": "    (a) Inventories", "heading": "Inventories", "note": 16, "indent": 2},
        {"type": "DATA", "label": "    (b) Trade Receivables", "heading": "Trade Receivables", "note": 17, "indent": 2},
        {"type": "DATA", "label": "    (c) Cash and Cash Equivalents", "heading": "Cash & Cash Equivalents", "note": 18, "indent": 2},
        {"type": "DATA", "label": "    (d) Short-term Loans & Advances", "heading": "Short Term Loans & Advances", "note": 19, "indent": 2},
        {"type": "DATA", "label": "    (e) Other Current Assets", "heading": "Other Current Assets", "note": 20, "indent": 2},
        {"type": "TOTAL", "label": "    Sub-total — Current Assets (E)", "formula": "GROUP:Current Assets"},
        
        {"type": "GRAND", "label": "TOTAL — ASSETS (D+E)", "formula": "GROUP:Current Assets + GROUP:Non-Current Assets"},
    ]
}

# --- LLP BALANCE SHEET ---
LLP_BS_SCHEMA: FSReportSchema = {
    "title": "BALANCE SHEET",
    "layout": [
        {"type": "HEADER", "label": "BALANCE SHEET"},
        {"type": "BLANK"},
        {"type": "SECTION", "label": "FUNDS & LIABILITIES"},
        {"type": "DATA", "label": "I.   Partners' Capital Account", "heading": "Partners' Capital Account", "note": 1, "indent": 1},
        {"type": "DATA", "label": "II.  Reserves & Surplus", "heading": "Reserves & Surplus", "note": 2, "indent": 1},
        {"type": "DATA", "label": "III. Secured Loans", "heading": "Secured Loans", "note": 3, "indent": 1},
        {"type": "DATA", "label": "IV.  Unsecured Loans", "heading": "Unsecured Loans", "note": 4, "indent": 1},
        {"type": "DATA", "label": "V.   Current Liabilities & Provisions", "heading": "Current Liabilities & Provisions", "note": 5, "indent": 1},
        {"type": "GRAND", "label": "TOTAL — LIABILITIES", "formula": "GROUP:Funds & Liabilities"},
        {"type": "BLANK"},
        {"type": "SECTION", "label": "ASSETS"},
        {"type": "DATA", "label": "I.   Fixed Assets (Net Block)", "heading": "Fixed Assets", "note": 8, "indent": 1},
        {"type": "DATA", "label": "II.  Investments", "heading": "Investments", "note": 9, "indent": 1},
        {"type": "DATA", "label": "III. Cash & Bank Balances", "heading": "Cash & Bank Balances", "note": 10, "indent": 1},
        {"type": "DATA", "label": "IV.  Trade Receivables", "heading": "Trade Receivables", "note": 11, "indent": 1},
        {"type": "DATA", "label": "V.   Loans & Advances", "heading": "Loans & Advances", "note": 12, "indent": 1},
        {"type": "DATA", "label": "VI.  Other Current Assets", "heading": "Other Current Assets", "note": 13, "indent": 1},
        {"type": "GRAND", "label": "TOTAL — ASSETS", "formula": "GROUP:Assets"},
    ]
}

# --- COMPANY P&L (SCHEDULE III) ---
COMPANY_PL_SCHEMA: FSReportSchema = {
    "title": "STATEMENT OF PROFIT AND LOSS",
    "layout": [
        {"type": "HEADER", "label": "STATEMENT OF PROFIT AND LOSS"},
        {"type": "BLANK"},
        {"type": "DATA", "label": "I.   Revenue from Operations", "heading": "Revenue from Operations", "note": 21, "indent": 1},
        {"type": "DATA", "label": "II.  Other Income", "heading": "Other Income", "note": 22, "indent": 1},
        {"type": "TOTAL", "label": "III. Total Revenue (I + II)", "formula": "HEADING:Revenue from Operations + HEADING:Other Income"},
        {"type": "BLANK"},
        {"type": "SECTION", "label": "IV.  Expenses:"},
        {"type": "DATA", "label": "     Cost of Materials Consumed", "heading": "Cost of Materials Consumed", "note": 23, "indent": 2},
        {"type": "DATA", "label": "     Purchases of Stock-in-Trade", "heading": "Purchases of Stock-in-Trade", "note": 24, "indent": 2},
        {"type": "DATA", "label": "     Changes in Inventories", "heading": "Changes in Inventories", "note": 25, "indent": 2},
        {"type": "DATA", "label": "     Employee Benefit Expenses", "heading": "Employee Benefit Expenses", "note": 26, "indent": 2},
        {"type": "DATA", "label": "     Finance Costs", "heading": "Finance Costs", "note": 27, "indent": 2},
        {"type": "DATA", "label": "     Depreciation & Amortisation", "heading": "Depreciation & Amortisation", "note": 28, "indent": 2},
        {"type": "DATA", "label": "     Other Expenses", "heading": "Other Expenses", "note": 29, "indent": 2},
        {"type": "TOTAL", "label": "     Total Expenses (IV)", "formula": "GROUP:Expenses"},
        {"type": "BLANK"},
        {"type": "GRAND", "label": "V.   Profit/(Loss) before Tax (III – IV)", "formula": "(HEADING:Revenue from Operations + HEADING:Other Income) - GROUP:Expenses"},
        {"type": "DATA", "label": "VI.  Tax Expense", "heading": "Tax Expense", "indent": 1},
        {"type": "GRAND", "label": "VII. Profit/(Loss) after Tax (V – VI)", "formula": "((HEADING:Revenue from Operations + HEADING:Other Income) - GROUP:Expenses) - HEADING:Tax Expense"},
    ]
}

# --- RECEIPTS & PAYMENTS ACCOUNT ---
AOP_RP_SCHEMA: FSReportSchema = {
    "title": "RECEIPT AND PAYMENT ACCOUNT",
    "layout": [
        {"type": "HEADER", "label": "RECEIPT AND PAYMENT ACCOUNT"},
        {"type": "BLANK"},
        {"type": "SECTION", "label": "RECEIPTS"},
        # Note: RP opening balance usually comes from PY Assets (Cash & Bank)
        # For now, we'll use a special formula or let the engine handle it.
        {"type": "DATA", "label": "Opening Balance (Cash & Bank)", "formula": "HEADING:Cash & Bank Balances", "indent": 1},
        {"type": "DATA", "label": "Maintenance Charges Received", "heading": "Maintenance Income", "indent": 1},
        {"type": "DATA", "label": "Other Receipts", "heading": "Other Income", "indent": 1},
        {"type": "GRAND", "label": "TOTAL RECEIPTS (A)", "formula": "HEADING:Cash & Bank Balances + HEADING:Maintenance Income + HEADING:Other Income"},
        {"type": "BLANK"},
        {"type": "SECTION", "label": "PAYMENTS"},
        {"type": "DATA", "label": "Establishment Expenses", "heading": "Establishment Expenses", "indent": 1},
        {"type": "DATA", "label": "Maintenance Expenses", "heading": "Maintenance Expenses", "indent": 1},
        {"type": "DATA", "label": "Administrative Expenses", "heading": "Administrative Expenses", "indent": 1},
        {"type": "DATA", "label": "Closing Balance (Cash & Bank)", "heading": "Cash & Bank Balances", "indent": 1},
        {"type": "GRAND", "label": "TOTAL PAYMENTS (B)", "formula": "HEADING:Establishment Expenses + HEADING:Maintenance Expenses + HEADING:Administrative Expenses + HEADING:Cash & Bank Balances"},
    ]
}
