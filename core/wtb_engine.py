"""Working Trial Balance — compute, validate, aggregate.

Ported from Engine_WTB.gs logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from core.master_db import get_lookup_map, MappingEntry


@dataclass
class WTBLine:
    wtb_id: int
    raw_tb_id: int
    ledger_name: str
    group_name: str
    mapping_code: str
    entry: MappingEntry | None
    confidence: float
    source: str
    cy_net: float
    py_net: float
    is_confirmed: bool


@dataclass
class ValidationResult:
    ok: bool
    balance_diff_cy: float = 0.0
    balance_diff_py: float = 0.0
    unmapped_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_wtb_lines(wtb_rows, raw_tb_rows) -> list[WTBLine]:
    """Build WTBLine objects from database rows with error resilience."""
    lookup = get_lookup_map()
    
    # Index raw_tb by id
    raw_map = {}
    for r in raw_tb_rows:
        rd = dict(r) if hasattr(r, "keys") else (r if isinstance(r, dict) else {})
        if "id" in rd:
            raw_map[rd["id"]] = rd

    # Index wtb by raw_tb_id
    wtb_by_raw_id = {}
    for row in wtb_rows:
        w = dict(row) if hasattr(row, "keys") else (row if isinstance(row, dict) else {})
        raw_id = w.get("raw_tb_id")
        if raw_id is not None:
            wtb_by_raw_id[raw_id] = w

    lines = []
    if raw_map:
        for raw_id, raw in raw_map.items():
            w = wtb_by_raw_id.get(raw_id, {})
            m_code = w.get("mapping_code") or ""
            entry = lookup.get(m_code) if m_code else None
            cy_net = float(w.get("cy_net") if "cy_net" in w and w.get("cy_net") is not None else raw.get("cy_net") or 0.0)
            py_net = float(w.get("py_net") if "py_net" in w and w.get("py_net") is not None else raw.get("py_net") or 0.0)
            lines.append(WTBLine(
                wtb_id       = int(w.get("id") or raw_id),
                raw_tb_id    = raw_id,
                ledger_name  = raw.get("ledger_name") or w.get("ledger_name") or "Unknown Ledger",
                group_name   = raw.get("group_name") or w.get("group_name") or "",
                mapping_code = m_code,
                entry        = entry,
                confidence   = float(w.get("confidence") or 0.0),
                source       = w.get("confidence_source") or "MANUAL",
                cy_net       = cy_net,
                py_net       = py_net,
                is_confirmed = bool(w.get("is_confirmed", 0)),
            ))
    else:
        for row in wtb_rows:
            w = dict(row) if hasattr(row, "keys") else (row if isinstance(row, dict) else {})
            raw_id = w.get("raw_tb_id") or 0
            raw = raw_map.get(raw_id)
            m_code = w.get("mapping_code") or ""
            entry = lookup.get(m_code) if m_code else None
            lines.append(WTBLine(
                wtb_id       = int(w.get("id") or raw_id),
                raw_tb_id    = raw_id,
                ledger_name  = (raw.get("ledger_name") if raw else None) or w.get("ledger_name") or "Unknown Ledger",
                group_name   = (raw.get("group_name") if raw else None) or w.get("group_name") or "",
                mapping_code = m_code,
                entry        = entry,
                confidence   = float(w.get("confidence") or 0.0),
                source       = w.get("confidence_source") or "MANUAL",
                cy_net       = float(w.get("cy_net") or 0.0),
                py_net       = float(w.get("py_net") or 0.0),
                is_confirmed = bool(w.get("is_confirmed", 0)),
            ))

    return lines


def aggregate_by_code(lines: list[WTBLine]) -> dict[str, tuple[float, float]]:
    """Sum CY and PY net amounts by mapping_code."""
    result: dict[str, list[float]] = {}
    for l in lines:
        if not l.mapping_code:
            continue
        try:
            result.setdefault(l.mapping_code, [0.0, 0.0])
            result[l.mapping_code][0] += float(l.cy_net or 0.0)
            result[l.mapping_code][1] += float(l.py_net or 0.0)
        except (ValueError, TypeError):
            continue
    return {k: (v[0], v[1]) for k, v in result.items()}


def apply_adjustments(
    totals: dict[str, tuple[float, float]],
    adj_rows: list,
    lookup: dict | None = None,
) -> dict[str, tuple[float, float]]:
    """Fold adjustment journal entries (dr/cr) into CY totals by mapping_code."""
    if lookup is None:
        from core.master_db import get_lookup_map
        lookup = get_lookup_map()
    result: dict[str, list[float]] = {k: list(v) for k, v in totals.items()}
    for adj in adj_rows:
        code = adj["mapping_code"] if adj["mapping_code"] else ""
        if not code:
            continue
        dr  = float(adj["dr_amount"] or 0)
        cr  = float(adj["cr_amount"] or 0)
        entry = lookup.get(code)
        net = cr - dr
        if code not in result:
            result[code] = [0.0, 0.0]
        result[code][0] += net
    return {k: (v[0], v[1]) for k, v in result.items()}


def validate_balance(
    totals: dict[str, tuple[float, float]],
    entity_type: str,
) -> ValidationResult:
    """Check BS balance and P&L tie-out."""
    from core.master_db import MASTER

    lookup = get_lookup_map()
    bs_cy = 0.0
    bs_py = 0.0
    pl_net_cy = 0.0
    pl_net_py = 0.0

    for code, (cy, py) in totals.items():
        e = lookup.get(code)
        if not e:
            continue
        if e.fs_tag in ("BS",):
            bs_cy += cy
            bs_py += py
        elif e.fs_tag in ("PL", "IE"):
            pl_net_cy += cy
            pl_net_py += py

    errors = []
    warnings = []
    
    total_cy_diff = bs_cy + pl_net_cy
    total_py_diff = bs_py + pl_net_py

    if abs(total_cy_diff) > 1:
        errors.append(f"TB does not balance — CY difference: ₹{total_cy_diff:,.2f}")
    if abs(total_py_diff) > 1:
        warnings.append(f"TB PY does not balance — difference: ₹{total_py_diff:,.2f}")

    return ValidationResult(
        ok              = not errors,
        balance_diff_cy = total_cy_diff,
        balance_diff_py = total_py_diff,
        errors          = errors,
        warnings        = warnings,
    )


def compute_net_from_raw(row_obj: Any, sign: str) -> float:
    """Apply sign convention: DR_POSITIVE → cy_debit - cy_credit."""
    row = dict(row_obj) if not isinstance(row_obj, dict) else row_obj
    dr = float(row.get("cy_debit", 0) or 0)
    cr = float(row.get("cy_credit", 0) or 0)
    net = float(row.get("cy_net", 0) or 0)
    if net != 0:
        return net
    return cr - dr
