# CLAUDE.md — AI Assistant Guide for CA Compliance Reminder

## Project Identity

| Field | Value |
|---|---|
| **Application** | CA Compliance Reminder |
| **Version** | 1.0.0 |
| **Type** | Desktop application (Tkinter GUI) |
| **Language** | Python 3.10+ |
| **Repository** | `rajacacs/Claudeproject` |
| **Branch** | `claude/add-claude-documentation-YoAJL` |
| **Owner** | Chartered Accountant (CA) & Company Secretary (CS) — also a teacher/faculty in finance, accounting, and audit |

---

## What This App Does

A **local-first desktop application** that automatically emails personalised monthly compliance reminders to CA/CS office clients. It runs on the client's Windows/macOS/Linux machine — no cloud, no server, no third-party data transfer.

**Core workflow:**
1. CA adds clients and assigns compliance obligations (GST, TDS, Income Tax, ROC, PF/ESI, etc.)
2. On the **1st of every month** (configurable), the app auto-sends HTML email reminders listing each client's relevant due dates for that month
3. All PII is **encrypted at rest** (Fernet AES-128) — compliant with India's DPDP Act, 2023

---

## Repository Structure (Actual)

```
Claudeproject/
├── main.py                          # Entry point: bootstraps app dir, encryption, DB, GUI
├── requirements.txt                 # cryptography, keyring, openpyxl
├── build.spec                       # PyInstaller config for standalone .exe
├── .gitignore
│
├── ca_reminder/                     # Main package
│   ├── __init__.py
│   ├── config.py                    # All constants, paths, SMTP presets, compliance categories
│   │
│   ├── core/                        # Business logic (no GUI dependency)
│   │   ├── scheduler.py             # Monthly auto-send logic + manual "Send Now" flow
│   │   ├── mailer.py                # SMTP email composition (HTML + plain text) and dispatch
│   │   └── importer.py              # CSV/XLSX import/export for clients & compliances
│   │
│   ├── data/                        # Persistence layer
│   │   ├── encryption.py            # Fernet key management (OS keychain → file fallback)
│   │   └── database.py              # SQLite DDL, CRUD for all 6 tables, field-level encryption
│   │
│   ├── gui/                         # Tkinter UI
│   │   ├── theme.py                 # Apple-inspired design tokens + widget factories
│   │   ├── main_window.py           # Root window: dashboard, tabs, scheduler thread, backup/restore
│   │   ├── client_form.py           # Clients tab: CRUD, compliance assignment, import/export
│   │   ├── compliance_form.py       # Compliances tab: CRUD, toggle active/inactive
│   │   └── settings_form.py         # Email Setup tab: SMTP config with provider presets
│   │
│   └── templates/
│       └── reminder_email.html      # Professional HTML email template with {placeholders}
│
├── README.md                        # User-facing project overview
├── SETUP.md                         # Detailed setup & email provider configuration
├── USER_GUIDE.md                    # Comprehensive user manual (476 lines)
└── CLAUDE.md                        # This file — AI assistant context
```

---

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Runtime | Python 3.10+ | Uses `match` syntax is NOT used; compatible 3.10+ features |
| GUI | `tkinter` + `ttk` | Ships with Python — no extra install |
| Database | `sqlite3` | Single file: `~/.ca_compliance_reminder/compliance_data.db` |
| Encryption | `cryptography` (Fernet) | AES-128-CBC + HMAC-SHA256 |
| Key storage | `keyring` | Windows Credential Manager / macOS Keychain / Linux SecretService |
| Excel I/O | `openpyxl` | CSV/XLSX import and template generation |
| Email | `smtplib` | STARTTLS / SSL / plain — with MIME multipart (HTML + text) |
| Packaging | PyInstaller | `build.spec` produces standalone folder |

**No external API calls.** No LLM integration. No web framework. Pure local desktop app.

---

## Database Schema (6 tables)

| Table | Purpose | Encrypted Fields |
|---|---|---|
| `settings` | Key-value app config | — |
| `email_accounts` | SMTP credentials | `email_address`, `username`, `password` |
| `clients` | Client PII | `name`, `email`, `phone`, `pan`, `gstin` |
| `compliances` | Compliance type definitions (16 pre-seeded) | — |
| `client_compliances` | Many-to-many: client ↔ compliance assignment | — |
| `send_logs` | Audit trail of every email dispatch | `recipient_email` |

**DB location:** `~/.ca_compliance_reminder/compliance_data.db`

---

## Key Design Decisions

### Encryption Architecture
- **Application-level field encryption** — individual PII columns are encrypted before write, decrypted after read
- Key stored in OS keychain via `keyring`; falls back to `~/.ca_compliance_reminder/.enc_key` (chmod 600)
- `EncryptionManager.encrypt()` / `.decrypt()` wrap every PII access in `Database`

### Scheduling Model
- **No background daemon** — the app checks on launch whether today is `REMINDER_SEND_DAY` (default: 1)
- Uses `already_sent_today()` to prevent duplicate sends on re-launch
- "Send Now" button bypasses both date and duplicate guards (`force=True`)
- Scheduler runs in a background `threading.Thread`; communicates with GUI via `queue.Queue`

### Email Providers
- Pre-configured presets in `config.py → EMAIL_PROVIDERS`: Gmail, Zoho India, Zoho Global, Microsoft 365, Custom SMTP
- Each preset includes SMTP host, port, encryption mode, and detailed App Password instructions
- Supports STARTTLS (587), SSL (465), and plain (25)

### GUI Architecture
- Single `MainWindow` class manages root window and 5 tabs (Dashboard, Clients, Compliances, Email Setup, Activity Log)
- `theme.py` provides Apple-inspired design tokens and factory functions (`btn()`, `label()`, `card()`, `entry()`, `divider()`)
- All tab forms are self-contained classes (`ClientsTab`, `CompliancesTab`, `SettingsForm`)

### Import/Export
- CSV and XLSX supported for both clients and compliances
- Template generators create downloadable sample files with column notes
- Fuzzy key normalisation (`_normalise_keys`) handles header variations
- PAN and GSTIN are auto-uppercased on import

---

## Domain Conventions

### Regulatory Context
- **DPDP Act 2023** — consent checkbox required before sending; hard-delete (right to erasure) supported
- **Indian CA compliance calendar** — GST (GSTR-1, 3B, 9), TDS/TCS, Income Tax (Advance Tax Q1–Q4, ITR), ROC/MCA (MGT-7, AOC-4), PF/ESI, Professional Tax

### Date & Number Formatting
- Display dates: `DD-MM-YYYY` (Indian standard) where shown
- Internal/storage: ISO 8601 (`YYYY-MM-DD`, `YYYY-MM`)
- Financial year: April–March

### Compliance Frequency Logic (`_filter_for_month`)
| Frequency | Included in month |
|---|---|
| Monthly | Every month |
| Quarterly | Mar, Jun, Sep, Dec (FY quarter-end months) |
| Half-Yearly | Mar, Sep |
| Annual | Only the month matching `due_month` |
| Event-Based | Every month (always included) |

---

## Code Conventions

### Style
- **PEP 8** with 100-char line limit
- Type hints on all function signatures
- Google-style docstrings
- `pathlib.Path` over `os.path`
- Logging via `logging.getLogger(__name__)`

### Naming Patterns
- Private methods: `_method_name()`
- Internal helpers: `_helper_name()` at module level
- Constants: `UPPER_SNAKE_CASE` in `config.py`
- GUI callback methods: `_on_event()`, `_build_section()`

### Error Handling
- SMTP errors: caught per-recipient, logged, returned as `(bool, str)` tuples
- Encryption errors: logged, return `"[DECRYPTION ERROR]"` sentinel
- Startup failures: `_fatal()` shows messagebox + `sys.exit(1)`

---

## AI Assistant Rules

### DO
- Read a file before editing it
- Prefer `Edit` over full file rewrites
- Create new commits (don't amend)
- Run on the designated feature branch
- Test SMTP-related changes with `test_smtp_connection()` before live sends
- Validate import data against `CLIENT_REQUIRED` / `COMPLIANCE_REQUIRED` sets

### DON'T
- Hardcode credentials or API keys
- Push to `main` / `master` without permission
- Create PRs unless explicitly asked
- Use `--force` push or `--no-verify` hooks
- Add speculative features not requested
- Break the encryption contract (every PII field must go through `EncryptionManager`)

### Testing Considerations
- No test suite exists yet — consider `pytest` if adding one
- Mock `smtplib.SMTP` for mailer tests
- Use `EncryptionManager` with a known test key for database tests
- All financial/date logic in `_filter_for_month()` and `scheduler.py` should have edge-case coverage

---

## Environment Setup

```bash
# Clone & install
git clone <repo-url>
cd Claudeproject
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt

# Run
python main.py

# Build standalone
pip install pyinstaller
pyinstaller build.spec
# Output: dist/CA_Compliance_Reminder/CA_Compliance_Reminder.exe
```

### App Data Location
| Platform | Path |
|---|---|
| Windows | `C:\Users\<you>\.ca_compliance_reminder\` |
| macOS/Linux | `~/.ca_compliance_reminder/` |

Contents: `compliance_data.db`, `app.log`, `.enc_key` (fallback only)

---

## Configuration Quick Reference

| Config | Location | Default |
|---|---|---|
| Auto-send day | `config.py → REMINDER_SEND_DAY` | `1` (1st of month) |
| DB path | `config.py → DB_PATH` | `~/.ca_compliance_reminder/compliance_data.db` |
| Keyring service | `config.py → KEYRING_SERVICE` | `ca_compliance_reminder_v1` |
| Compliance categories | `config.py → COMPLIANCE_CATEGORIES` | 8 categories |
| SMTP presets | `config.py → EMAIL_PROVIDERS` | Gmail, Zoho IN, Zoho Global, MS365, Custom |

---

*Last updated: 2026-04-26*
*Maintained by: CA/CS developer — rajacacs*
