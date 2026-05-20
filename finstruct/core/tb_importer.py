"""Trial Balance importer — XLSX, CSV, Tally XML."""

from __future__ import annotations
import csv
import io
import logging
from pathlib import Path

log = logging.getLogger(__name__)

COMMON_LEDGER_HEADERS = {"ledger", "account", "particulars", "name", "description", "account name"}
COMMON_GROUP_HEADERS  = {"group", "category", "parent", "type", "nature"}
COMMON_DR_HEADERS     = {"debit", "dr", "debit amount", "debit balance", "closing debit"}
COMMON_CR_HEADERS     = {"credit", "cr", "credit amount", "credit balance", "closing credit"}
COMMON_NET_HEADERS    = {"net", "closing", "balance", "amount", "closing balance", "net amount"}
COMMON_PYNET_HEADERS  = {"py", "previous", "prev year", "last year", "prior year", "py amount"}


def _norm(s: str) -> str:
    return str(s or "").strip().lower().replace("_", " ")


def _detect_col(headers: list[str], candidates: set[str]) -> int | None:
    for i, h in enumerate(headers):
        if _norm(h) in candidates:
            return i
    return None


def _to_float(v) -> float:
    try:
        s = str(v or "").replace(",", "").replace("(", "-").replace(")", "").strip()
        return float(s) if s else 0.0
    except (ValueError, TypeError):
        return 0.0


class ImportResult:
    def __init__(self):
        self.rows: list[dict] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.col_map: dict[str, int | None] = {}


def import_xlsx(path: Path) -> ImportResult:
    result = ImportResult()
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            result.errors.append("Empty sheet")
            return result
        headers = [str(c or "") for c in all_rows[0]]
        _parse_rows(headers, all_rows[1:], result)
        wb.close()
    except Exception as e:
        result.errors.append(f"XLSX read error: {e}")
    return result


def import_csv(path: Path) -> ImportResult:
    result = ImportResult()
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
        reader = csv.reader(io.StringIO(text), dialect)
        rows = list(reader)
        if not rows:
            result.errors.append("Empty CSV")
            return result
        headers = rows[0]
        _parse_rows(headers, rows[1:], result)
    except Exception as e:
        result.errors.append(f"CSV read error: {e}")
    return result


def import_tally_xml(path: Path) -> ImportResult:
    result = ImportResult()
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        for ledger in root.iter("LEDGER"):
            name = ledger.get("NAME") or (ledger.findtext("NAME") or "").strip()
            parent = ledger.findtext("PARENT") or ""
            cl_bal_txt = ledger.findtext("CLOSINGBALANCE") or "0"
            is_dr = "Dr" in cl_bal_txt or "DR" in cl_bal_txt
            net = _to_float(cl_bal_txt.replace("Dr", "").replace("CR", "").replace("Cr", ""))
            if not is_dr:
                net = -net
            if name:
                result.rows.append({
                    "ledger_name": name,
                    "group_name":  parent,
                    "cy_debit":    net if net >= 0 else 0,
                    "cy_credit":   abs(net) if net < 0 else 0,
                    "cy_net":      net,
                    "py_net":      0.0,
                    "source":      "XML",
                })
    except Exception as e:
        result.errors.append(f"XML parse error: {e}")
    return result


def _parse_rows(headers: list[str], data_rows, result: ImportResult):
    lcol = _detect_col(headers, COMMON_LEDGER_HEADERS)
    gcol = _detect_col(headers, COMMON_GROUP_HEADERS)
    dcol = _detect_col(headers, COMMON_DR_HEADERS)
    ccol = _detect_col(headers, COMMON_CR_HEADERS)
    ncol = _detect_col(headers, COMMON_NET_HEADERS)
    pcol = _detect_col(headers, COMMON_PYNET_HEADERS)

    result.col_map = {
        "ledger": lcol, "group": gcol, "debit": dcol,
        "credit": ccol, "net": ncol, "py_net": pcol,
    }

    if lcol is None:
        result.errors.append(
            "Could not detect Ledger column. Please map columns manually."
        )
        # Fallback: use first column
        lcol = 0

    for i, row in enumerate(data_rows, start=2):
        row = list(row)
        if all((v is None or str(v).strip() == "") for v in row):
            continue
        name = str(row[lcol] if lcol < len(row) else "").strip()
        if not name:
            continue
        group = str(row[gcol] if gcol is not None and gcol < len(row) else "").strip()
        dr    = _to_float(row[dcol]) if dcol is not None and dcol < len(row) else 0.0
        cr    = _to_float(row[ccol]) if ccol is not None and ccol < len(row) else 0.0
        net   = _to_float(row[ncol]) if ncol is not None and ncol < len(row) else (dr - cr)
        py    = _to_float(row[pcol]) if pcol is not None and pcol < len(row) else 0.0
        result.rows.append({
            "ledger_name": name,
            "group_name":  group,
            "cy_debit":    dr,
            "cy_credit":   cr,
            "cy_net":      net,
            "py_net":      py,
            "source":      "XLSX",
        })

    # Warn on duplicate ledger names
    seen: dict[str, int] = {}
    for r in result.rows:
        n = r["ledger_name"].lower()
        seen[n] = seen.get(n, 0) + 1
    for name, cnt in seen.items():
        if cnt > 1:
            result.warnings.append(f"Duplicate ledger: '{name}' appears {cnt} times")


def override_columns(
    import_result: ImportResult,
    raw_rows: list,
    headers: list[str],
    col_map: dict[str, int | None],
) -> ImportResult:
    """Re-parse with user-supplied column assignments."""
    result = ImportResult()
    result.col_map = col_map
    _parse_rows_with_map(headers, raw_rows, result, col_map)
    return result


def _parse_rows_with_map(headers, data_rows, result, col_map):
    lcol = col_map.get("ledger")
    gcol = col_map.get("group")
    dcol = col_map.get("debit")
    ccol = col_map.get("credit")
    ncol = col_map.get("net")
    pcol = col_map.get("py_net")
    if lcol is None:
        result.errors.append("Ledger column not mapped")
        return
    for row in data_rows:
        row = list(row)
        name = str(row[lcol] if lcol < len(row) else "").strip()
        if not name:
            continue
        group = str(row[gcol] if gcol is not None and gcol < len(row) else "").strip()
        dr  = _to_float(row[dcol]) if dcol is not None and dcol < len(row) else 0.0
        cr  = _to_float(row[ccol]) if ccol is not None and ccol < len(row) else 0.0
        net = _to_float(row[ncol]) if ncol is not None and ncol < len(row) else (dr - cr)
        py  = _to_float(row[pcol]) if pcol is not None and pcol < len(row) else 0.0
        result.rows.append({
            "ledger_name": name, "group_name": group,
            "cy_debit": dr, "cy_credit": cr, "cy_net": net, "py_net": py, "source": "MANUAL",
        })
