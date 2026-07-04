import pytest
from unittest.mock import MagicMock
from core.mapper import Mapper, MappingResult

def test_mapper_exact_match():
    settings = MagicMock()
    settings.lookup.return_value = None
    
    import core.master_db
    class MockEntry:
        def __init__(self, code, lookup_name, entity_types, sub_heading=""):
            self.code = code
            self.lookup_name = lookup_name
            self.entity_types = entity_types
            self.sub_heading = sub_heading
            
    # Save original MASTER
    import core.mapper
    orig = core.mapper.MASTER
    core.mapper.MASTER = [
        MockEntry("C1", "Cash", ["COMPANY"]),
        MockEntry("C2", "Bank", ["COMPANY"])
    ]
    
    try:
        mapper = Mapper("COMPANY", settings)
        res = mapper.map_ledger("Cash")
        assert res.code == "C1"
        assert res.source == "EXACT"
    finally:
        core.mapper.MASTER = orig

def test_mapper_learned():
    settings = MagicMock()
    settings.lookup.return_value = "C2"
    
    mapper = Mapper("COMPANY", settings)
    res = mapper.map_ledger("Bank Account")
    assert res.code == "C2"
    assert res.source == "LEARNED"
