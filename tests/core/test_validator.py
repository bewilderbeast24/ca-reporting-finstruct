import pytest
from core.validator import ValidationReport, validate_mapping_complete, validate_balance, is_small_company, validate_cin, validate_fy, validate_pan

def test_validation_report():
    r = ValidationReport()
    assert r.ok is True
    r.fail("Error 1")
    assert r.ok is False
    assert "Error 1" in r.errors
    r.warn("Warning 1")
    assert "Warning 1" in r.warnings

def test_validate_mapping_complete():
    wtb_rows = [
        {"ledger_name": "Mapped", "mapping_code": "C1", "is_confirmed": 1},
        {"ledger_name": "Unmapped", "mapping_code": "", "is_confirmed": 0}
    ]
    r = validate_mapping_complete(wtb_rows)
    assert not r.ok
    assert "Unmapped" in r.errors[0]

def test_is_small_company():
    assert is_small_company(4_00_00_000, 40_00_00_000) is True
    assert is_small_company(4_00_00_001, 40_00_00_000) is False
    assert is_small_company(4_00_00_000, 40_00_00_001) is False

def test_validate_cin():
    assert validate_cin("U12345MH2000PTC123456") is True
    assert validate_cin("SHORT") is False

def test_validate_fy():
    assert validate_fy("2023-24") is True
    assert validate_fy("23-24") is False
    assert validate_fy("2023") is False

def test_validate_pan():
    assert validate_pan("ABCDE1234F") is True
    assert validate_pan("12345ABCDE") is False
    assert validate_pan("") is True
