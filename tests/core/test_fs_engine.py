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
