import pytest
from core.master_db import MappingEntry, get_master, get_lookup_map, get_entry, validate_master

def test_mapping_entry():
    entry = MappingEntry(code="C1", entity_types=("COMPANY",), group="G1", heading="SH1", sub_heading="LN1", fs_tag="BS", sign="DR_POSITIVE", note_number=1, small_co_exempt=False)
    assert entry.code == "C1"
    assert entry.group == "G1"
    assert entry.sub_heading == "LN1"
    assert entry.lookup_name == "G1 > SH1 > LN1"
    assert entry.fs_tag == "BS"

def test_get_master():
    m = get_master(["COMPANY"])
    assert isinstance(m, list)

def test_get_lookup_map():
    lm = get_lookup_map()
    assert isinstance(lm, dict)

def test_get_entry():
    entry = get_entry("CO_EL001")
    if entry:
        assert entry.code == "CO_EL001"
        
def test_validate_master():
    errors = validate_master()
    assert isinstance(errors, list)
