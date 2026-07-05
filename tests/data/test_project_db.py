import pytest
import sqlite3
from pathlib import Path
from datetime import datetime

from data.project_db import ProjectDB
from data.encryption import encrypt, decrypt

@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "test_project.db"

@pytest.fixture
def project_db(temp_db_path):
    db = ProjectDB(temp_db_path)
    db.connect()
    yield db
    db.close()

def test_project_db_init(temp_db_path):
    db = ProjectDB(temp_db_path)
    assert db.path == temp_db_path
    assert db._conn is None

def test_connect_close(temp_db_path):
    db = ProjectDB(temp_db_path)
    db.connect()
    assert db._conn is not None
    # schema should be initialized
    assert db.get_meta("schema_version") == "3"
    db.close()
    assert db._conn is None

def test_schema_migrations(temp_db_path):
    # Simulate version 1 schema
    conn = sqlite3.connect(temp_db_path)
    conn.executescript("""
        CREATE TABLE project_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO project_meta(key, value) VALUES('schema_version', '1');
        CREATE TABLE raw_tb (id INTEGER PRIMARY KEY);
        CREATE TABLE wtb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_tb_id INTEGER,
            mapping_code TEXT,
            confidence REAL DEFAULT 0,
            confidence_source TEXT DEFAULT 'MANUAL',
            cy_net REAL DEFAULT 0,
            py_net REAL DEFAULT 0,
            is_confirmed INTEGER DEFAULT 0
        );
    """)
    conn.close()
    
    db = ProjectDB(temp_db_path)
    db.connect()
    
    # Should migrate to v3
    assert db.get_meta("schema_version") == "3"
    
    # Verify annexure_rows table exists (v3 migration)
    assert isinstance(db.get_all_annexure_codes(), list)
    
    # Verify wtb has unique constraint (v2 migration)
    with pytest.raises(sqlite3.IntegrityError):
        db._conn.execute("INSERT INTO raw_tb (id) VALUES (1)")
        db._conn.execute("INSERT INTO raw_tb (id) VALUES (2)")
        db._conn.execute("INSERT INTO wtb(raw_tb_id) VALUES(1)")
        db._conn.execute("INSERT INTO wtb(raw_tb_id) VALUES(1)") # Should fail due to UNIQUE constraint
    db.close()

def test_meta_operations(project_db):
    project_db.set_meta("test_key", "test_value")
    assert project_db.get_meta("test_key") == "test_value"
    
    project_db.set_meta("test_key", "updated_value")
    assert project_db.get_meta("test_key") == "updated_value"
    
    all_meta = project_db.get_all_meta()
    assert "test_key" in all_meta
    assert all_meta["test_key"] == "updated_value"
    assert "schema_version" in all_meta
    
def test_entity_master_operations(project_db):
    # Non-PII
    project_db.set_entity("company_name", "Test Corp")
    assert project_db.get_entity("company_name") == "Test Corp"
    
    # PII (e.g. pan)
    project_db.set_entity("pan", "ABCDE1234F")
    assert project_db.get_entity("pan") == "ABCDE1234F"
    
    # check if encrypted in DB
    raw_row = project_db._conn.execute("SELECT value FROM entity_master WHERE key='pan'").fetchone()
    assert raw_row[0] != "ABCDE1234F" # Should be encrypted
    
    project_db.save_entity_batch({"address": "123 Street", "phone": "123456"})
    assert project_db.get_entity("address") == "123 Street"
    assert project_db.get_entity("phone") == "123456"
    
    all_entities = project_db.get_all_entity()
    assert all_entities["company_name"] == "Test Corp"
    assert all_entities["pan"] == "ABCDE1234F"
    assert all_entities["address"] == "123 Street"

def test_directors_operations(project_db):
    dir_id1 = project_db.upsert_director({
        "name": "John Doe", "din": "12345678", "pan": "ABCDE1111A", "sort_order": 1
    })
    dir_id2 = project_db.upsert_director({
        "name": "Jane Smith", "din": "87654321", "pan": "ABCDE2222B", "sort_order": 0
    })
    
    directors = project_db.get_directors()
    assert len(directors) == 2
    assert directors[0]["name"] == "Jane Smith" # due to sort order
    assert directors[0]["din"] == "87654321"
    assert directors[1]["name"] == "John Doe"
    
    # Update
    project_db.upsert_director({
        "id": dir_id1, "name": "John Doe Updated", "din": "12345678", "sort_order": 1
    })
    directors = project_db.get_directors()
    assert directors[1]["name"] == "John Doe Updated"
    
    # Delete
    project_db.delete_director(dir_id2)
    assert len(project_db.get_directors()) == 1

def test_migrate_legacy_directors(project_db):
    # clear directors table
    project_db._conn.execute("DELETE FROM directors")
    project_db._conn.commit()
    
    project_db.set_entity("dir1_name", "Legacy Dir 1")
    project_db.set_entity("dir1_din", "11111111")
    project_db.set_entity("dir2_name", "Legacy Dir 2")
    project_db.set_entity("dir2_din", "22222222")
    
    project_db.migrate_legacy_directors()
    directors = project_db.get_directors()
    assert len(directors) == 2
    assert directors[0]["name"] == "Legacy Dir 1"
    assert directors[0]["din"] == "11111111"
    assert directors[1]["name"] == "Legacy Dir 2"

def test_raw_tb_operations(project_db):
    data = [
        {"ledger_name": "Cash", "group_name": "Assets", "cy_debit": 100, "cy_credit": 0, "cy_net": 100, "py_net": 50, "source": "MANUAL"},
        {"ledger_name": "Sales", "group_name": "Revenue", "cy_debit": 0, "cy_credit": 200, "cy_net": -200, "py_net": -150, "source": "MANUAL"}
    ]
    project_db.insert_raw_tb_batch(data)
    
    tb = project_db.get_raw_tb()
    assert len(tb) == 2
    assert tb[0]["ledger_name"] == "Cash"
    assert tb[1]["cy_net"] == -200
    
    project_db.clear_raw_tb()
    assert len(project_db.get_raw_tb()) == 0
    # clearing raw tb also clears wtb
    assert len(project_db.get_wtb()) == 0

def test_wtb_operations(project_db):
    project_db.insert_raw_tb_batch([
        {"ledger_name": "Cash", "group_name": "Assets", "cy_debit": 100, "cy_credit": 0, "cy_net": 100, "py_net": 50, "source": "MANUAL"},
        {"ledger_name": "Bank", "group_name": "Assets", "cy_debit": 50, "cy_credit": 0, "cy_net": 50, "py_net": 20, "source": "MANUAL"}
    ])
    tb = project_db.get_raw_tb()
    raw_tb_id1 = tb[0]["id"]
    raw_tb_id2 = tb[1]["id"]
    
    project_db.upsert_wtb(raw_tb_id1, "CASH_1", 0.9, "AI", 100, 50, 0)
    project_db.upsert_wtb(raw_tb_id2, "BANK_1", 0.8, "AI", 50, 20, 0)
    
    wtb = project_db.get_wtb()
    assert len(wtb) == 2
    
    project_db.confirm_mapping(raw_tb_id1, "CASH_CONFIRMED")
    wtb = project_db.get_wtb()
    
    # Verify mapping confirmed
    confirmed_row = next(r for r in wtb if r["raw_tb_id"] == raw_tb_id1)
    assert confirmed_row["mapping_code"] == "CASH_CONFIRMED"
    assert confirmed_row["is_confirmed"] == 1
    
    assert project_db.unconfirmed_count() == 1
    
    sums = project_db.sum_by_code()
    assert sums["CASH_CONFIRMED"] == (100, 50)
    assert sums["BANK_1"] == (50, 20)

def test_adjustments_operations(project_db):
    project_db.add_adjustment("ADJ-1", "Depreciation", "DEP", 100, 0, "Dep for the year")
    project_db.add_adjustment("ADJ-2", "Acc. Dep", "ACC_DEP", 0, 100, "Acc Dep")
    project_db.add_adjustment("DEP-1", "Auto Dep", "DEP", 50, 0, "Auto Dep")
    
    adjs = project_db.get_adjustments()
    assert len(adjs) == 3
    
    project_db.delete_dep_adjustments()
    adjs = project_db.get_adjustments()
    assert len(adjs) == 2
    assert "DEP-1" not in [a["adj_id"] for a in adjs]

def test_ppe_operations(project_db):
    project_db.upsert_ppe({
        "asset_name": "Laptop", "category": "Computers", "method": "SLM",
        "gross_op": 1000, "additions": 200, "dep_op": 100, "dep_charge": 200
    })
    ppe = project_db.get_ppe()
    assert len(ppe) == 1
    assert ppe[0]["asset_name"] == "Laptop"
    assert ppe[0]["gross_op"] == 1000
    
    asset_id = ppe[0]["id"]
    project_db.upsert_ppe({
        "id": asset_id, "asset_name": "Laptop Pro", "gross_op": 1200
    })
    ppe = project_db.get_ppe()
    assert len(ppe) == 1
    assert ppe[0]["asset_name"] == "Laptop Pro"
    assert ppe[0]["gross_op"] == 1200
    
    project_db.delete_ppe(asset_id)
    assert len(project_db.get_ppe()) == 0

def test_fs_overrides_operations(project_db):
    project_db.set_override("BS", "SHARE_CAP", 5000, 4000, "Manual correction")
    project_db.set_override("BS", "RES_SURP", 2000, 1500)
    
    overrides = project_db.get_overrides("BS")
    assert overrides["SHARE_CAP"] == (5000, 4000)
    assert overrides["RES_SURP"] == (2000, 1500)
    
    assert len(project_db.get_overrides("PL")) == 0

def test_note_data_operations(project_db):
    project_db.save_note_line(1, 1, "Authorised Capital", 10000, 10000)
    project_db.save_note_line(1, 2, "Issued Capital", 5000, 5000, "SUB_TOTAL")
    
    note = project_db.get_note_data(1)
    assert note[1]["label"] == "Authorised Capital"
    assert note[1]["cy_value"] == 10000
    assert note[2]["row_type"] == "SUB_TOTAL"
    assert note[2]["py_value"] == 5000

def test_audit_log_operations(project_db):
    project_db.log("TEST_ACTION", "Test Detail")
    project_db.log("TEST_ACTION_2")
    
    logs = project_db.get_audit_log(10)
    assert len(logs) == 2
    assert logs[0]["action"] == "TEST_ACTION_2"  # Descending order
    assert logs[1]["action"] == "TEST_ACTION"
    assert logs[1]["detail"] == "Test Detail"

def test_annexure_rows_operations(project_db):
    project_db.save_annexure_rows("ANNEX_1", [
        {"label": "Row 1", "cy_value": 10, "py_value": 5},
        {"label": "Row 2", "cy_value": 20, "py_value": 15}
    ])
    
    codes = project_db.get_all_annexure_codes()
    assert "ANNEX_1" in codes
    
    rows = project_db.get_annexure_rows("ANNEX_1")
    assert len(rows) == 2
    assert rows[0]["label"] == "Row 1"
    assert rows[0]["cy_value"] == 10
    assert rows[1]["label"] == "Row 2"
    assert rows[1]["py_value"] == 15
    
    # test overwrite
    project_db.save_annexure_rows("ANNEX_1", [
        {"label": "Row 1 Updated", "cy_value": 100, "py_value": 50}
    ])
    rows = project_db.get_annexure_rows("ANNEX_1")
    assert len(rows) == 1
    assert rows[0]["label"] == "Row 1 Updated"
