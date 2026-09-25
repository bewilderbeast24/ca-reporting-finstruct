import pytest
from core.fs_engine import FSLine, FSDocument, FSEngine, _r

def test_fs_line():
    l = FSLine("Total", 100, 50, note=None, indent=0, row_type="TOTAL")
    assert l.cy == 100
    assert l.py == 50
    assert l.row_type == "TOTAL"

def test_round():
    assert _r(1500, 1000) == 1.5
    assert _r(1500, 1) == 1500.0

def test_fs_engine_init():
    engine = FSEngine(entity_type="COMPANY", totals={}, entity_master={}, fy="2024-25")
    assert engine._etype == "COMPANY"
    
def test_fs_document():
    doc = FSDocument(entity_type="COMPANY", fy="2024-25", entity_master={}, divisor=1)
    assert doc.entity_type == "COMPANY"
    assert doc.fy == "2024-25"
    doc.bs.append(FSLine("Line", 10, 5, note=None, indent=0, row_type="DATA"))
    assert len(doc.bs) == 1


def test_fs_engine_bs_includes_shareholders_funds_in_totals():
    """Verify Shareholders Funds is included in TOTAL — EQUITY AND LIABILITIES and balances with assets."""
    # TB convention: Credit = negative, Debit = positive.
    # EL/Revenue credits arrive negative and are flipped *-1 in FS.
    totals = {
        "CO_EL001": (-100000.0, -80000.0),   # Share Capital (Shareholders Funds)
        "CO_EL003": (-25000.0, -20000.0),    # Reserves & Surplus (Shareholders Funds)
        "CO_EL020": (-50000.0, -40000.0),    # Short Term Borrowings (Current Liabilities)
        "CO_AS001": (-175000.0, -140000.0) # PPE (Non-Current Assets)
    }
    engine = FSEngine(entity_type="COMPANY", totals=totals, entity_master={}, fy="2024-25", divisor=1)
    doc = engine.generate()

    # Find the grand total lines and subtotal lines
    sf_subtotal = next((l for l in doc.bs if l.label.endswith("— Shareholders Funds") and l.row_type == "TOTAL"), None)
    cl_subtotal = next((l for l in doc.bs if l.label.endswith("— Current Liabilities") and l.row_type == "TOTAL"), None)
    tot_el = next((l for l in doc.bs if l.label == "TOTAL — EQUITY AND LIABILITIES" and l.row_type == "GRAND"), None)
    tot_as = next((l for l in doc.bs if l.label == "TOTAL — ASSETS" and l.row_type == "GRAND"), None)

    assert sf_subtotal is not None
    assert sf_subtotal.cy == 125000.0
    assert sf_subtotal.py == 100000.0

    assert cl_subtotal is not None
    assert cl_subtotal.cy == 50000.0
    assert cl_subtotal.py == 40000.0

    assert tot_el is not None
    # 125,000 (SF) + 50,000 (CL) = 175,000
    assert tot_el.cy == 175000.0
    assert tot_el.py == 140000.0

    assert tot_as is not None
    assert tot_as.cy == 175000.0
    assert tot_as.py == 140000.0

    assert doc.is_balanced is True
    assert doc.balance_diff_cy == 0.0


def test_fs_engine_bs_imbalance_detected():
    """Verify imbalance is properly detected and flagged."""
    totals = {
        "CO_EL001": (-100000.0, 0.0),    # Share Capital: 100k credit (negative in TB)
        "CO_EL020": (-50000.0, 0.0),     # Short Term Borrowings: 50k credit (negative in TB)
        "CO_AS001": (-160000.0, 0.0)    # Assets: 160k (10k imbalance)
    }
    engine = FSEngine(entity_type="COMPANY", totals=totals, entity_master={}, fy="2024-25", divisor=1)
    doc = engine.generate()

    assert doc.is_balanced is False
    assert doc.balance_diff_cy == -10000.0
    imbalance_line = next((l for l in doc.bs if "BS imbalance" in l.label), None)
    assert imbalance_line is not None
    assert "-10,000.00" in imbalance_line.label


def test_fs_engine_bs_non_corporate_totals():
    """Verify non-corporate entity formats generate TOTAL — FUNDS & LIABILITIES."""
    totals = {
        "LL_EL001": (-80000.0, 0.0),     # Partners' Capital (credit-negative)
        "LL_EL007": (-20000.0, 0.0),     # Current Liabilities (credit-negative)
        "LL_AS010": (-100000.0, 0.0)    # Fixed Assets
    }
    engine = FSEngine(entity_type="LLP", totals=totals, entity_master={}, fy="2024-25", divisor=1)
    doc = engine.generate()

    tot_fl = next((l for l in doc.bs if l.label == "TOTAL — FUNDS & LIABILITIES" and l.row_type == "GRAND"), None)
    tot_as = next((l for l in doc.bs if l.label == "TOTAL — ASSETS" and l.row_type == "GRAND"), None)

    assert tot_fl is not None
    assert tot_fl.cy == 100000.0
    assert tot_as is not None
    assert tot_as.cy == 100000.0
    assert doc.is_balanced is True


def test_fs_engine_bs_unclosed_pl_transferred_to_reserves():
    """Verify unclosed P&L net profit is included in Reserves & Surplus on Balance Sheet."""
    totals = {
        "CO_EL001": (-100000.0, 0.0),    # Share Capital (credit-negative)
        "CO_AS023": (-120000.0, 0.0),   # Cash & Bank
        "CO_IN001": (-50000.0, 0.0),     # Revenue (Credit-negative -> flipped to +50k)
        "CO_EX020": (-30000.0, 0.0)     # Expense (Debit) -> Net PAT = 20,000
    }
    engine = FSEngine(entity_type="COMPANY", totals=totals, entity_master={}, fy="2024-25", divisor=1)
    doc = engine.generate()

    tot_el = next((l for l in doc.bs if l.label == "TOTAL — EQUITY AND LIABILITIES" and l.row_type == "GRAND"), None)
    tot_as = next((l for l in doc.bs if l.label == "TOTAL — ASSETS" and l.row_type == "GRAND"), None)

    assert tot_el is not None
    assert tot_el.cy == 120000.0
    assert tot_as is not None
    assert tot_as.cy == 120000.0
    assert doc.is_balanced is True
