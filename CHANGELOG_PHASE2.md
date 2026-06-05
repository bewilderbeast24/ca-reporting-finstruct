# FinStruct — Phase 2 Update (Sch III Company First)

**Date:** 5 June 2026
**Branch:** `claude/nifty-cannon-hlDuT`
**Scope:** Sch III Company-first build; LLP/NCE/AOP/Trust use the same shared engine.

---

## Headline Changes

1. **SubType auto-mapping** — TBs with a SubType column get auto-mapped at confidence 1.0. Manufacturing TB jumps from 27% → 75% auto-coverage. Account-name disambiguation finds the right sub-heading within a heading bucket.
2. **PY column editable in Mapping View** — Double-click any "PY Amount ₹" cell to enter Previous Year figures (mirrors xlsm Mapped_TB Col O). Also writable via the Excel template's PY Net column, or filled by Rollover next year.
3. **Custom Annexures with TB tie-out** — new Step 5b in the workflow. Trade Receivables Ageing, Trade Payables Ageing (MSME+Others), Share Capital working, Borrowings disclosure. Each shows TB total (auto-computed from mapped codes) and a live variance + green/red status. User-configurable tolerance (default ₹10).
4. **Auto note numbering** — xlsm-style dynamic numbering. Notes 1, 2 reserved (Accounting Policies / General Info); from 3 onwards, notes with no data are dropped and remaining notes renumber sequentially. FS line note references auto-update via the renumber map.
5. **Depreciation auto-post** — "Post Depreciation Entry" button in PPE view. Entity-aware (Dr PL025/Cr AS002 for Companies; Dr LL025/Cr LL010 for LLP; Dr NP008/Cr NC012 for NCE; Dr AE004/Cr AO009 for AOP; Dr TE004/Cr TR007 for Trust). Splits tangible vs intangible. Idempotent — re-posting prompts confirmation and replaces prior DEP entries.
6. **Audit Report template** — conditional rendering (Company always, LLP only if turnover > ₹40L, hidden for others). Opinion-type dropdown swaps in correct paragraph (Unmodified / Qualified / Adverse / Disclaimer). UDIN placeholder added.
7. **Balancing-line skip** — "Current Year Loss / P&L Transfer" rows in synthetic TBs are auto-detected and skipped on import (avoids double-counting since FS engine computes PAT independently).

---

## New Files

| File | Purpose |
|---|---|
| `finstruct/core/annexures.py` | Annexure definitions + `AnnexureData` dataclass + TB tie-out reconciliation logic |
| `finstruct/gui/annexures_view.py` | GUI view for Step 5b — bucket entry with live TB tie-out variance |
| `CHANGELOG_PHASE2.md` | This file |

## Modified Files

| File | Change Summary |
|---|---|
| `core/tb_importer.py` | SubType column detection; `_build_subtype_index()`; `_lookup_subtype_code()` 4-tier matcher; balancing-line skip; account-name fallback |
| `core/notes_engine.py` | `generate_dynamic(doc)` — auto-renumber + remap FSLine.note references; stale refs cleared to None |
| `core/master_db.py` | (unchanged this sprint; reused 265 mapping entries) |
| `data/project_db.py` | Schema v3 — `annexure_rows` table; `delete_dep_adjustments()` for idempotent dep post |
| `data/settings_db.py` | `get/set_annexure_tolerance` — user-configurable variance threshold |
| `export/docx_exporter.py` | `OPINION_PARAGRAPHS` dict; `{{OPINION_PARA}}`, `{{UDIN}}`, `{{FY_END_YEAR}}` placeholders |
| `gui/main_window.py` | Steps reordered (5b Annexures); `_show_reports` conditional on entity/turnover |
| `gui/tb_import_view.py` | SubType role in ColumnMappingDialog; auto-confirm WTB from subtype_hints |
| `gui/mapping_view.py` | "py" added to editable_cols; `_on_cell_change` persists PY to wtb.py_net |
| `gui/annexures_view.py` | (new) |
| `gui/ppe_view.py` | Entity-aware `DEP_CODES`; idempotent post with confirm; tangible/intangible split |
| `gui/report_editor.py` | Opinion-type combobox (audit only); auto-reload on change |
| `gui/export_dialog.py` | Uses `generate_dynamic(doc)` so exported PDF/XLSX have remapped note numbers |

---

## Workflow (Updated 10-Step)

```
1. Entity Setup         →  Company name, FY, paid-up capital, auditor details, opinion type
2. Import TB            →  XLSX/CSV/Tally XML; SubType column auto-maps; balancing line skipped
3. Map Ledgers          →  ML mapper for the unmapped; double-click PY cell to enter PY
4. Review WTB           →  Sanity check the mapped data
5. PPE Register         →  Add assets; click "Post Depreciation" to flow into FS (idempotent)
5b. Custom Annexures    →  TR/TP ageing, share capital, borrowings — with TB tie-out check
6. Generate FS          →  BS, P&L, CF (Schedule III Non-Ind AS)
7. Notes                →  Auto-numbered; empty notes dropped
8. Reports              →  Directors' Report (Co only) + Audit Report (Co + LLP>40L only)
9. Export               →  PDF, XLSX, DOCX (with all auto-renumbered note refs intact)
```

---

## Configurations & Settings

### Annexure Tie-out Tolerance
- Default: ₹10 (soft limit)
- Configurable: Settings panel in Annexures view (top bar) → updates `settings.annexure_tolerance` in global SettingsDB
- Soft: above tolerance, user can override on save with reason logged to audit trail

### Audit Report Opinion Types
- Unmodified (default; most common)
- Qualified (with Basis for Qualified Opinion paragraph)
- Adverse (with Basis for Adverse Opinion paragraph)
- Disclaimer (no opinion expressed)

### Depreciation Account Mapping (per entity)
| Entity | Tangible Dr | Tangible Cr | Intangible Dr | Intangible Cr |
|---|---|---|---|---|
| COMPANY / SEC8 | PL025 | AS002 | PL026 | AS005 |
| LLP | LL025 | LL010 | LL025 | LL011 |
| PROP / PART | NP008 | NC012 | NP008 | NC013 |
| AOP | AE004 | AO009 | AE004 | AO009 |
| TRUST | TE004 | TR007 | TE004 | TR007 |

---

## Synthetic TB Test Results (5 Jun 2026)

| Entity | TB rows | SubType Auto-Mapped | Notes Generated (auto-numbered) |
|---|---|---|---|
| Manufacturing Pvt Ltd | 63 | 47 (75%) | 10 |
| LLP | 17 | 10 (59%) | (workflow tested) |
| Proprietorship | 12 | 6 (50%) | (workflow tested) |
| Partnership | 14 | 7 (50%) | (workflow tested) |

The remaining ledgers are handled by the ML mapper (TF-IDF + SBERT) in Step 3 with confidence-based color coding.

---

## Schema Migrations

| Version | Change | Migration |
|---|---|---|
| v1 → v2 | Added `UNIQUE(raw_tb_id)` to wtb table | Drops duplicates via INSERT OR IGNORE; renames _v2 → wtb |
| v2 → v3 | Added `annexure_rows` table | Additive only — no data loss |

Existing projects auto-migrate on open.

---

## Phase 1 Bug-Fix Summary (carried forward — commit 04b44d3)

12 critical bugs fixed earlier this sprint:
- DB integrity (UNIQUE wtb.raw_tb_id)
- Adjustments flow into FS totals (new `apply_adjustments()`)
- SEC8 uses `_sec8_ie()` with PL codes (was reading AOP AI/AE)
- LLP P&L uses `_llp_pl()` with LL018-LL027 (was reading NP codes)
- CF interest income: PL005 (was PL007 = Profit on Sale)
- Note 22 label correction (Interest/Dividend/Profit on Sale order)
- Note 23 closing stock from AS015 (was hardcoded 0)
- Note 33 EPS auto-calculated from PAT (was hardcoded 0)
- CSV source tag correction
- Tally XML Dr/Cr stripping helper
- Duplicate Alt-p shortcut removed
- _go_notes deduped (was aggregating WTB twice)

---

## Outstanding (Deferred to Next Sprint)

- **CARO 2020 questionnaire** (21 clauses) — to be embedded in audit report annexure
- **CSR Annexure** (Section 135) — separate disclosure for net profit calc + spent/unspent
- **ICFR Annexure** (Section 143(3)(i))
- **AOP/Trust notes build-out** — currently 1–2 stub notes for these entity types
- **Sch II + IT Schedule formatted PDF output** — data exists in PPE register; only PDF templates needed
- **Sample Excel macro adaptation for LLP** — current xlsm is Companies-only

---

## Running the App

```bash
# From repo root:
python -m finstruct._app

# Or build standalone executable:
pyinstaller finstruct.spec
# → dist/FinStruct/FinStruct.exe (Windows)
```

Sample TBs for testing are in this repo at the file paths provided in the test results section.

---

## Sprint Hours: Actual vs Plan

| Block | Plan | Actual |
|---|---|---|
| A. TB Importer (SubType + balancing) | 3h | 2.5h |
| B. PY column (Mapping View + template) | 2h | 0.5h (template already had PY) |
| C. Custom Annexures + tie-out | 4h | 3h |
| D. PPE Dep auto-post | 1h | 1h |
| E. Audit Report template | 2h | 1h |
| F. Auto note numbering | (added) | 1.5h |
| Smoke test all 4 entities | 2h | 1h |
| **TOTAL** | **14h** | **~10.5h** |

Ahead of plan; CARO and remaining annexures can be added in the next short sprint.
