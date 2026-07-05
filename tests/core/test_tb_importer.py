import pytest
from core.tb_importer import _normalise, _strip_dr_cr_text, _to_float, _is_balancing_line

def test_normalise():
    assert _normalise("  Hello  World  ") == "hello world"

def test_strip_dr_cr_text():
    assert _strip_dr_cr_text("100 Dr") == "100 "
    assert _strip_dr_cr_text("100 Cr") == "100 "

def test_to_float():
    assert _to_float("1,000.50") == 1000.50
    assert _to_float("100 Dr") == -100.0
    assert _to_float("(500)") == -500.0
    assert _to_float("-") == 0.0
    assert _to_float("abc") == 0.0

def test_is_balancing_line():
    assert _is_balancing_line("Profit for the year") is True
    assert _is_balancing_line("Deficit") is True
    assert _is_balancing_line("Grand Total") is False
