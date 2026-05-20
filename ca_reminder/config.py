"""
Central configuration for CA Compliance Reminder.
All paths, constants, and provider defaults live here.
"""

from pathlib import Path

APP_NAME = "CA Compliance Reminder"
APP_VERSION = "1.0.0"

# ── Filesystem ────────────────────────────────────────────────────────────────
APP_DIR = Path.home() / ".ca_compliance_reminder"
DB_PATH = APP_DIR / "compliance_data.db"
LOG_PATH = APP_DIR / "app.log"

# ── Encryption / DPDP Act ─────────────────────────────────────────────────────
KEYRING_SERVICE = "ca_compliance_reminder_v1"
KEYRING_KEY_ACCOUNT = "fernet_master_key"
# Fallback key file (used when OS keyring is unavailable)
KEY_FILE = APP_DIR / ".enc_key"

DPDP_NOTICE = (
    "All personal data stored by this application is encrypted at rest "
    "in compliance with the Digital Personal Data Protection Act, 2023 (DPDP Act). "
    "Client data is used solely for sending compliance reminders and is never "
    "shared with any third party."
)

# ── Scheduling ────────────────────────────────────────────────────────────────
# Day of month on which reminders are auto-sent (1 = 1st of every month)
REMINDER_SEND_DAY = 1

# ── Domain look-ups ───────────────────────────────────────────────────────────
COMPLIANCE_CATEGORIES = [
    "GST",
    "TDS / TCS",
    "Income Tax",
    "ROC / MCA",
    "PF / ESI",
    "Professional Tax",
    "FEMA / RBI",
    "Custom / Others",
]

COMPLIANCE_FREQUENCIES = [
    "Monthly",
    "Quarterly",
    "Half-Yearly",
    "Annual",
    "Event-Based",
]

# ── SMTP encryption options ───────────────────────────────────────────────────
SMTP_ENCRYPTION_OPTIONS = ["STARTTLS", "SSL", "None"]
# Default port associated with each encryption mode
SMTP_DEFAULT_PORTS: dict[str, int] = {
    "STARTTLS": 587,
    "SSL":      465,
    "None":     25,
}

# ── Email provider presets ────────────────────────────────────────────────────
EMAIL_PROVIDERS: dict[str, dict] = {
    "gmail": {
        "name": "Gmail",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "encryption": "STARTTLS",   # port 465 + SSL also works
        "help": (
            "Gmail requires an App Password — NOT your regular Gmail password.\n\n"
            "STEP 1 — Enable 2-Step Verification (mandatory prerequisite):\n"
            "  1. Open myaccount.google.com in a browser\n"
            "  2. Click 'Security' in the left sidebar\n"
            "  3. Under 'How you sign in to Google', click '2-Step Verification'\n"
            "  4. Follow the on-screen prompts and turn it ON\n\n"
            "STEP 2 — Generate an App Password:\n"
            "  1. Go to: myaccount.google.com/apppasswords\n"
            "     (Tip: type 'App Passwords' in the Google Account search bar)\n"
            "  2. In the 'App name' field type: CA Compliance Reminder\n"
            "  3. Click 'Create'\n"
            "  4. Google shows a 16-character password — copy it immediately\n"
            "     (it will NOT be shown again)\n"
            "  5. Paste it into the App Password field in this form\n\n"
            "If myaccount.google.com/apppasswords says 'Setting not available':\n"
            "  • 2-Step Verification is not yet active — complete Step 1 first\n"
            "  • Google Workspace (business/school) users: your admin must enable\n"
            "    App Passwords in the Google Admin console\n\n"
            "SMTP: smtp.gmail.com  |  Port 587 + STARTTLS  or  Port 465 + SSL"
        ),
    },
    "zoho_in": {
        "name": "Zoho India (zoho.in)",
        "smtp_host": "smtp.zoho.in",
        "smtp_port": 587,
        "encryption": "STARTTLS",
        "help": (
            "For Zoho Mail accounts on India servers — free plans, SMB plans,\n"
            "or domains hosted on zoho.in.\n\n"
            "Generate an App Password:\n"
            "  1. Log in at mail.zoho.in\n"
            "  2. Click the gear icon (Settings) → Security\n"
            "  3. Under 'App Passwords', click 'Generate New Password'\n"
            "  4. Name it 'CA Reminder' → click Generate\n"
            "  5. Copy the password and paste it in the App Password field below\n\n"
            "SMTP Username: your full email address (e.g. you@yourdomain.in)\n\n"
            "SMTP: smtp.zoho.in  |  Port 587 + STARTTLS  or  Port 465 + SSL\n\n"
            "If smtp.zoho.in fails, try the 'Zoho Global' preset (smtp.zoho.com)."
        ),
    },
    "zoho": {
        "name": "Zoho Global (zoho.com)",
        "smtp_host": "smtp.zoho.com",
        "smtp_port": 587,
        "encryption": "STARTTLS",
        "help": (
            "For Zoho Mail paid / business accounts or international accounts\n"
            "created on zoho.com.\n\n"
            "Generate an App Password:\n"
            "  1. Log in at mail.zoho.com\n"
            "  2. Click the gear icon (Settings) → Security\n"
            "  3. Under 'App Passwords', click 'Generate New Password'\n"
            "  4. Name it 'CA Reminder' → click Generate\n"
            "  5. Copy the password and paste it in the App Password field below\n\n"
            "SMTP Username: your full email address\n\n"
            "SMTP: smtp.zoho.com  |  Port 587 + STARTTLS  or  Port 465 + SSL\n\n"
            "If smtp.zoho.com fails, try the 'Zoho India' preset (smtp.zoho.in)."
        ),
    },
    "microsoft": {
        "name": "Microsoft 365 / Outlook",
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "encryption": "STARTTLS",
        "help": (
            "For Microsoft 365 Business and Outlook.com (personal) accounts.\n\n"
            "SMTP AUTH must be enabled for your mailbox (admin step):\n"
            "  Microsoft 365 Admin Centre → Users → Active Users\n"
            "  → select the user → Mail tab → Manage email apps\n"
            "  → tick 'Authenticated SMTP' → Save\n\n"
            "If Multi-Factor Authentication (MFA) is enabled:\n"
            "  1. Go to account.microsoft.com → Security\n"
            "  2. Under 'Advanced security options', click 'App passwords'\n"
            "  3. Click 'Create a new app password' — copy it and use below\n\n"
            "Outlook.com personal accounts without MFA:\n"
            "  Use your regular Outlook password.\n\n"
            "SMTP: smtp.office365.com  |  Port 587 + STARTTLS only\n"
            "(Port 465 SSL is not supported by Microsoft 365)"
        ),
    },
    "custom": {
        "name": "Custom SMTP",
        "smtp_host": "",
        "smtp_port": 587,
        "encryption": "STARTTLS",
        "help": (
            "Enter your SMTP server details manually.\n\n"
            "Common port / encryption combinations:\n"
            "  Port 587 + STARTTLS — modern standard (most providers)\n"
            "  Port 465 + SSL      — legacy; still used by many providers\n"
            "  Port 25  + None     — plain text; usually blocked by ISPs\n\n"
            "Consult your email provider's documentation for the exact settings.\n"
            "Changing the Encryption dropdown will auto-suggest the standard port."
        ),
    },
}
