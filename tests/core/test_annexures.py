import pytest
from core.annexures import ANNEXURE_DEFS, AnnexureRow, AnnexureData, compute_tb_total, build_blank_annexure, load_annexure, save_annexure

def test_annexure_defs():
    assert "TR_AGEING" in ANNEXURE_DEFS
    assert "TP_AGEING" in ANNEXURE_DEFS

def test_compute_tb_total():
    totals = {
        "CO_AS020": (100, 50),
        "CO_AS021": (200, 100),
        "CO_AS022": (50, 20)
    }
    cy, py = compute_tb_total("TR_AGEING", totals)
    assert cy == 250.0
    assert py == 130.0

def test_annexure_data_recompute():
    a = AnnexureData("TEST", "Test", 1, 100.0, 50.0)
    a.rows = [AnnexureRow("Row 1", 60.0, 30.0), AnnexureRow("Row 2", 40.0, 20.0)]
    a.recompute()
    assert a.variance_cy == 0.0
    assert a.variance_py == 0.0
    assert a.is_balanced is True

    a.rows[0].cy_value = 50.0
    a.recompute()
    assert a.variance_cy == 10.0
    assert a.is_balanced is True

def test_build_blank_annexure():
    totals = {"CO_AS020": (100, 50)}
    annx = build_blank_annexure("TR_AGEING", totals)
    assert annx.code == "TR_AGEING"
    assert len(annx.rows) > 0
    assert annx.tb_total_cy == 100.0
