import pytest
from core.entity_types import EntityType, ENTITY_LABELS, ENTITY_FS, fs_label, AOP_SUBTYPES, TRUST_SUBTYPES, IE_ENTITIES, CF_MANDATORY, SMALL_CO_ELIGIBLE, MASTER_TAGS

def test_entity_types_exist():
    assert EntityType.COMPANY == "COMPANY"
    assert EntityType.LLP == "LLP"

def test_fs_label():
    labels = fs_label(EntityType.COMPANY)
    assert labels["bs"] == "Balance Sheet"
    assert "pl" in labels

def test_constants():
    assert EntityType.COMPANY in CF_MANDATORY
    assert EntityType.COMPANY in SMALL_CO_ELIGIBLE
    assert EntityType.AOP in IE_ENTITIES
