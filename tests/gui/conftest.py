import pytest
import tkinter as tk

_root = None

@pytest.fixture(scope='session')
def tk_root():
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    yield _root
    if _root:
        try:
            _root.update_idletasks()
            _root.update()
            _root.destroy()
        except Exception:
            pass
