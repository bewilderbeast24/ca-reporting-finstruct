"""
Apple-inspired design tokens for CA Compliance Reminder.

All UI files import from here — change once, applies everywhere.
"""

import tkinter as tk
from tkinter import ttk

# ── Colour palette ────────────────────────────────────────────────────────────
BG           = "#FFFFFF"   # page background
BG_ALT       = "#F5F5F7"   # alternate row / sidebar
BG_HOVER     = "#F0F0F2"   # hover state
BG_SELECTED  = "#E8F0FE"   # selected row
TEXT         = "#1D1D1F"   # primary text
TEXT_SEC     = "#6E6E73"   # secondary / placeholder
TEXT_LIGHT   = "#AEAEB2"   # disabled / caption
ACCENT       = "#0071E3"   # Apple blue – primary action
ACCENT_DARK  = "#005BBB"   # hover on primary buttons
BORDER       = "#D2D2D7"   # input borders, dividers
BORDER_FOCUS = "#0071E3"   # focused input ring
SUCCESS      = "#34C759"   # success / sent
ERROR        = "#FF3B30"   # error / failed
WARNING      = "#FF9500"   # warning / pending
DIVIDER      = "#E5E5EA"   # horizontal rule

# ── Typography ────────────────────────────────────────────────────────────────
# Tkinter uses the first matching family on each platform
_FONT_STACK = "Helvetica Neue"   # macOS; falls back to Helvetica on Linux/Win

def font(size: int = 13, weight: str = "normal") -> tuple:
    return (_FONT_STACK, size, weight)

F_TITLE    = font(18, "bold")
F_HEADING  = font(15, "bold")
F_SUBHEAD  = font(13, "bold")
F_BODY     = font(13)
F_CAPTION  = font(11)
F_LABEL    = font(12)

# ── Spacing ───────────────────────────────────────────────────────────────────
PAD   = 16   # standard padding
PAD_S = 8    # small padding
PAD_L = 24   # large padding

# ── Widget factories ──────────────────────────────────────────────────────────

def configure_ttk_style() -> None:
    """Apply the theme globally to all ttk widgets."""
    s = ttk.Style()
    for pref in ("clam", "alt", "default"):
        if pref in s.theme_names():
            s.theme_use(pref)
            break

    # Notebook (tabs)
    s.configure("TNotebook",
                background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    s.configure("TNotebook.Tab",
                background=BG_ALT, foreground=TEXT_SEC,
                font=F_BODY, padding=[18, 8], borderwidth=0)
    s.map("TNotebook.Tab",
          background=[("selected", BG), ("active", BG_HOVER)],
          foreground=[("selected", TEXT), ("active", TEXT)])

    # Treeview
    s.configure("Treeview",
                background=BG, foreground=TEXT,
                fieldbackground=BG, rowheight=28,
                font=F_BODY, borderwidth=0, relief="flat")
    s.configure("Treeview.Heading",
                background=BG_ALT, foreground=TEXT_SEC,
                font=font(11, "bold"), relief="flat", borderwidth=0)
    s.map("Treeview",
          background=[("selected", BG_SELECTED)],
          foreground=[("selected", TEXT)])

    # Scrollbar — minimal
    s.configure("TScrollbar",
                background=BG_ALT, troughcolor=BG,
                borderwidth=0, arrowsize=12)

    # Buttons
    s.configure("TButton",
                font=F_BODY, padding=[10, 5], relief="flat",
                borderwidth=0)

    # Combobox
    s.configure("TCombobox",
                background=BG, foreground=TEXT,
                fieldbackground=BG, font=F_BODY)

    # Checkbutton
    s.configure("TCheckbutton",
                background=BG, foreground=TEXT, font=F_BODY)

    # Separator
    s.configure("TSeparator", background=DIVIDER)

    # Progressbar
    s.configure("TProgressbar",
                background=ACCENT, troughcolor=BG_ALT, borderwidth=0)


# ── Re-usable widget helpers ─────────────────────────────────────────────────

def btn(parent, text: str, command, style: str = "primary",
        icon: str = "", **kw) -> tk.Button:
    """
    Flat button in three flavours:
      primary   — solid accent fill, white text
      secondary — white fill, accent border/text
      danger    — white fill, red text
      ghost     — no border, secondary text (toolbar icon-ish)
    """
    label = f"{icon}  {text}" if icon else text
    cfg = {
        "primary":   dict(bg=ACCENT,   fg="white",  activebackground=ACCENT_DARK,
                          activeforeground="white",  relief="flat",  bd=0),
        "secondary": dict(bg=BG,       fg=ACCENT,   activebackground=BG_ALT,
                          activeforeground=ACCENT,   relief="solid", bd=1,
                          highlightbackground=ACCENT, highlightthickness=1),
        "danger":    dict(bg=BG,       fg=ERROR,    activebackground="#FFF1F0",
                          activeforeground=ERROR,    relief="solid", bd=1,
                          highlightbackground=ERROR, highlightthickness=1),
        "ghost":     dict(bg=BG,       fg=TEXT_SEC, activebackground=BG_ALT,
                          activeforeground=TEXT,     relief="flat",  bd=0),
    }.get(style, {})
    return tk.Button(
        parent, text=label, command=command,
        font=F_BODY, padx=12, pady=5,
        cursor="hand2",
        **cfg, **kw,
    )


def label(parent, text: str, style: str = "body", **kw) -> tk.Label:
    fonts = {
        "title":   F_TITLE,
        "heading": F_HEADING,
        "subhead": F_SUBHEAD,
        "body":    F_BODY,
        "caption": F_CAPTION,
        "label":   F_LABEL,
    }
    colors = {
        "title":   TEXT,
        "heading": TEXT,
        "subhead": TEXT,
        "body":    TEXT,
        "caption": TEXT_SEC,
        "label":   TEXT_SEC,
    }
    return tk.Label(
        parent, text=text,
        font=fonts.get(style, F_BODY),
        fg=colors.get(style, TEXT),
        bg=kw.pop("bg", BG),
        **kw,
    )


def divider(parent, orient: str = "horizontal") -> tk.Frame:
    if orient == "horizontal":
        return tk.Frame(parent, bg=DIVIDER, height=1)
    return tk.Frame(parent, bg=DIVIDER, width=1)


def card(parent, **kw) -> tk.Frame:
    """White card with a subtle 1-px border."""
    return tk.Frame(
        parent,
        bg=kw.pop("bg", BG),
        relief="flat", bd=0,
        highlightbackground=BORDER,
        highlightthickness=1,
        **kw,
    )


def section_header(parent, text: str) -> tk.Frame:
    """Labelled section divider used inside forms."""
    f = tk.Frame(parent, bg=BG)
    tk.Label(f, text=text, font=F_LABEL, fg=TEXT_SEC, bg=BG).pack(side="left")
    tk.Frame(f, bg=DIVIDER, height=1).pack(side="left", fill="x", expand=True,
                                           padx=(8, 0), pady=6)
    return f


def entry(parent, width: int = 32, show: str = "", **kw) -> tk.Entry:
    return tk.Entry(
        parent,
        font=F_BODY,
        bg=BG, fg=TEXT,
        insertbackground=TEXT,
        relief="solid", bd=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER_FOCUS,
        highlightthickness=1,
        width=width,
        show=show,
        **kw,
    )
