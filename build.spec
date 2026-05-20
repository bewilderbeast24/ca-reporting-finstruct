# PyInstaller spec — builds a single-folder desktop application.
# Run: pyinstaller build.spec
#
# Output: dist/CA_Compliance_Reminder/
#   Windows: run CA_Compliance_Reminder.exe
#   macOS:   open CA_Compliance_Reminder.app  (add --windowed to Analysis)
#   Linux:   ./CA_Compliance_Reminder

import sys
from pathlib import Path

ROOT = Path(SPECPATH)   # directory containing this .spec file

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include the HTML email template
        (str(ROOT / "ca_reminder" / "templates"), "ca_reminder/templates"),
        # Include optional icon asset (create assets/icon.png if desired)
        # (str(ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        # keyring backends — include all so the correct one is picked at runtime
        "keyring.backends.Windows",
        "keyring.backends.macOS",
        "keyring.backends.SecretService",
        "keyring.backends.fail",
        "keyring.backends.kwallet",
        # cryptography internals
        "cryptography.hazmat.primitives.ciphers.algorithms",
        "cryptography.hazmat.primitives.ciphers.modes",
        "cryptography.hazmat.backends.openssl",
        # tkinter (sometimes missed on Windows)
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.simpledialog",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "numpy", "pandas"],   # not used — keep binary small
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CA_Compliance_Reminder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # set True to show a console window for debugging
    icon=None,            # point to assets/icon.ico on Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CA_Compliance_Reminder",
)

# ── macOS .app bundle (uncomment to build on macOS) ───────────────────────────
# app = BUNDLE(
#     coll,
#     name="CA Compliance Reminder.app",
#     icon=None,
#     bundle_identifier="com.caoffice.compliance_reminder",
#     info_plist={
#         "NSHighResolutionCapable": True,
#         "CFBundleShortVersionString": "1.0.0",
#     },
# )
