import pytest
import sqlite3
from datetime import datetime

from data.settings_db import SettingsDB

@pytest.fixture
def temp_settings_db(tmp_path, monkeypatch):
    db_path = tmp_path / "settings.db"
    monkeypatch.setattr("data.settings_db.SETTINGS_DB", str(db_path))
    # Reset singleton instance to ensure clean state
    SettingsDB._instance = None
    db = SettingsDB.instance()
    yield db
    if db._conn:
        db._conn.close()
    SettingsDB._instance = None

def test_singleton(temp_settings_db):
    db1 = SettingsDB.instance()
    db2 = SettingsDB.instance()
    assert db1 is db2

def test_settings_get_set(temp_settings_db):
    assert temp_settings_db.get("nonexistent") == ""
    assert temp_settings_db.get("nonexistent", "default") == "default"
    
    temp_settings_db.set("test_key", "test_value")
    assert temp_settings_db.get("test_key") == "test_value"
    
    temp_settings_db.set("test_key", "updated_value")
    assert temp_settings_db.get("test_key") == "updated_value"

def test_api_keys_and_providers(temp_settings_db):
    assert temp_settings_db.get_api_key("Claude") == ""
    
    temp_settings_db.set_api_key("test_api_key_123", "Claude")
    assert temp_settings_db.get_api_key("Claude") == "test_api_key_123"
    
    # check encryption
    raw_val = temp_settings_db.get("claude_api_key")
    assert raw_val != "test_api_key_123"
    assert raw_val != ""
    
    temp_settings_db.set_api_key("", "Claude")
    assert temp_settings_db.get_api_key("Claude") == ""
    
    assert temp_settings_db.get_ai_provider() == "Claude"
    temp_settings_db.set_ai_provider("OpenAI")
    assert temp_settings_db.get_ai_provider() == "OpenAI"

def test_annexure_tolerance(temp_settings_db):
    assert temp_settings_db.get_annexure_tolerance() == 10.0
    
    temp_settings_db.set_annexure_tolerance(15.5)
    assert temp_settings_db.get_annexure_tolerance() == 15.5
    
    temp_settings_db.set("annexure_tolerance", "invalid")
    assert temp_settings_db.get_annexure_tolerance() == 10.0

def test_recent_projects(temp_settings_db):
    temp_settings_db.add_recent("/path/to/proj1", "Project 1", "Company", "2023-24")
    temp_settings_db.add_recent("/path/to/proj2", "Project 2", "LLP", "2023-24")
    
    recent = temp_settings_db.get_recent()
    assert len(recent) == 2
    assert recent[0]["path"] == "/path/to/proj2" # added later, so descending last_opened
    assert recent[1]["path"] == "/path/to/proj1"
    
    temp_settings_db.remove_recent("/path/to/proj2")
    recent = temp_settings_db.get_recent()
    assert len(recent) == 1
    assert recent[0]["path"] == "/path/to/proj1"

def test_learned_mappings(temp_settings_db):
    assert temp_settings_db.lookup("Office Exp", "Company") is None
    
    temp_settings_db.learn("Office Exp", "Company", "EXP_OFFICE")
    assert temp_settings_db.lookup("Office Exp", "Company") == "EXP_OFFICE"
    
    # Check case insensitivity
    assert temp_settings_db.lookup("OFFICE EXP", "Company") == "EXP_OFFICE"
    
    # Increment count and update mapping code
    temp_settings_db.learn("Office Exp", "Company", "EXP_OFFICE_UPDATED")
    assert temp_settings_db.lookup("Office Exp", "Company") == "EXP_OFFICE_UPDATED"
    
    row = temp_settings_db._conn.execute(
        "SELECT confirmed_count FROM learned_mappings WHERE ledger_name='office exp'"
    ).fetchone()
    assert row[0] == 2
    
    temp_settings_db.learn("Bank Charges", "Company", "EXP_BANK")
    
    all_learned = temp_settings_db.get_all_learned("Company")
    assert len(all_learned) == 2
    assert all_learned["office exp"] == "EXP_OFFICE_UPDATED"
    assert all_learned["bank charges"] == "EXP_BANK"
