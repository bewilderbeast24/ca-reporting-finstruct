"""
SQLite database layer with application-level field encryption for all PII.

Schema covers:
  settings            — key/value app config
  email_accounts      — SMTP credentials (encrypted)
  clients             — client PII (encrypted)
  compliances         — compliance type definitions
  client_compliances  — many-to-many assignment
  send_logs           — audit trail of every reminder dispatch
"""

import logging
import sqlite3
from datetime import date, datetime
from typing import Optional

from ca_reminder.config import DB_PATH
from ca_reminder.data.encryption import EncryptionManager

logger = logging.getLogger(__name__)

# ── DDL ───────────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS email_accounts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name  TEXT    NOT NULL,
    email_address TEXT    NOT NULL,   -- encrypted
    provider      TEXT    NOT NULL,   -- gmail | zoho | microsoft | custom
    smtp_host     TEXT    NOT NULL,
    smtp_port     INTEGER NOT NULL DEFAULT 587,
    use_tls       INTEGER NOT NULL DEFAULT 1,
    username      TEXT    NOT NULL,   -- encrypted
    password      TEXT    NOT NULL,   -- encrypted (app password)
    sender_name   TEXT    NOT NULL DEFAULT '',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_code   TEXT    UNIQUE,
    name          TEXT    NOT NULL,   -- encrypted
    email         TEXT    NOT NULL,   -- encrypted
    phone         TEXT    NOT NULL DEFAULT '',  -- encrypted
    pan           TEXT    NOT NULL DEFAULT '',  -- encrypted
    gstin         TEXT    NOT NULL DEFAULT '',  -- encrypted
    consent_given INTEGER NOT NULL DEFAULT 0,
    consent_date  TEXT    NOT NULL DEFAULT '',
    notes         TEXT    NOT NULL DEFAULT '',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS compliances (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL,
    description           TEXT    NOT NULL DEFAULT '',
    category              TEXT    NOT NULL,
    frequency             TEXT    NOT NULL,
    due_day               INTEGER,          -- day-of-month (1-31); NULL for event-based
    due_month             INTEGER,          -- 1-12, used for Annual frequency
    advance_reminder_days INTEGER NOT NULL DEFAULT 7,
    active                INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS client_compliances (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER NOT NULL REFERENCES clients(id)     ON DELETE CASCADE,
    compliance_id  INTEGER NOT NULL REFERENCES compliances(id) ON DELETE CASCADE,
    custom_due_day INTEGER,
    notes          TEXT    NOT NULL DEFAULT '',
    active         INTEGER NOT NULL DEFAULT 1,
    UNIQUE(client_id, compliance_id)
);

CREATE TABLE IF NOT EXISTS send_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER REFERENCES clients(id),
    email_account_id INTEGER REFERENCES email_accounts(id),
    sent_at          TEXT    NOT NULL,
    month_year       TEXT    NOT NULL,   -- YYYY-MM
    status           TEXT    NOT NULL,   -- sent | failed | skipped
    error_message    TEXT    NOT NULL DEFAULT '',
    compliance_count INTEGER NOT NULL DEFAULT 0,
    recipient_email  TEXT    NOT NULL    -- encrypted
);
"""

# ── Default compliances (seeded on first run) ─────────────────────────────────

_DEFAULT_COMPLIANCES = [
    # (name, description, category, frequency, due_day, due_month, advance_days)
    ("GSTR-1 (Monthly)",        "Monthly return — outward supplies",           "GST",           "Monthly",   11, None, 7),
    ("GSTR-3B",                 "Monthly summary GST return",                  "GST",           "Monthly",   20, None, 7),
    ("GSTR-9 Annual Return",    "Annual GST consolidated return",              "GST",           "Annual",    31, 12,   30),
    ("TDS Payment",             "Monthly TDS deposit to government",           "TDS / TCS",     "Monthly",    7, None, 3),
    ("TDS Return (Quarterly)",  "Quarterly TDS / TCS return (Form 26Q/27Q)",  "TDS / TCS",     "Quarterly", 31, None, 15),
    ("Advance Tax — Q1",        "15 June instalment (15% of tax)",             "Income Tax",    "Annual",    15, 6,    7),
    ("Advance Tax — Q2",        "15 September instalment (45% cumulative)",    "Income Tax",    "Annual",    15, 9,    7),
    ("Advance Tax — Q3",        "15 December instalment (75% cumulative)",     "Income Tax",    "Annual",    15, 12,   7),
    ("Advance Tax — Q4",        "15 March instalment (100% cumulative)",       "Income Tax",    "Annual",    15, 3,    7),
    ("ITR — Individuals",       "Income Tax Return for individuals / HUF",     "Income Tax",    "Annual",    31, 7,    30),
    ("ITR — Audit Cases",       "ITR for companies / audit-required entities", "Income Tax",    "Annual",    31, 10,   30),
    ("ROC Annual Return MGT-7", "Annual return filing with MCA",               "ROC / MCA",     "Annual",    29, 11,   15),
    ("AOC-4 Financial Stmts",   "Financial statements filing with MCA",        "ROC / MCA",     "Annual",    29, 10,   15),
    ("PF Monthly Contribution", "Provident Fund monthly payment",              "PF / ESI",      "Monthly",   15, None, 5),
    ("ESI Monthly Payment",     "Employee State Insurance monthly payment",    "PF / ESI",      "Monthly",   15, None, 5),
    ("Professional Tax",        "State professional tax monthly / annual",     "Professional Tax","Monthly", 30, None, 5),
]


class Database:
    """All database operations for the CA Compliance Reminder application."""

    def __init__(self, enc: EncryptionManager) -> None:
        self.enc = enc
        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection ────────────────────────────────────────────────────────────

    def _conn_(self) -> sqlite3.Connection:
        if self._conn is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn

    def initialize(self) -> None:
        conn = self._conn_()
        conn.executescript(_SCHEMA)
        conn.commit()
        self._migrate()
        self._seed_compliances()
        logger.info("Database ready: %s", DB_PATH)

    def _migrate(self) -> None:
        """Apply incremental schema migrations for existing databases."""
        conn = self._conn_()
        cols = {row[1] for row in
                conn.execute("PRAGMA table_info(email_accounts)").fetchall()}
        if "encryption" not in cols:
            conn.execute(
                "ALTER TABLE email_accounts "
                "ADD COLUMN encryption TEXT NOT NULL DEFAULT 'STARTTLS'"
            )
            conn.commit()
            logger.info("Migration: added 'encryption' column to email_accounts")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn_().execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn_().execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value)
        )
        self._conn_().commit()

    # ── Email accounts ────────────────────────────────────────────────────────

    def save_email_account(self, data: dict) -> int:
        now = _now()
        acct_id = data.get("id")
        if acct_id:
            self._conn_().execute(
                """UPDATE email_accounts SET
                   display_name=:display_name, email_address=:email_address,
                   provider=:provider, smtp_host=:smtp_host, smtp_port=:smtp_port,
                   use_tls=:use_tls, encryption=:encryption,
                   username=:username, password=:password,
                   sender_name=:sender_name
                   WHERE id=:id""",
                {**self._encrypt_account(data), "id": acct_id},
            )
        else:
            cur = self._conn_().execute(
                """INSERT INTO email_accounts
                   (display_name, email_address, provider, smtp_host, smtp_port,
                    use_tls, encryption, username, password, sender_name, active, created_at)
                   VALUES (:display_name,:email_address,:provider,:smtp_host,:smtp_port,
                           :use_tls,:encryption,:username,:password,:sender_name,1,:created_at)""",
                {**self._encrypt_account(data), "created_at": now},
            )
            acct_id = cur.lastrowid
        self._conn_().commit()
        return acct_id

    def get_active_email_account(self) -> Optional[dict]:
        row = self._conn_().execute(
            "SELECT * FROM email_accounts WHERE active=1 ORDER BY id LIMIT 1"
        ).fetchone()
        return self._decrypt_account(dict(row)) if row else None

    def get_all_email_accounts(self) -> list[dict]:
        rows = self._conn_().execute(
            "SELECT * FROM email_accounts ORDER BY id"
        ).fetchall()
        return [self._decrypt_account(dict(r)) for r in rows]

    def delete_email_account(self, acct_id: int) -> None:
        self._conn_().execute("DELETE FROM email_accounts WHERE id=?", (acct_id,))
        self._conn_().commit()

    def _encrypt_account(self, d: dict) -> dict:
        # Derive encryption string from old use_tls bool if new field absent
        enc = d.get("encryption") or ("STARTTLS" if d.get("use_tls", True) else "None")
        return {
            **d,
            "email_address": self.enc.encrypt(d.get("email_address", "")),
            "username":      self.enc.encrypt(d.get("username", "")),
            "password":      self.enc.encrypt(d.get("password", "")),
            "use_tls":       1 if enc == "STARTTLS" else 0,
            "encryption":    enc,
        }

    def _decrypt_account(self, d: dict) -> dict:
        d["email_address"] = self.enc.decrypt(d["email_address"])
        d["username"]      = self.enc.decrypt(d["username"])
        d["password"]      = self.enc.decrypt(d["password"])
        d["use_tls"]       = bool(d["use_tls"])
        # Back-fill encryption string for rows saved before migration
        if not d.get("encryption"):
            d["encryption"] = "STARTTLS" if d["use_tls"] else "None"
        return d

    # ── Clients ───────────────────────────────────────────────────────────────

    def save_client(self, data: dict) -> int:
        now = _now()
        enc = self._encrypt_client(data)
        client_id = data.get("id")
        if client_id:
            self._conn_().execute(
                """UPDATE clients SET
                   client_code=:client_code, name=:name, email=:email,
                   phone=:phone, pan=:pan, gstin=:gstin,
                   consent_given=:consent_given, consent_date=:consent_date,
                   notes=:notes, updated_at=:updated_at
                   WHERE id=:id""",
                {**enc, "id": client_id, "updated_at": now},
            )
        else:
            cur = self._conn_().execute(
                """INSERT INTO clients
                   (client_code,name,email,phone,pan,gstin,
                    consent_given,consent_date,notes,active,created_at,updated_at)
                   VALUES(:client_code,:name,:email,:phone,:pan,:gstin,
                          :consent_given,:consent_date,:notes,1,:created_at,:updated_at)""",
                {**enc, "created_at": now, "updated_at": now},
            )
            client_id = cur.lastrowid
        self._conn_().commit()
        return client_id

    def get_all_clients(self, active_only: bool = True) -> list[dict]:
        q = "SELECT * FROM clients" + (" WHERE active=1" if active_only else "") + " ORDER BY rowid"
        rows = self._conn_().execute(q).fetchall()
        return [self._decrypt_client(dict(r)) for r in rows]

    def get_client(self, client_id: int) -> Optional[dict]:
        row = self._conn_().execute(
            "SELECT * FROM clients WHERE id=?", (client_id,)
        ).fetchone()
        return self._decrypt_client(dict(row)) if row else None

    def soft_delete_client(self, client_id: int) -> None:
        self._conn_().execute(
            "UPDATE clients SET active=0, updated_at=? WHERE id=?",
            (_now(), client_id),
        )
        self._conn_().commit()

    def hard_delete_client(self, client_id: int) -> None:
        """DPDP Act — right to erasure: permanently removes all client data."""
        conn = self._conn_()
        conn.execute("DELETE FROM client_compliances WHERE client_id=?", (client_id,))
        conn.execute("DELETE FROM send_logs WHERE client_id=?", (client_id,))
        conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        conn.commit()

    def _encrypt_client(self, d: dict) -> dict:
        # Use None (not "") for empty client_code so the UNIQUE constraint
        # allows multiple clients without a code (SQLite permits multiple NULLs).
        raw_code = (d.get("client_code") or "").strip()
        return {
            "client_code":   raw_code if raw_code else None,
            "name":          self.enc.encrypt(d.get("name", "")),
            "email":         self.enc.encrypt(d.get("email", "")),
            "phone":         self.enc.encrypt(d.get("phone", "") or ""),
            "pan":           self.enc.encrypt(d.get("pan", "") or ""),
            "gstin":         self.enc.encrypt(d.get("gstin", "") or ""),
            "consent_given": 1 if d.get("consent_given") else 0,
            "consent_date":  d.get("consent_date", "") or "",
            "notes":         d.get("notes", "") or "",
        }

    def _decrypt_client(self, d: dict) -> dict:
        for field in ("name", "email", "phone", "pan", "gstin"):
            d[field] = self.enc.decrypt(d.get(field) or "")
        return d

    # ── Compliances ───────────────────────────────────────────────────────────

    def save_compliance(self, data: dict) -> int:
        comp_id = data.get("id")
        fields = {
            "name":                  data["name"],
            "description":           data.get("description", ""),
            "category":              data["category"],
            "frequency":             data["frequency"],
            "due_day":               data.get("due_day"),
            "due_month":             data.get("due_month"),
            "advance_reminder_days": data.get("advance_reminder_days", 7),
        }
        if comp_id:
            self._conn_().execute(
                """UPDATE compliances SET name=:name,description=:description,
                   category=:category,frequency=:frequency,due_day=:due_day,
                   due_month=:due_month,advance_reminder_days=:advance_reminder_days
                   WHERE id=:id""",
                {**fields, "id": comp_id},
            )
        else:
            cur = self._conn_().execute(
                """INSERT INTO compliances
                   (name,description,category,frequency,due_day,due_month,
                    advance_reminder_days,active)
                   VALUES(:name,:description,:category,:frequency,:due_day,:due_month,
                          :advance_reminder_days,1)""",
                fields,
            )
            comp_id = cur.lastrowid
        self._conn_().commit()
        return comp_id

    def get_all_compliances(self, active_only: bool = True) -> list[dict]:
        q = "SELECT * FROM compliances"
        if active_only:
            q += " WHERE active=1"
        rows = self._conn_().execute(q + " ORDER BY category,name").fetchall()
        return [dict(r) for r in rows]

    def get_compliance(self, comp_id: int) -> Optional[dict]:
        row = self._conn_().execute(
            "SELECT * FROM compliances WHERE id=?", (comp_id,)
        ).fetchone()
        return dict(row) if row else None

    def toggle_compliance_active(self, comp_id: int, active: bool) -> None:
        self._conn_().execute(
            "UPDATE compliances SET active=? WHERE id=?", (1 if active else 0, comp_id)
        )
        self._conn_().commit()

    def delete_compliance(self, comp_id: int) -> None:
        """Permanently delete a compliance and all client assignments for it."""
        conn = self._conn_()
        conn.execute("DELETE FROM client_compliances WHERE compliance_id=?", (comp_id,))
        conn.execute("DELETE FROM compliances WHERE id=?", (comp_id,))
        conn.commit()

    # ── Assignments ───────────────────────────────────────────────────────────

    def assign_compliance(
        self, client_id: int, compliance_id: int,
        custom_due_day: Optional[int] = None, notes: str = ""
    ) -> None:
        self._conn_().execute(
            """INSERT OR REPLACE INTO client_compliances
               (client_id,compliance_id,custom_due_day,notes,active)
               VALUES (?,?,?,?,1)""",
            (client_id, compliance_id, custom_due_day, notes),
        )
        self._conn_().commit()

    def remove_assignment(self, client_id: int, compliance_id: int) -> None:
        self._conn_().execute(
            "DELETE FROM client_compliances WHERE client_id=? AND compliance_id=?",
            (client_id, compliance_id),
        )
        self._conn_().commit()

    def get_client_compliances(self, client_id: int) -> list[dict]:
        rows = self._conn_().execute(
            """SELECT cc.*, co.name, co.description, co.category,
                      co.frequency, co.due_day, co.due_month
               FROM client_compliances cc
               JOIN compliances co ON cc.compliance_id = co.id
               WHERE cc.client_id=? AND cc.active=1 AND co.active=1
               ORDER BY co.category, co.name""",
            (client_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_unassigned_compliances(self, client_id: int) -> list[dict]:
        rows = self._conn_().execute(
            """SELECT * FROM compliances
               WHERE active=1
                 AND id NOT IN (
                     SELECT compliance_id FROM client_compliances
                     WHERE client_id=? AND active=1
                 )
               ORDER BY category, name""",
            (client_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Clients-with-compliances (for monthly send) ───────────────────────────

    def get_clients_for_reminder(self, year: int, month: int) -> list[dict]:
        """
        Return active, consenting clients who have at least one compliance
        relevant to *year/month*, with the relevant compliances attached.
        """
        all_clients = self._conn_().execute(
            "SELECT * FROM clients WHERE active=1 AND consent_given=1 ORDER BY rowid"
        ).fetchall()

        result = []
        for row in all_clients:
            client = self._decrypt_client(dict(row))
            compliances = self.get_client_compliances(client["id"])
            relevant = _filter_for_month(compliances, month)
            if relevant:
                client["compliances"] = relevant
                result.append(client)
        return result

    def get_unsent_clients_for_reminder(self, year: int, month: int) -> list[dict]:
        """
        Return active, consenting clients who have at least one compliance
        relevant to *year/month*, EXCLUDING those who already have a 'sent' 
        status in send_logs for this month.
        """
        month_year = f"{year}-{month:02d}"
        all_clients = self._conn_().execute(
            """SELECT c.* FROM clients c 
               WHERE c.active=1 AND c.consent_given=1 
               AND c.id NOT IN (
                   SELECT client_id FROM send_logs 
                   WHERE month_year=? AND status='sent'
               )
               ORDER BY c.rowid""",
            (month_year,)
        ).fetchall()

        result = []
        for row in all_clients:
            client = self._decrypt_client(dict(row))
            compliances = self.get_client_compliances(client["id"])
            relevant = _filter_for_month(compliances, month)
            if relevant:
                client["compliances"] = relevant
                result.append(client)
        return result

    # ── Send logs ─────────────────────────────────────────────────────────────

    def log_send(
        self, *, client_id: int, email_account_id: int,
        month_year: str, status: str, recipient_email: str,
        error_message: str = "", compliance_count: int = 0,
    ) -> None:
        self._conn_().execute(
            """INSERT INTO send_logs
               (client_id,email_account_id,sent_at,month_year,status,
                error_message,compliance_count,recipient_email)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                client_id, email_account_id, _now(), month_year, status,
                error_message, compliance_count,
                self.enc.encrypt(recipient_email),
            ),
        )
        self._conn_().commit()

    def already_sent_today(self, month_year: str) -> bool:
        today = date.today().isoformat()
        row = self._conn_().execute(
            "SELECT 1 FROM send_logs WHERE month_year=? AND status='sent' AND sent_at LIKE ?",
            (month_year, f"{today}%"),
        ).fetchone()
        return row is not None

    def get_recent_logs(self, limit: int = 200) -> list[dict]:
        rows = self._conn_().execute(
            """SELECT sl.*, cl.name AS _client_enc
               FROM send_logs sl
               LEFT JOIN clients cl ON sl.client_id = cl.id
               ORDER BY sl.sent_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["recipient_email"] = self.enc.decrypt(d["recipient_email"])
            d["client_name"]     = self.enc.decrypt(d.get("_client_enc") or "") or "—"
            result.append(d)
        return result

    # ── Seed ─────────────────────────────────────────────────────────────────

    def _seed_compliances(self) -> None:
        count = self._conn_().execute(
            "SELECT COUNT(*) FROM compliances"
        ).fetchone()[0]
        if count:
            return
        self._conn_().executemany(
            """INSERT INTO compliances
               (name,description,category,frequency,due_day,due_month,
                advance_reminder_days,active)
               VALUES (?,?,?,?,?,?,?,1)""",
            _DEFAULT_COMPLIANCES,
        )
        self._conn_().commit()
        logger.info("Seeded %d default compliances.", len(_DEFAULT_COMPLIANCES))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat()


def _filter_for_month(compliances: list[dict], month: int) -> list[dict]:
    """Return compliances relevant to the given calendar month."""
    relevant = []
    for c in compliances:
        freq = (c.get("frequency") or "").lower()
        if freq == "monthly":
            relevant.append(c)
        elif freq == "quarterly":
            # Remind in the last month of each FY quarter:
            # Q1 ends Jun, Q2 ends Sep, Q3 ends Dec, Q4 ends Mar
            if month in {3, 6, 9, 12}:
                relevant.append(c)
        elif freq == "half-yearly":
            # Remind in the last month of each half-year: Sep (H1) and Mar (H2)
            if month in {3, 9}:
                relevant.append(c)
        elif freq == "annual":
            if c.get("due_month") == month:
                relevant.append(c)
        elif freq == "event-based":
            relevant.append(c)
    return relevant
