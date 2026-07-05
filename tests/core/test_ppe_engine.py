import pytest
from core.ppe_engine import calc_slm, calc_wdv, calc_it_dep, recalc_asset, summarize_ppe

def test_calc_slm():
    res = calc_slm(gross_op=1000, additions=200, disposals=0, dep_op=100, dep_disposal=0, life_yrs=10)
    assert res["gross_cl"] == 1200
    assert res["dep_charge"] == 120.0
    assert res["dep_cl"] == 220.0
    assert res["nbv_cy"] == 980.0

def test_calc_wdv():
    res = calc_wdv(gross_op=1000, additions=0, disposals=0, dep_op=100, dep_disposal=0, rate=10.0)
    assert res["dep_charge"] == 90.0
    assert res["gross_cl"] == 1000
    assert res["dep_cl"] == 190.0
    assert res["nbv_cy"] == 810.0

def test_calc_it_dep():
    res = calc_it_dep(1000, 200, 100, 0, 0, 10.0)
    assert res["it_dep_full"] == 120.0
    assert res["it_dep_half"] == 5.0
    assert res["it_dep"] == 125.0
    assert res["it_wdv_cl"] == 1175.0

def test_recalc_asset():
    asset = {"method": "SLM", "useful_life_yrs": 10, "it_rate": 10, "gross_op": 1000, "dep_op": 100, "it_wdv_op": 800}
    res = recalc_asset(asset)
    assert res["nbv_cy"] == 800.0

def test_summarize_ppe():
    assets = [
        {"method": "SLM", "useful_life_yrs": 10, "it_rate": 10, "gross_op": 1000, "dep_op": 100},
        {"method": "SLM", "useful_life_yrs": 10, "it_rate": 10, "gross_op": 500, "dep_op": 50},
    ]
    totals = summarize_ppe(assets)
    assert totals["gross_op"] == 1500
    assert totals["dep_op"] == 150
