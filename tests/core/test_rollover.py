import pytest
from unittest.mock import MagicMock
from pathlib import Path
from core.rollover import rollover_project
import sys
import core.rollover

def test_rollover_project(tmp_path):
    src = tmp_path / "src.sqlite"
    dest = tmp_path / "dest.sqlite"
    src.write_text("")
    
    settings_db = MagicMock()
    
    class MockDB:
        def __init__(self, path):
            self.path = path
            self._conn = MagicMock()
            self._conn.execute.return_value.fetchall.return_value = [("ledger1", "code1")]
        def connect(self): pass
        def close(self): pass
        def set_meta(self, k, v): pass
        def set_entity(self, k, v): pass
        def get_meta(self, k): return "COMPANY"
        def log(self, *args): pass
        
    orig_project_db = sys.modules.get("data.project_db")
    class MockProjectDBModule:
        ProjectDB = MockDB
    
    sys.modules["data.project_db"] = MockProjectDBModule
    try:
        res = rollover_project(src, dest, "2024-25", settings_db)
        assert res == dest
        assert dest.exists()
        settings_db.learn.assert_called_with("ledger1", "COMPANY", "code1")
    finally:
        if orig_project_db:
            sys.modules["data.project_db"] = orig_project_db
        else:
            del sys.modules["data.project_db"]
