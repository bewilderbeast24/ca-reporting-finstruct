import pytest
import tkinter as tk
from tkinter import ttk
from gui.theme import apply_theme, sidebar_btn, primary_btn, secondary_btn, label, entry, card, separator, scrolled_frame

def test_apply_theme(tk_root):
    apply_theme(tk_root)
    # Just checking it runs without exceptions
    style = ttk.Style(tk_root)
    assert style.theme_use() == "clam"

def test_widget_factories(tk_root):
    apply_theme(tk_root)
    
    btn1 = sidebar_btn(tk_root, "Sidebar")
    assert isinstance(btn1, tk.Button)
    assert btn1["text"] == "Sidebar"

    btn2 = primary_btn(tk_root, "Primary")
    assert isinstance(btn2, ttk.Button)
    assert btn2["text"] == "Primary"

    btn3 = secondary_btn(tk_root, "Secondary")
    assert isinstance(btn3, ttk.Button)
    assert btn3["style"] == "Secondary.TButton"

    lbl = label(tk_root, "Label")
    assert isinstance(lbl, ttk.Label)
    assert lbl["text"] == "Label"

    ent = entry(tk_root, width=50)
    assert isinstance(ent, ttk.Entry)
    assert ent["width"] == 50

    c = card(tk_root)
    assert isinstance(c, ttk.Frame)
    assert c["style"] == "Card.TFrame"

    sep = separator(tk_root)
    assert isinstance(sep, ttk.Separator)
    
def test_scrolled_frame(tk_root):
    outer, canvas, inner = scrolled_frame(tk_root)
    assert isinstance(outer, ttk.Frame)
    assert isinstance(canvas, tk.Canvas)
    assert isinstance(inner, ttk.Frame)
