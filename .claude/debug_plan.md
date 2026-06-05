# FinStruct — Weekend Debug & Completion Plan

## Auditor's Summary (CA Lens)

Like a Balance Sheet that shows Assets ≠ Liabilities, this codebase has **structural errors in financial logic** mixed with **code-quality issues**. The architecture is sound. The data layer is clean. The GUI workflow is complete. But 4 bugs would produce materially wrong financial statements if uncaught. Fix those first — everything else is polish.

---

## CONFIRMED BUGS (Priority-Ordered)

### P0 — Will silently corrupt financial data

#### BUG 1 — `project_db.py`: `upsert_wtb` creates duplicate WTB rows
**File:** `finstruct/data/project_db.py` line 247–254  
**Root cause:** `wtb` table has no `UNIQUE` constraint on `raw_tb_id`. `INSERT OR REPLACE` has nothing to conflict on, so it always INSERTs. If the user re-runs mapping (without re-importing TB), every ledger gets a second row. `aggregate_by_code` then double-counts every amount → FS figures double.  
**Fix:** Add `UNIQUE(raw_tb_id)` to schema + schema migration.

```sql
-- SCHEMA CHANGE NEEDED:
CREATE TABLE IF NOT EXISTS wtb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_tb_id INTEGER UNIQUE REFERENCES raw_tb(id) ON DELETE CASCADE,
    ...
);
```
Also update `upsert_wtb` to use `INSERT OR REPLACE` correctly, or change to `INSERT OR IGNORE` + `UPDATE`.

---

#### BUG 2 — `project_db.py` / `wtb_engine.py`: Adjustment entries ignored in FS aggregation
**File:** `finstruct/data/project_db.py` lines 270–276; `finstruct/core/wtb_engine.py` lines 57–66  
**Root cause:** `sum_by_code()` reads only from `wtb` table. `aggregate_by_code()` processes only WTBLine objects (which come from `wtb`). Adjustment journal entries saved in `adjustments` table never flow into `totals` → adjustments have zero effect on the generated FS.  
**Fix:** In `aggregate_by_code` (or `_build_fs_doc`), query `adjustments` and fold Dr/Cr into the totals dict by mapping_code.

---

### P1 — Material errors in financial statement figures

#### BUG 3 — `fs_engine.py`: NCE BS Fixed Assets shows GROSS not Net Block
**File:** `finstruct/core/fs_engine.py` lines 332–334  
**Root cause:**
```python
fa_gross_cy = self._cy("NC012") + self._cy("NC013")   # ← adds two gross codes
lines.append(_line("I.   Fixed Assets (Net Block)", fa_gross_cy ...))
```
The label says "Net Block" but accumulated depreciation is never deducted. Compare with Company BS (lines 194–201) which correctly does `ppe_net = ppe_gross - ppe_dep + ppe_cwip`.  
Need to verify NC012/NC013 definitions in master_db (NC012 = Tangible Gross, NC013 = Intangible — there's likely an NC012_dep / NC013_dep missing).  
**Same bug in LLP BS** (line 410): `fa_cy = self._cy("LL010") + self._cy("LL011")`.  
**Fix:** Add accumulated depreciation codes to master_db for NCE/LLP and deduct them explicitly in the engine.

---

#### BUG 4 — `notes_engine.py`: Note 23 (Cost of Materials) closing stock hardcoded to zero
**File:** `finstruct/core/notes_engine.py` lines 352–360  
**Root cause:**
```python
_dl("Less: Closing Stock of Raw Materials", 0, 0),   # ← hardcoded 0
_tl("Cost of Materials Consumed", self._cy("PL010")+self._cy("PL011"), ...)
# ↑ total also ignores closing stock — formula is Opening + Purchases (wrong)
```
Correct formula: Cost of Materials = Opening Stock (PL010) + Purchases (PL011) − Closing Stock (AS015).  
The total line must deduct AS015.  
**Fix:** Replace the hardcoded 0 with `self._cy("AS015")` and fix the total.

---

#### BUG 5 — `fs_engine.py`: Dead variable in Cash Flow Statement causes reconciliation gap
**File:** `finstruct/core/fs_engine.py` lines 745–748  
**Root cause:**
```python
cash_op_cy = self._sum_cy(["AS023","AS024","AS025","AS026"])  # ← NEVER USED
cash_cl_cy = self._cy("AS023") + ... 
cash_op_val = self._sum_py(["AS023","AS024","AS025","AS026"])
```
`cash_op_cy` is assigned but only `cash_op_val` is used. This is harmless to the reconciliation check on line 751 (`net_cf_cy - (cash_cl_cy - cash_op_val)`) but the logic should use `self._sum_py` for opening which is correct. The dead variable should be removed to avoid confusion.  
**Fix:** Delete the `cash_op_cy` line (line 745).

---

### P2 — Incomplete features that will confuse users

#### BUG 6 — NCE / AOP / Trust notes are stub placeholders
**File:** `finstruct/core/notes_engine.py` lines 520–559  
`_nce_notes()` returns 2 notes (Capital Account + Accounting Policies only — no numeric content for any code).  
`_aop_notes()` returns 1 note. `_trust_notes()` returns 1 note.  
Users of PROP / PART / LLP / AOP / TRUST entities get essentially blank notes.  
**Fix:** Build out notes using the NC/LL/AO/TI/TE codes matching the pattern in `_company_notes()`.

---

#### BUG 7 — `notes_engine.py`: Note 33 (EPS) has dead variables
**File:** `finstruct/core/notes_engine.py` lines 480–491  
```python
pat_cy = self._cy("EL007")   # ← assigned, never used
tax_cy = self._cy("PL040") + self._cy("PL041")  # ← assigned, never used
rev_cy = self._sum_cy(["PL001","PL002","PL003"]) # ← assigned, never used
```
EPS note always shows zeros for all lines. The PAT should be derived from the P&L engine result, not hardcoded from EL007 (retained earnings).  
**Fix:** Wire EPS calculation using actual PAT from P&L totals.

---

### P3 — Code quality / minor errors

#### BUG 8 — `main_window.py`: Duplicate keyboard shortcut (Alt-b and Alt-p both go to step 5)
**File:** `finstruct/gui/main_window.py` lines 464–465  
```python
root.bind("<Alt-b>", lambda e: self._go_step(5))   # BS step
root.bind("<Alt-p>", lambda e: self._go_step(5))   # also BS step — copy-paste error
```
Alt-p should likely navigate to P&L/step 5 (same view) or intended as a separate shortcut. One of these should be removed or corrected.  
**Fix:** Remove duplicate or assign Alt-p to a different action.

---

#### BUG 9 — `main_window.py`: `_go_notes` duplicates WTB aggregation
**File:** `finstruct/gui/main_window.py` lines 363–386  
`_go_notes()` calls `_build_fs_doc()` (which already aggregates WTB), then re-fetches and re-aggregates WTB again to build `totals`. The second aggregation is redundant.  
**Fix:** Have `_build_fs_doc()` return `totals` as a third return value, reuse it in `_go_notes`.

---

#### BUG 10 — `tb_importer.py`: Source tag hardcoded to "XLSX" for CSV imports
**File:** `finstruct/core/tb_importer.py` line 310  
```python
result.rows.append({... "source": "XLSX"})  # ← wrong for CSV files
```
`_parse_rows` is called by both `import_xlsx` and `import_csv` but always tags source as "XLSX".  
**Fix:** Pass `source` as a parameter to `_parse_rows`.

---

#### BUG 11 — `tb_importer.py`: Overlong lines in Tally XML parser
**File:** `finstruct/core/tb_importer.py` lines 246 and 253  
Both are 115+ character lines doing repetitive string replacements. Readable but violates code style.  
```python
net = _to_float(cl_bal_txt.replace("Dr.", "").replace("Cr.", "").replace("Dr", "").replace("CR", "").replace("Cr", ""))
```
**Fix:** Extract a helper `_strip_dr_cr(s)` for the repetitive replace chain.

---

#### BUG 12 — `fs_engine.py`: SEC8 Income & Expenditure uses AOP codes
**File:** `finstruct/core/fs_engine.py` lines 98–103  
SEC8 companies use Company BS (EL/AS codes) for the balance sheet, but `_aop_ie()` for the I&E — which reads AOP codes (AI001-AI003, AE001-AE015). If a Section 8 company maps its ledgers to company codes (PL series), the I&E will show all zeros.  
**Confirm/fix:** Either create a separate `_sec8_ie()` that reads PL codes, or document that SEC8 entities must map to AO/AI/AE codes.

---

## IMPLEMENTATION PLAN (Weekend Sprint)

### Saturday Morning (4 hrs): P0 + P1 Fixes

| # | Task | File | Est. |
|---|------|------|------|
| 1 | Add UNIQUE(raw_tb_id) + migration in schema | `project_db.py` | 30m |
| 2 | Include adjustments in FS aggregation | `project_db.py` / `wtb_engine.py` | 45m |
| 3 | Fix NCE/LLP Net Block calculation | `fs_engine.py` + `master_db.py` | 60m |
| 4 | Fix Note 23 closing stock formula | `notes_engine.py` | 20m |
| 5 | Remove dead `cash_op_cy` variable | `fs_engine.py` | 5m |

### Saturday Afternoon (3 hrs): P2 Fixes

| # | Task | File | Est. |
|---|------|------|------|
| 6 | Build out NCE notes (LLP/PROP/PART at minimum) | `notes_engine.py` | 90m |
| 7 | Fix EPS Note 33 wiring | `notes_engine.py` | 30m |
| 8 | Fix SEC8 I&E code conflict | `fs_engine.py` | 30m |

### Saturday Evening (2 hrs): P3 + Build

| # | Task | File | Est. |
|---|------|------|------|
| 9 | Fix keyboard shortcut duplicate | `main_window.py` | 5m |
| 10 | Fix _go_notes double computation | `main_window.py` | 20m |
| 11 | Fix CSV source tag + long lines | `tb_importer.py` | 20m |
| 12 | PyInstaller build + smoke test | `finstruct.spec` | 45m |

### Sunday (Full day): Testing

Test matrix per entity type: COMPANY → LLP → PROP → AOP → TRUST

For each:
- Import sample TB (use FinStruct template)
- Verify BS balances (CY diff = 0)
- Verify P&L / I&E totals
- Verify Note 12 PPE (with actual asset entries)
- Export PDF — check all pages render
- Export XLSX — check formulas

---

## QUESTIONS FOR YOU (CA Review)

Before we start coding, please confirm:

1. **NCE Fixed Assets codes**: Do NC012 and NC013 represent (a) Tangible + Intangible gross, or (b) Tangible gross + Accumulated depreciation? This changes the bug severity.

2. **SEC8 entity**: Should Section 8 companies map their income/expense ledgers to AO/AI/AE codes (like an AOP) or to PL codes (like a company)? This determines whether we need a new `_sec8_ie()` method.

3. **Adjustments in FS**: Currently adjustments in the `adjustments` table don't affect the generated FS. Is that by design (adjustments are informational/workpaper only), or should they flow into totals?

4. **EPS Note**: Should Note 33 auto-calculate from P&L PAT + share capital data, or remain a manual-fill placeholder?

5. **Rounding divisor**: The `divisor` field exists for ₹ Lakhs / Crores presentation. Is this tested end-to-end through to export? Any rounding issues seen?

---

## FILES NOT TO TOUCH (Working Correctly)

- `encryption.py` — solid
- `ppe_engine.py` — correct depreciation formulas  
- `rollover.py` — clean
- `settings_db.py` — clean
- `theme.py` — clean
- `pdf_exporter.py`, `xlsx_exporter.py`, `docx_exporter.py` — functional
- `company_master.py`, `mapping_view.py`, `wtb_view.py`, `ppe_view.py` — GUI working

---

## OVERLONG FILES (Refactor After Deployment)

Post-weekend cleanup (do NOT touch now):
- `fs_engine.py` (757 lines) — extract entity-specific builders into separate files
- `notes_engine.py` (559 lines) — same
- `pdf_exporter.py` (407 lines) — acceptable for export

The 9-step GUI files are all appropriately sized. No changes needed there.
