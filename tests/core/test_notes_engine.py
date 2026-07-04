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
