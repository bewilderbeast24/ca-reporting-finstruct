import pytest
from pathlib import Path
from core.ppe_template_generator import generate_ppe_template

def test_generate_ppe_template(tmp_path):
    out = tmp_path / "ppe.xlsx"
    generate_ppe_template(out)
    assert out.exists()
    assert out.stat().st_size > 0
