import pytest
from unittest.mock import patch, MagicMock
from core.wtb_engine import build_wtb_lines, aggregate_by_code, apply_adjustments, validate_balance, compute_net_from_raw, WTBLine

def test_aggregate_by_code():
    lines = [
        WTBLine(1, 1, "L1", "G1", "C1", None, 1.0, "M", 100, 50, True),
        WTBLine(2, 2, "L2", "G1", "C1", None, 1.0, "M", 200, 100, True),
        WTBLine(3, 3, "L3", "G1", "C2", None, 1.0, "M", 300, 150, True),
    ]
    totals = aggregate_by_code(lines)
    assert totals["C1"] == (300.0, 150.0)
    assert totals["C2"] == (300.0, 150.0)

def test_compute_net_from_raw():
    assert compute_net_from_raw({"cy_debit": 100, "cy_credit": 40}, "DR_POSITIVE") == -60
    assert compute_net_from_raw({"cy_debit": 100, "cy_credit": 40}, "CR_POSITIVE") == -60
    assert compute_net_from_raw({"cy_net": 50}, "DR_POSITIVE") == 50

def test_apply_adjustments():
    totals = {"C1": (100.0, 50.0)}
    adj = [{"mapping_code": "C1", "dr_amount": 20, "cr_amount": 0}]
    lookup = {"C1": MagicMock(sign="DR_POSITIVE")}
    res = apply_adjustments(totals, adj, lookup)
    assert res["C1"][0] == 80.0

@patch('core.master_db.get_lookup_map')
def test_validate_balance(mock_lookup):
    mock_lookup.return_value = {
        "C1": MagicMock(fs_tag="BS", sign="DR_POSITIVE"),
        "C2": MagicMock(fs_tag="BS", sign="CR_POSITIVE")
    }
    totals = {"C1": (100.0, 50.0), "C2": (100.0, 50.0)}
    res = validate_balance(totals, "COMPANY")
    assert res.ok is True
    assert res.balance_diff_cy == 0.0
