import pytest
from core.notes_engine import Note, NotesEngine, _dl

def test_note():
    n = Note(1, "Share Capital")
    assert n.number == 1
    assert n.title == "Share Capital"
    n.lines.append(_dl("Label", 100, 50))
    assert len(n.lines) == 1

def test_dl():
    l = _dl("Label", 100, 50, indent=1, note="1")
    assert l.label == "Label"
    assert l.cy == 100
    assert l.indent == 1
    
def test_notes_engine_init():
    engine = NotesEngine(totals={}, entity_type="COMPANY")
    assert engine._etype == "COMPANY"

def test_notes_engine_sign_matches_fs_engine():
    """Debit-negative flips by -1 for Assets/non-Revenue; credit stays *1."""
    totals = {
        "CO_AS001": (-100.0, -80.0),  # Asset debit-neg -> +100/+80
        "CO_EL001": (100.0, 80.0),    # Liability credit-pos -> +100/+80
        "CO_IN001": (50.0, 40.0),     # Revenue credit-pos -> +50/+40
        "CO_EX020": (-30.0, -20.0),   # Expense debit-neg -> +30/+20
    }
    engine = NotesEngine(totals=totals, entity_type="COMPANY")
    assert engine._cy("CO_AS001") == 100.0
    assert engine._py("CO_AS001") == 80.0
    assert engine._cy("CO_EL001") == 100.0
    assert engine._cy("CO_IN001") == 50.0
    assert engine._cy("CO_EX020") == 30.0
    assert engine._py("CO_EX020") == 20.0
