"""
CA Compliance Reminder — entry point.

On every launch the app:
  1. Creates the app-data directory (~/.ca_compliance_reminder/).
  2. Loads or generates the Fernet encryption key (OS keychain or key file).
  3. Opens / migrates the SQLite database.
  4. Launches the Tkinter GUI.
  5. Runs the scheduler check in a background thread:
       - If today == REMINDER_SEND_DAY and no email sent yet today
         → dispatches compliance reminder emails to all eligible clients.
"""

import logging
import sys
import tkinter as tk
import tkinter.messagebox as mb
from pathlib import Path

# ── Bootstrap app directory before any local imports ──────────────────────────
_APP_DIR = Path.home() / ".ca_compliance_reminder"
_APP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(_APP_DIR / "app.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
# Also log to console in development
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

logger = logging.getLogger(__name__)

# ── Local imports (after path setup) ─────────────────────────────────────────
from ca_reminder.data.encryption import EncryptionManager  # noqa: E402
from ca_reminder.data.database import Database              # noqa: E402
from ca_reminder.gui.main_window import MainWindow          # noqa: E402
from ca_reminder.config import APP_NAME, APP_VERSION        # noqa: E402


def main() -> None:
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)

    try:
        enc = EncryptionManager()
        db  = Database(enc)
        db.initialize()
    except Exception as exc:
        logger.critical("Startup failure — data layer: %s", exc, exc_info=True)
        _fatal(f"Failed to initialise the database:\n\n{exc}")
        return

    root = tk.Tk()

    # Attempt to set a window icon (silently skip if asset not found)
    icon_path = Path(__file__).parent / "assets" / "icon.png"
    if icon_path.exists():
        try:
            icon = tk.PhotoImage(file=str(icon_path))
            root.iconphoto(True, icon)
        except Exception:
            pass

    try:
        MainWindow(root, db, enc)
        root.protocol("WM_DELETE_WINDOW", lambda: _on_close(root, db))
        root.mainloop()
    except Exception as exc:
        logger.critical("Unhandled exception in GUI: %s", exc, exc_info=True)
        _fatal(f"An unexpected error occurred:\n\n{exc}")
    finally:
        db.close()
        logger.info("%s closed.", APP_NAME)


def _on_close(root: tk.Tk, db: Database) -> None:
    db.close()
    root.destroy()


def _fatal(message: str) -> None:
    """Show an error dialog and exit."""
    try:
        mb.showerror("Fatal Error", message)
    except Exception:
        print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
