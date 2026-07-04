import pytest
from pathlib import Path
from core.tb_template_generator import generate, detect_template, get_column_letter

def test_get_column_letter():
    assert get_column_letter(1) == "A"
    assert get_column_letter(26) == "Z"
    assert get_column_letter(27) == "AA"

def test_generate_tb_template(tmp_path):
    out = tmp_path / "tb.xlsx"
    generate("COMPANY", out)
    assert out.exists()
    
    etype = detect_template(out)
    assert etype == "COMPANY"
