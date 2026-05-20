# CA Compliance Reminder

A desktop application for Chartered Accountants to automatically email
personalised compliance reminders to each client on the 1st of every month.

---

## Features

- **Auto-send on launch** — emails go out on the 1st of every month, the first
  time you open the app that day. No scheduler or background service required.
- **Per-client compliance assignments** — each client gets only the compliances
  assigned to them, with due dates.
- **16 pre-loaded Indian CA compliances** — GST, TDS/TCS, Income Tax, ROC/MCA,
  PF/ESI, and more. Add custom ones any time.
- **Bulk import** — load clients and compliances from CSV or XLSX files.
  Download templates with one click.
- **Encrypted at rest** — all PII (name, email, phone, PAN, GSTIN) is encrypted
  using Fernet AES-128 before being written to the local SQLite database.
- **DPDP Act 2023 compliant** — consent checkbox, hard-delete (right to erasure),
  purpose limitation.
- **Supports Gmail, Zoho Mail, Microsoft 365, custom SMTP** via App Passwords.
  Your real login password is never stored.
- **Activity log** — every send/fail event is recorded with a timestamp.

---

## Quick Start

### Prerequisites

- Python 3.10 or later  →  <https://www.python.org/downloads/>
- On Windows: tick **"Add Python to PATH"** during installation

### Install

```cmd
:: Clone or extract the project, then:
cd Claudeproject

:: Create a virtual environment
python -m venv venv

:: Activate it  (Windows)
venv\Scripts\activate

:: Install the three required libraries
pip install -r requirements.txt
```

### Run

```cmd
python main.py
```

---

## First-Time Setup (5 minutes)

1. **Email Setup tab** → click your provider (Gmail / Zoho / Microsoft 365) →
   paste your App Password → **Test Connection** → **Save Account**
2. **Clients tab** → **+ Add Client** → fill in Name, Email, tick Consent
3. **Compliances tab** → 16 defaults are ready; add custom ones if needed
4. **Clients tab** → select each client → **+ Add Compliance** to assign
5. **Dashboard** → click **Send Now** to do a test send

Auto-send happens automatically on the 1st of each month when the app opens.

---

## Libraries to Install

```
cryptography>=41.0.0   — AES-128 encryption for stored personal data
keyring>=24.0.0        — stores the encryption key in Windows Credential Manager
openpyxl>=3.1.0        — read/write .xlsx files (remove if you only need CSV)
```

All other modules (`tkinter`, `sqlite3`, `smtplib`, `csv`, etc.) ship with Python.

---

## Security & Privacy

| Feature | Implementation |
|---|---|
| Encryption at rest | Fernet AES-128-CBC + HMAC-SHA256 (`cryptography` library) |
| Key storage | Windows Credential Manager / macOS Keychain / Linux SecretService (file fallback) |
| Data location | 100% local — `~/.ca_compliance_reminder/compliance_data.db` |
| Email transit | SMTP STARTTLS (TLS in transit) |
| Credentials | App Passwords only; your real password is never stored |
| DPDP Act | Consent checkbox · AES encryption · hard-delete (right to erasure) |

---

## App Data

| Platform | Path |
|---|---|
| Windows | `C:\Users\<you>\.ca_compliance_reminder\` |
| macOS / Linux | `~/.ca_compliance_reminder/` |

- `compliance_data.db` — SQLite database (PII encrypted inside)
- `app.log` — application log

---

## Building a Standalone .exe (Windows)

```cmd
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist\CA_Compliance_Reminder\CA_Compliance_Reminder.exe`

Copy the entire `dist\CA_Compliance_Reminder\` folder to any Windows PC —
no Python required.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Only 3 tabs show on startup | Update to latest code — startup crash in Email Setup was fixed |
| `ModuleNotFoundError: tkinter` | `sudo apt install python3-tk` (Ubuntu/Debian) |
| SMTP Authentication Failed | Use an App Password, not your account password |
| Gmail "Username/Password not accepted" | Enable 2-Step Verification before generating App Password |
| Client not receiving emails | Ensure **Consent Given** is ticked for that client |
| App doesn't auto-send on 1st | Open the app on the 1st; it does not run in the background |
| Want a different auto-send day | Edit `REMINDER_SEND_DAY = 1` in `ca_reminder/config.py` |

---

*CA Compliance Reminder v1.0 · Data encrypted · DPDP Act 2023 compliant*
