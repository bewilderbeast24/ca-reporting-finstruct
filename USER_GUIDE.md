# CA Compliance Reminder — User Guide

**Version 1.0 · For CA / CS offices running Windows 10 / 11**

---

## Table of Contents

1. [What This Tool Does](#1-what-this-tool-does)
2. [How It Works — Step by Step](#2-how-it-works)
3. [Security Architecture](#3-security-architecture)
4. [Windows Installation](#4-windows-installation)
5. [First-Time Setup](#5-first-time-setup)
6. [Managing Clients](#6-managing-clients)
7. [Managing Compliances](#7-managing-compliances)
8. [Importing via CSV / Excel](#8-importing-via-csv--excel)
9. [Email Account Setup](#9-email-account-setup)
10. [Auto-Send & Manual Send](#10-auto-send--manual-send)
11. [Activity Log](#11-activity-log)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What This Tool Does

CA Compliance Reminder is a **desktop application** that:

- Stores your client list and their compliance obligations **locally on your PC** (no cloud, no third-party servers)
- Automatically emails each client a **personalised reminder** listing their pending compliances and due dates on the **1st of every month**, the first time you open the app that day
- Lets you import client lists and compliance schedules from **CSV or Excel files**
- Encrypts all personal data at rest, in compliance with the **Digital Personal Data Protection Act, 2023 (DPDP Act)**

---

## 2. How It Works

```
App starts
    │
    ▼
Is today the 1st of the month?
    │ No  → Show dashboard. Nothing sent.
    │ Yes ↓
Have reminders already been sent today?
    │ Yes → Show "Already sent" status. Stop.
    │ No  ↓
Is an email account configured?
    │ No  → Show warning. Open Email Setup tab.
    │ Yes ↓
For each active client with consent ticked:
    └─ Get their assigned compliances due this month
    └─ Compose HTML + plain-text email
    └─ Send via your SMTP account
    └─ Log result (sent / failed)
    │
    ▼
Show summary. Dashboard refreshes.
```

**Key behaviours:**
- Emails are sent **only once per month**, even if you open the app multiple times
- Only clients with the **"Consent Given"** checkbox ticked receive emails (DPDP requirement)
- You can click **"Send Now"** on any day to send immediately (ignores the date check)
- All send/fail events are stored in the **Activity Log**

---

## 3. Security Architecture

### 3.1 Encryption at Rest (DPDP Act Compliance)

All personally identifiable information (PII) is **encrypted before it is written to the database**:

| Field encrypted | Why |
|---|---|
| Client name | Personal data |
| Email address | Personal data |
| Phone number | Personal data |
| PAN | Sensitive financial identifier |
| GSTIN | Business identifier |
| SMTP password | Credential |
| SMTP username | Credential |

**Algorithm:** Fernet (AES-128-CBC + HMAC-SHA256) from Python's `cryptography` library — the same standard used in production security systems.

### 3.2 Encryption Key Storage

The encryption key is stored in the **Windows Credential Manager** (the same secure vault used by browsers to store passwords). If Credential Manager is unavailable, a restricted key file is used instead:

```
C:\Users\<you>\.ca_compliance_reminder\.enc_key
```

This file is created with restricted permissions and should never be shared or backed up to cloud storage.

### 3.3 Local-Only Storage

- **No data leaves your PC** except the reminder emails you choose to send.
- The SQLite database (`compliance_data.db`) lives entirely on your local drive.
- No analytics, telemetry, or cloud sync of any kind.

### 3.4 DPDP Act Compliance Features

| Requirement | How it is met |
|---|---|
| Consent before processing | "Consent Given" checkbox — only ticked clients receive emails |
| Encryption at rest | All PII fields encrypted with Fernet AES-128 |
| Right to erasure | **"Erase (DPDP)"** button permanently deletes all client data |
| Data minimisation | Only name + email are required; all other fields are optional |
| Purpose limitation | Data used only to send compliance reminders |

### 3.5 Email Security

- Emails are sent via **SMTP with STARTTLS** (encrypted in transit).
- The app uses **App Passwords** (not your main login password), so your real password is never stored.
- App Passwords can be revoked from your email provider at any time without changing your main password.

---

## 4. Windows Installation

### 4.1 Prerequisites

| Item | Download |
|---|---|
| Python 3.10 or later | https://www.python.org/downloads/ |
| Git (optional) | https://git-scm.com/download/win |

> **During Python installation:** Tick **"Add Python to PATH"** on the first screen.

### 4.2 Install the application

**Option A — Download ZIP**

1. Download the project as a ZIP file and extract it to a folder, e.g.:
   ```
   E:\CA Tools\ca-compliance-reminder\
   ```

**Option B — Git clone**

```cmd
git clone http://local_proxy@127.0.0.1:60383/git/rajacacs/Claudeproject
cd Claudeproject
```

### 4.3 Set up the Python environment

Open **Command Prompt** (not PowerShell) in the project folder:

```cmd
:: Create a virtual environment
python -m venv venv

:: Activate it
venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt
```

Expected output for `pip install`:
```
Successfully installed cryptography-xx.x.x keyring-xx.x.x openpyxl-xx.x.x ...
```

### 4.4 Run the application

```cmd
:: Make sure the venv is active (you see "(venv)" in the prompt)
venv\Scripts\activate

python main.py
```

The app window opens. On first run it creates:
```
C:\Users\<you>\.ca_compliance_reminder\
    compliance_data.db      ← encrypted database
    app.log                 ← activity log
```

---

## 5. First-Time Setup

Follow this order on first run:

```
① Email Setup tab  →  Enter SMTP credentials  →  Test Connection  →  Save
② Clients tab      →  Add clients (or Import CSV/Excel)
③ Compliances tab  →  Review/add compliances (16 pre-loaded)
④ Clients tab      →  Select each client  →  Add Compliance assignments
⑤ Dashboard        →  Click "Send Now" to test
```

---

## 6. Managing Clients

### Adding a client manually

1. Go to the **Clients** tab.
2. Click **+ Add Client**.
3. Fill in:
   - **Full Name** *(required)*
   - **Email Address** *(required)*
   - Phone, PAN, GSTIN *(optional)*
   - **Consent Given** — tick this box. Without it, the client will not receive any emails.
4. Click **Save**.

### Editing a client

Select the client in the table → click **Edit** → modify → **Save**.

### Deactivate vs Erase

| Button | Effect |
|---|---|
| **Deactivate** | Hides client from active list; data retained; reminders stop |
| **Erase (DPDP)** | Permanently deletes ALL data for this client (irreversible) |

Use **Erase** when a client requests deletion of their data under the DPDP Act.

### Assigning compliances to a client

1. Select the client in the left panel.
2. The **Compliance Assignments** panel appears on the right.
3. Click **+ Add Compliance** → select from the list → optionally set a custom due day → **Assign**.
4. To remove: select the assignment → **Remove**.

---

## 7. Managing Compliances

The app pre-loads **16 standard Indian CA compliances** on first run:

| Category | Examples |
|---|---|
| GST | GSTR-1, GSTR-3B, GSTR-9 Annual |
| TDS / TCS | TDS Payment (7th), TDS Return (Quarterly) |
| Income Tax | Advance Tax Q1–Q4, ITR Individual, ITR Audit |
| ROC / MCA | MGT-7 Annual Return, AOC-4 Financial Statements |
| PF / ESI | Monthly contribution (15th) |

### Adding a custom compliance

1. Go to **Compliances** tab → **+ Add**.
2. Fill in:
   - **Name** — e.g., "Profession Tax — Karnataka"
   - **Category** — pick from dropdown
   - **Frequency** — Monthly / Quarterly / Half-Yearly / Annual / Event-Based
   - **Due Day** — day of month (e.g., 20)
   - **Due Month** — only for Annual frequency (e.g., April)
   - **Remind N days before** — how many days before due date to mention in the 1st-of-month reminder
3. Click **Save**.

### Toggling active/inactive

Select a compliance → **Toggle Active**. Inactive compliances are not included in reminders and cannot be assigned to new clients.

---

## 8. Importing via CSV / Excel

This is the fastest way to bulk-add clients or compliances.

### Step 1 — Download the template

**Clients tab toolbar:**
- Click **Template CSV** → save `client_template.csv`
- Click **Template XLSX** → save `client_template.xlsx` (requires openpyxl)

**Compliances tab toolbar:**
- Click **Template CSV** → save `compliance_template.csv`

### Step 2 — Fill in the template

Open in Excel or any spreadsheet. The template contains:
- Column headers in **row 1**
- Sample data in rows 2–4 (delete before importing)
- Column notes at the bottom of the XLSX file

**Client template columns:**

| Column | Required | Notes |
|---|---|---|
| client_code | No | Your internal code, e.g. C001 |
| name | **Yes** | Full client name |
| email | **Yes** | Email address for reminders |
| phone | No | Mobile number |
| pan | No | PAN (auto-uppercased) |
| gstin | No | GSTIN (auto-uppercased) |
| consent_given | No | Type **yes** or **no** |
| notes | No | Any free-text notes |

**Compliance template columns:**

| Column | Required | Notes |
|---|---|---|
| name | **Yes** | Compliance name |
| description | No | Longer description |
| category | **Yes** | Must match: GST / TDS / TCS / Income Tax / ROC / MCA / PF / ESI / Professional Tax / FEMA / RBI / Custom / Others |
| frequency | **Yes** | Monthly / Quarterly / Half-Yearly / Annual / Event-Based |
| due_day | No | Day 1–31 |
| due_month | No | Month number or name (e.g. 7 or July) |
| advance_reminder_days | No | Default: 7 |

### Step 3 — Import

1. In the **Clients** (or **Compliances**) tab, click **↓ Import CSV/XLSX**.
2. Select your file.
3. A **preview dialog** shows:
   - The first 8 rows to be imported
   - Any rows that will be skipped (missing required fields)
4. Click **Import N row(s)** to confirm, or **Cancel** to abort.

---

## 9. Email Account Setup

### Gmail

1. Sign in to your Google Account → **Security** → **2-Step Verification** → enable it.
2. Still in Security → scroll to **App Passwords**.
3. Choose App: **Mail**, Device: **Windows Computer** → **Generate**.
4. Copy the 16-character password shown.
5. In the app → **Email Setup** tab:
   - Click **Gmail** provider button
   - Enter your Gmail address
   - Paste the 16-character App Password
   - Click **Test Connection** — you should see "Connection successful!"
   - Click **Save Account**

### Zoho Mail

1. Log in to Zoho Mail → **Settings** → **Security** → **App Passwords** → Generate.
2. In the app:
   - Click **Zoho Mail** provider button
   - Enter your Zoho email and the generated App Password
   - Test and Save

### Microsoft 365 / Outlook

1. Go to https://account.microsoft.com → **Security** → **Advanced security options** → **App passwords** → Create.
2. In the app:
   - Click **Microsoft 365 / Outlook** provider button
   - Enter your Microsoft email and App Password
   - Test and Save

> **Why App Passwords?** They are single-purpose passwords that can be revoked instantly without changing your main account password. Your real password is never stored in this app.

### Sender Name

In the **Sender Name** field, enter your firm name — e.g., *"Sharma & Associates, CA"*. This appears in the client's email **From:** field.

---

## 10. Auto-Send & Manual Send

### Auto-Send (1st of every month)

When you open the app on the **1st of any month** for the first time that day, reminders are sent automatically in the background. You will see:
- A thin progress bar at the top while sending
- Status text: *"Sending to Ramesh Kumar…"*
- A summary dialog when complete: *"5 compliance reminder(s) dispatched for 2025-05"*

If you open the app again the same day, it detects that reminders were already sent and does nothing.

### Manual Send — "Send Now"

Click **Send Now** (top-right of the window, or large button on Dashboard) at any time to send immediately. A confirmation dialog asks before sending.

Use this to:
- Test your setup on first configuration
- Send a mid-month reminder if needed
- Re-send after fixing a failed email account

### What the email looks like

Each client receives:
- **Subject:** `Compliance Reminder: May 2025 — Action Required`
- **From:** `Sharma & Associates, CA <yourfirm@gmail.com>`
- **Body:** A professionally formatted HTML email listing their compliances for the month with due dates, and a DPDP privacy footer

---

## 11. Activity Log

The **Activity Log** tab records every send attempt:

| Column | Meaning |
|---|---|
| Sent At | UTC timestamp of the send |
| Month | Which month's reminders these were |
| Client | Client name |
| Status | SENT (green) or FAILED (red) |
| Items | Number of compliances in the email |
| Error | Error message if failed |

The log is also visible on the Dashboard (last 10 entries).

---

## 12. Troubleshooting

| Error / symptom | Solution |
|---|---|
| `bad screen distance` error on launch | Upgrade to latest code — this bug has been fixed |
| `keyring library not available` | Normal on some systems — the app uses a key file instead; no action needed |
| SMTP Authentication Failed | Use an **App Password**, not your main account password. Re-read Section 9. |
| Gmail "Username and Password not accepted" | Ensure 2-Step Verification is enabled before generating App Password |
| Client not receiving emails | Check that **Consent Given** is ticked for that client |
| App doesn't auto-send on 1st | Make sure the app is opened on the 1st of the month. It does not run in the background when closed. |
| Database errors on startup | Delete `C:\Users\<you>\.ca_compliance_reminder\compliance_data.db` to reset (all data lost) |
| Want to change auto-send day | Edit `REMINDER_SEND_DAY = 1` in `ca_reminder/config.py` to any day 1–28 |

### Log file location

```
C:\Users\<YourName>\.ca_compliance_reminder\app.log
```

Open this in Notepad for detailed error information.

---

## Appendix — Auto-Launch on Windows Startup (Optional)

To have the app open automatically every day (so the 1st-of-month send happens without manual launch):

**Method 1 — Startup Folder**

1. Press `Win + R` → type `shell:startup` → Enter.
2. Create a shortcut to this batch file:

```bat
@echo off
cd /d "E:\CA Tools\ca-compliance-reminder"
call venv\Scripts\activate
pythonw main.py
```

Save as `start_ca_reminder.bat` in the Startup folder.
`pythonw` (not `python`) runs the app without a console window.

**Method 2 — Task Scheduler**

1. Open **Task Scheduler** → **Create Basic Task**.
2. Trigger: **When I log on**.
3. Action: **Start a program**.
4. Program: `E:\CA Tools\ca-compliance-reminder\venv\Scripts\pythonw.exe`
5. Arguments: `main.py`
6. Start in: `E:\CA Tools\ca-compliance-reminder`

This method gives more control (e.g., run only on certain days).

---

## Appendix — Building a Standalone .exe

To share the app with colleagues who don't have Python installed:

```cmd
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist\CA_Compliance_Reminder\CA_Compliance_Reminder.exe`

Copy the entire `dist\CA_Compliance_Reminder\` folder to any Windows PC and run the `.exe` — no Python required.

---

*CA Compliance Reminder v1.0 · Data encrypted · DPDP Act 2023 compliant*
