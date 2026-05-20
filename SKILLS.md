# SKILLS.md — Contributor & Modification Guide

This document describes the skills, patterns, and recipes needed to work on the **CA Compliance Reminder** codebase. Use it as a reference when making modifications.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Common Modification Patterns](#common-modification-patterns)
3. [Adding a New Compliance Type](#adding-a-new-compliance-type)
4. [Adding a New Email Provider Preset](#adding-a-new-email-provider-preset)
5. [Adding a New Database Table/Column](#adding-a-new-database-tablecolumn)
6. [Adding a New GUI Tab](#adding-a-new-gui-tab)
7. [Working with Encryption](#working-with-encryption)
8. [Working with the Scheduler](#working-with-the-scheduler)
9. [Import/Export Modifications](#importexport-modifications)
10. [Email Template Customisation](#email-template-customisation)
11. [Theming & UI Adjustments](#theming--ui-adjustments)
12. [Building & Distributing](#building--distributing)
13. [Debugging Recipes](#debugging-recipes)
14. [Testing Strategies](#testing-strategies)

---

## Architecture Overview

```
main.py
  └─ EncryptionManager()          ← loads/creates Fernet key
  └─ Database(enc)                ← SQLite + field-level encryption
  └─ MainWindow(root, db, enc)    ← Tkinter GUI + scheduler thread
       ├─ Dashboard               ← stat cards, recent logs, send button
       ├─ ClientsTab(db)          ← client CRUD + compliance assignments
       ├─ CompliancesTab(db)      ← compliance CRUD
       ├─ SettingsForm(db)        ← SMTP config with provider presets
       └─ Activity Log            ← Treeview of send_logs
```

**Data flow for sending reminders:**
```
Manual Send / Auto-scheduler
  → scheduler.check_and_send(db)
    → db.get_active_email_account()
    → db.get_clients_for_reminder(year, month)
      → _filter_for_month() — selects relevant compliances
    → mailer.send_reminder_email(account, client, compliances)
      → _load_template() + _build_compliance_table()
      → _smtp_connect() → sendmail()
    → db.log_send() — audit trail
```

---

## Common Modification Patterns

### Pattern 1: Config Change
**Where:** `ca_reminder/config.py`
**Example:** Change auto-send day, add a compliance category, modify SMTP defaults.
```python
# Change auto-send from 1st to 5th
REMINDER_SEND_DAY = 5

# Add a new compliance category
COMPLIANCE_CATEGORIES = [
    ...,
    "LLP / Partnership",  # New category
]
```

### Pattern 2: Database Migration
**Where:** `ca_reminder/data/database.py → Database._migrate()`
**When:** Adding a column to an existing table for deployed users.
```python
def _migrate(self) -> None:
    conn = self._conn_()
    
    # Existing migration
    cols = {row[1] for row in conn.execute("PRAGMA table_info(email_accounts)").fetchall()}
    if "encryption" not in cols:
        conn.execute("ALTER TABLE email_accounts ADD COLUMN encryption TEXT NOT NULL DEFAULT 'STARTTLS'")
        conn.commit()
    
    # NEW migration — add your column here
    client_cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)").fetchall()}
    if "new_field" not in client_cols:
        conn.execute("ALTER TABLE clients ADD COLUMN new_field TEXT NOT NULL DEFAULT ''")
        conn.commit()
        logger.info("Migration: added 'new_field' column to clients")
```

### Pattern 3: Encrypting a New PII Field
**Where:** `database.py → _encrypt_client()` and `_decrypt_client()`
```python
def _encrypt_client(self, d: dict) -> dict:
    return {
        ...,
        "new_pii_field": self.enc.encrypt(d.get("new_pii_field", "") or ""),
    }

def _decrypt_client(self, d: dict) -> dict:
    for field in ("name", "email", "phone", "pan", "gstin", "new_pii_field"):
        d[field] = self.enc.decrypt(d.get(field) or "")
    return d
```

---

## Adding a New Compliance Type

**Skill level:** Easy

1. **Add to seed data** in `database.py → _DEFAULT_COMPLIANCES`:
   ```python
   ("New Compliance Name", "Description", "Category", "Frequency", due_day, due_month, advance_days),
   ```
   > Note: Seeds only run once on first DB creation. For existing installs, add via the GUI.

2. **If adding a new category**, update `config.py → COMPLIANCE_CATEGORIES` and `importer.py → VALID_CATEGORIES`.

3. **If adding a new frequency**, update `config.py → COMPLIANCE_FREQUENCIES`, `importer.py → VALID_FREQUENCIES`, and the `_filter_for_month()` function in `database.py`.

---

## Adding a New Email Provider Preset

**Skill level:** Easy

**Where:** `ca_reminder/config.py → EMAIL_PROVIDERS`

```python
EMAIL_PROVIDERS["new_provider"] = {
    "name": "Display Name",
    "smtp_host": "smtp.provider.com",
    "smtp_port": 587,
    "encryption": "STARTTLS",
    "help": (
        "Step-by-step instructions for generating an App Password...\n"
        "Include the SMTP host, port, and encryption details."
    ),
}
```

The `SettingsForm` GUI automatically picks up new entries from this dictionary — no GUI code changes needed.

---

## Adding a New Database Table/Column

**Skill level:** Medium

### New Table
1. Add `CREATE TABLE IF NOT EXISTS` to `_SCHEMA` in `database.py`
2. Add CRUD methods to the `Database` class
3. If the table stores PII, add `_encrypt_*()` / `_decrypt_*()` methods

### New Column on Existing Table
1. Add the column to `_SCHEMA` (for fresh installs)
2. Add a migration in `_migrate()` (for existing installs) — see Pattern 2 above
3. Update all INSERT/UPDATE/SELECT queries that touch the table
4. Update `_encrypt_*()` / `_decrypt_*()` if PII

---

## Adding a New GUI Tab

**Skill level:** Medium–Hard

1. **Create a new form class** in `ca_reminder/gui/`:
   ```python
   # ca_reminder/gui/new_tab.py
   import tkinter as tk
   from ca_reminder.gui import theme as T
   from ca_reminder.data.database import Database

   class NewTab(tk.Frame):
       def __init__(self, parent, db: Database) -> None:
           super().__init__(parent, bg=T.BG)
           self.db = db
           self._build()

       def _build(self) -> None:
           # Header
           hdr = tk.Frame(self, bg=T.BG, padx=T.PAD_L, pady=T.PAD)
           hdr.pack(fill="x")
           T.label(hdr, "New Feature", style="heading").pack(anchor="w")
           T.divider(self).pack(fill="x", padx=T.PAD_L)
           # ... build the rest

       def refresh(self) -> None:
           """Called when tab is selected or data changes."""
           pass
   ```

2. **Register in `main_window.py`**:
   ```python
   from ca_reminder.gui.new_tab import NewTab
   
   # In _build():
   self._new_tab = NewTab(self._nb, self.db)
   self._nb.add(self._new_tab, text="  New Tab  ")
   ```

3. **Add refresh trigger** in `_on_tab_change()` if needed.

---

## Working with Encryption

### Key Principles
- **Never store raw PII** in SQLite — always encrypt with `self.enc.encrypt(value)` before write
- **Always decrypt after read** — `self.enc.decrypt(token)` returns the original string
- Empty strings pass through unchanged (no encryption/decryption)
- Failed decryption returns `"[DECRYPTION ERROR]"` — check logs for root cause

### EncryptionManager API
```python
enc = EncryptionManager()         # Loads or creates key automatically
token = enc.encrypt("plain text") # Returns URL-safe Fernet token string
text = enc.decrypt(token)         # Returns original plain text
```

### Gotchas
- If the encryption key is lost/changed, all existing encrypted data becomes unreadable
- The `hard_delete_client()` method permanently erases all traces (DPDP compliance)
- `send_logs.recipient_email` is also encrypted — don't forget when querying logs

---

## Working with the Scheduler

### Auto-Send Flow
```python
# In MainWindow._start_scheduler():
threading.Thread(target=self._run_send, kwargs={"force": False}, daemon=True).start()
self.root.after(200, self._poll_q)  # Start polling the queue

# The thread runs:
check_and_send(db, progress=callback, force=False)
# → Checks: is today == REMINDER_SEND_DAY?
# → Checks: already_sent_today()?
# → If both pass: sends to all eligible clients
```

### Adding Custom Schedule Logic
Modify `scheduler.py → check_and_send()`. The `force` parameter bypasses all guards.

### Thread Safety
- `Database` uses `check_same_thread=False` on the SQLite connection
- GUI updates go through `queue.Queue` — never touch Tkinter from a background thread
- The polling loop (`_poll_q`) runs every 150ms via `root.after()`

---

## Import/Export Modifications

### Adding a New Import Column
1. Add to `CLIENT_COLUMNS` or `COMPLIANCE_COLUMNS` in `importer.py`
2. Add sample data to `CLIENT_SAMPLE_ROWS` or `COMPLIANCE_SAMPLE_ROWS`
3. Update the parsing logic in `read_clients()` or `read_compliances()`
4. Update the XLSX template notes in `save_client_template_xlsx()`

### Validation
- Required fields: `CLIENT_REQUIRED = {"name", "email"}`, `COMPLIANCE_REQUIRED = {"name", "category", "frequency"}`
- Category/frequency fuzzy matching: `_best_match()` handles case-insensitive lookup
- Key normalisation: underscores, hyphens, spaces are interchangeable in headers

---

## Email Template Customisation

### Template Location
- **Primary:** `ca_reminder/templates/reminder_email.html`
- **Fallback:** `_BUILTIN_TEMPLATE` in `mailer.py` (used if file not found)

### Available Placeholders
| Placeholder | Source |
|---|---|
| `{client_name}` | Decrypted client name |
| `{month_name}` | e.g., "January" |
| `{year}` | e.g., 2026 |
| `{compliance_table}` | Generated HTML table from `_build_compliance_table()` |

### Adding New Placeholders
1. Add the placeholder to the HTML template
2. Pass the value in `mailer.py → send_reminder_email()` → `template.format(...)` call
3. Also update `_plain_text()` for the text/plain alternative

---

## Theming & UI Adjustments

### Design System (`theme.py`)
All UI components reference `theme.py` constants — change once, applies everywhere:

| Token | Current Value | Purpose |
|---|---|---|
| `BG` | `#FFFFFF` | Page background |
| `ACCENT` | `#0071E3` | Apple blue — primary actions |
| `TEXT` | `#1D1D1F` | Primary text |
| `SUCCESS` | `#34C759` | Green — sent status |
| `ERROR` | `#FF3B30` | Red — failed status |
| `WARNING` | `#FF9500` | Orange — pending status |

### Widget Factories
```python
T.btn(parent, "Label", command, style="primary|secondary|danger|ghost")
T.label(parent, "Text", style="title|heading|subhead|body|caption|label")
T.card(parent)                    # White card with 1px border
T.divider(parent)                 # Horizontal 1px line
T.entry(parent, width=32)         # Styled text input
T.section_header(parent, "Title") # Label + divider combo
```

---

## Building & Distributing

### Development Run
```bash
python main.py
```

### Standalone Build
```bash
pip install pyinstaller
pyinstaller build.spec
# Output: dist/CA_Compliance_Reminder/CA_Compliance_Reminder.exe
```

### Build Customisation (`build.spec`)
- Add data files: modify `datas` list in `Analysis()`
- Add hidden imports: modify `hiddenimports` list
- Add icon: set `icon=` in `EXE()` to an `.ico` file path
- Enable console for debugging: set `console=True` in `EXE()`

### Excluding Large Libraries
The build spec already excludes `pytest`, `numpy`, `pandas` to keep binary small.

---

## Debugging Recipes

### Log File
```
~/.ca_compliance_reminder/app.log
```
The app logs to both file and console (`sys.stdout`). Log level: `INFO`.

### Common Issues

| Issue | Diagnosis | Fix |
|---|---|---|
| SMTP auth failure | Check `app.log` for `SMTPAuthenticationError` | Regenerate App Password |
| Decryption errors | Key mismatch — `[DECRYPTION ERROR]` in UI | Delete `.enc_key`, lose old data |
| GUI freeze | Long-running operation on main thread | Ensure background thread + queue pattern |
| Missing tkinter | `ModuleNotFoundError` | `sudo apt install python3-tk` (Linux) |
| Tab not showing | Exception during tab `__init__` | Check `app.log` for traceback |

### Inspecting the Database
```python
import sqlite3
conn = sqlite3.connect(str(Path.home() / ".ca_compliance_reminder" / "compliance_data.db"))
conn.row_factory = sqlite3.Row
# Note: PII fields will show encrypted Fernet tokens
for row in conn.execute("SELECT id, client_code, consent_given FROM clients"):
    print(dict(row))
```

---

## Testing Strategies

### Unit Testing (recommended additions)

**Scheduler logic:**
```python
def test_filter_monthly():
    comps = [{"frequency": "Monthly", "due_day": 20}]
    assert _filter_for_month(comps, 5) == comps  # any month

def test_filter_quarterly():
    comps = [{"frequency": "Quarterly", "due_day": 31}]
    assert _filter_for_month(comps, 6) == comps  # quarter-end
    assert _filter_for_month(comps, 7) == []      # not quarter-end
```

**Encryption round-trip:**
```python
def test_encrypt_decrypt():
    enc = EncryptionManager()
    assert enc.decrypt(enc.encrypt("test")) == "test"
    assert enc.encrypt("") == ""
    assert enc.decrypt("") == ""
```

**Import validation:**
```python
def test_truthy():
    assert _truthy("yes") is True
    assert _truthy("no") is False
    assert _truthy("✓") is True
```

### Integration Testing
- Test the full send flow with a mock SMTP server (`smtplib.SMTP` mock)
- Test database migrations by creating a DB without the `encryption` column, then running `_migrate()`
- Test CSV/XLSX import with edge cases: missing columns, extra columns, blank rows

---

*Last updated: 2026-04-26*
