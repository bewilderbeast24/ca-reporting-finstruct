"""
Startup scheduler — triggers monthly compliance reminder emails.

Logic (runs once per app launch):
  1. Is today the configured REMINDER_SEND_DAY (default: 1st of month)?
  2. Have reminders already been sent today for this month?
  3. Is an email account configured?
  If all checks pass → send reminders for every eligible client.
"""

import logging
import time
from datetime import date
from typing import Callable, Optional

from ca_reminder.config import REMINDER_SEND_DAY
from ca_reminder.core.mailer import send_reminder_email, get_smtp_connection
from ca_reminder.data.database import Database

logger = logging.getLogger(__name__)

ProgressFn = Optional[Callable[[str], None]]


def check_and_send(
    db: Database,
    progress: ProgressFn = None,
    force: bool = False,
    resume_unsent: bool = False,
) -> dict:
    """
    Run the monthly reminder job.

    Args:
        db:       Initialised Database instance.
        progress: Optional callback(str) for UI progress messages.
        force:    If True, bypass the "already sent today" guard
                  (useful for the manual "Send Now" button).

    Returns a result dict:
        triggered (bool)  — whether the job actually ran
        sent      (int)   — emails dispatched successfully
        failed    (int)   — emails that encountered an error
        skipped   (int)   — clients without consent / no compliances
        errors    (list)  — (client_name, error_message) tuples
        month_year (str)  — 'YYYY-MM' of the run
    """
    today      = date.today()
    month_year = today.strftime("%Y-%m")

    result: dict = dict(
        triggered=False, sent=0, failed=0, skipped=0,
        errors=[], month_year=month_year,
    )

    # ── Guard: only run on the configured day (unless forced) ─────────────────
    if not force and today.day != REMINDER_SEND_DAY:
        logger.info(
            "Today is day %d; reminder day is %d — not triggered.",
            today.day, REMINDER_SEND_DAY,
        )
        return result

    # ── Guard: don't double-send ───────────────────────────────────────────────
    if not force and db.already_sent_today(month_year):
        logger.info("Reminders already sent today for %s — skipping.", month_year)
        return result

    result["triggered"] = True
    _progress(progress, "Checking email account…")

    account = db.get_active_email_account()
    if not account:
        msg = (
            "No active email account configured. "
            "Please add one in the Email Setup tab."
        )
        logger.warning(msg)
        result["errors"].append(("—", msg))
        return result

    _progress(progress, f"Collecting clients for {month_year}…")
    if resume_unsent:
        clients = db.get_unsent_clients_for_reminder(today.year, today.month)
    else:
        clients = db.get_clients_for_reminder(today.year, today.month)

    if not clients:
        logger.info("No eligible clients for %s.", month_year)
        return result

    smtp_conn = None
    try:
        for client in clients:
            compliances = client.pop("compliances", [])

            if not client.get("consent_given"):
                result["skipped"] += 1
                continue

            if not compliances:
                result["skipped"] += 1
                continue

            if smtp_conn is None:
                _progress(progress, "Connecting to email server…")
                try:
                    smtp_conn = get_smtp_connection(account)
                except Exception as exc:
                    msg = f"Failed to connect to email server: {exc}"
                    logger.error(msg)
                    result["errors"].append(("—", msg))
                    break

            _progress(progress, f"Sending to {client['name']}…")
            ok, err = send_reminder_email(
                account=account,
                client=client,
                compliances=compliances,
                year=today.year,
                month=today.month,
                conn=smtp_conn,
            )

            db.log_send(
                client_id=client["id"],
                email_account_id=account["id"],
                month_year=month_year,
                status="sent" if ok else "failed",
                recipient_email=client["email"],
                error_message=err,
                compliance_count=len(compliances),
            )

            if ok:
                result["sent"] += 1
            else:
                result["failed"] += 1
                result["errors"].append((client["name"], err))
                
                # Auto-heal: If the server disconnected or there's a network drop,
                # reset the connection so it re-establishes on the next client.
                err_lower = err.lower()
                if "network error" in err_lower or "server disconnected" in err_lower or "connection" in err_lower:
                    if smtp_conn:
                        try:
                            smtp_conn.quit()
                        except Exception:
                            pass
                    smtp_conn = None
                
            time.sleep(1.5)  # Pacing to avoid SMTP rate limits
    finally:
        if smtp_conn:
            try:
                smtp_conn.quit()
            except Exception:
                pass

    logger.info(
        "Reminder run %s — sent:%d  failed:%d  skipped:%d",
        month_year, result["sent"], result["failed"], result["skipped"],
    )
    return result


def _progress(fn: ProgressFn, msg: str) -> None:
    if fn:
        try:
            fn(msg)
        except Exception:
            pass
