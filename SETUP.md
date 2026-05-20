# CA Compliance Reminder — Setup Guide

A desktop application that automatically emails compliance reminders to your
CA clients on the 1st of every month (first app launch of the day).

---

## Quick Start

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | <https://www.python.org/downloads/> |
| `python3-tk` | On Ubuntu/Debian: `sudo apt install python3-tk` |

### 2. Install dependencies

```bash
cd Claudeproject
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Run the application

```bash
python main.py
```

---

## Email Provider Setup (App Password)

The app uses SMTP with **App Passwords** — you do **not** need OAuth or
developer credentials.

### Gmail
1. Enable 2-Step Verification on your Google Account.
2. Go to: **Google Account → Security → 2-Step Verification → App Passwords**.
3. Create an App Password for "Mail".
4. Use the 16-character password in the **Email Setup** tab.

### Zoho Mail
1. Go to **Zoho Mail → Settings → Security → App Passwords**.
2. Generate a password and use it in the **Email Setup** tab.

### Microsoft 365 / Outlook
1. Go to **Microsoft Account → Security → Advanced Security Options**.
2. Create an App Password.
3. Use it in the **Email Setup** tab.

---

## First-Time Workflow

1. **Email Setup tab** — Enter your SMTP credentials. Click **Test Connection**.
2. **Clients tab** — Add clients. Tick **Consent Given** (required by DPDP Act).
3. **Compliances tab** — 16 default Indian CA compliances are pre-loaded. Add/edit as needed.
4. **Clients tab → select client** — Assign compliances to each client.
5. Click **Send Now** to dispatch immediately, or let the app auto-send on the 1st.

---

## Auto-Send Behaviour

| Condition | Result |
|---|---|
| Today == 1st of month AND no email sent yet today | Emails sent automatically on launch |
| Already sent today | Skipped (no duplicates) |
| Any other day | No automatic send |
| Manual "Send Now" button | Sends immediately regardless of date |

---

## Data Privacy — DPDP Act 2023

- All PII (name, email, phone, PAN, GSTIN) is **encrypted at rest** using
  Fernet AES-128 encryption.
- The encryption key is stored in the **OS keychain** (Windows Credential Manager /
  macOS Keychain / Linux SecretService). If unavailable, a restricted key file
  `~/.ca_compliance_reminder/.enc_key` is used (chmod 600).
- Client data is used **only** to send compliance reminders.
- Use **"Erase" (hard delete)** to permanently remove all data for a client
  (satisfies DPDP right-to-erasure obligations).
- Only clients with **Consent Given** checked receive emails.

---

## Building a Desktop Executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/CA_Compliance_Reminder/CA_Compliance_Reminder` (Linux/macOS) or
`dist/CA_Compliance_Reminder/CA_Compliance_Reminder.exe` (Windows).

Distribute the entire `dist/CA_Compliance_Reminder/` folder.

---

## Auto-Launch on System Start (optional)

### Windows
Add a shortcut to `CA_Compliance_Reminder.exe` in:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

### macOS
System Settings → General → Login Items → add the `.app`.

### Linux (systemd user service)
```ini
# ~/.config/systemd/user/ca-reminder.service
[Unit]
Description=CA Compliance Reminder

[Service]
ExecStart=/path/to/venv/bin/python /path/to/main.py
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```
```bash
systemctl --user enable ca-reminder
systemctl --user start ca-reminder
```

---

## App Data Location

| Platform | Path |
|---|---|
| Linux / macOS | `~/.ca_compliance_reminder/` |
| Windows | `C:\Users\<you>\.ca_compliance_reminder\` |

Contents:
- `compliance_data.db` — SQLite database (PII encrypted inside)
- `app.log` — application log
- `.enc_key` — encryption key file (only if OS keychain unavailable)

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: tkinter` | `sudo apt install python3-tk` (Ubuntu/Debian) |
| SMTP authentication failed | Use App Password, not your login password |
| Gmail "Less secure app" error | App Passwords require 2FA — enable 2FA first |
| No emails sent | Check consent checkbox is ticked for the client |
| Encryption error on launch | Delete `~/.ca_compliance_reminder/.enc_key` — a new key is generated (old data unreadable) |
