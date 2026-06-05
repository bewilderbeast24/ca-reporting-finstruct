# FinStruct — Phase 2 Build Plan (Sch III Company First)

## ✅ Phase 1 COMPLETED & PUSHED (commit 04b44d3)
12 bugs fixed across 7 files: DB integrity (UNIQUE wtb.raw_tb_id), adjustments flow into FS, SEC8 I&E, LLP P&L (LL018-LL027), CF interest income code, Note 22/23 fixes, EPS auto-calc.

---

## Phase 2 — Feature Build (Weekend Sprint)

### Confirmed Scope (from your answers)

| # | Decision | Approach |
|---|---|---|
| 1 | TB SubType column | Primary mapping signal — auto-confirm at confidence 1.0 when SubType matches Sch III sub-heading |
| 2 | PY figures | Three paths: Mapping View editable col (primary, mirrors xlsm Col O) + Excel template PY Net col + Rollover for next year |
| 3 | Custom Notes/Annexures | Template entry with TB tie-out check; carries forward via rollover |
| 4 | Depreciation post | User-triggered "Post Depreciation" button (handles both pre/post-adjusted TBs) |
| 5 | Audit Report | Template + placeholder substitution for Company + LLP(>40L turnover) only; CARO later |
| 6 | PPE Register | Manual entry retained; provide Excel template for bulk import |
| 7 | Balancing line | Auto-detect & skip "Current Year Loss / P&L Transfer" rows on import |

---

## A. TB Importer enhancements (3 hours)

**File:** `finstruct/core/tb_importer.py`

- Detect synthetic-TB layout: `AccountCode | AccountName | AccountType | SubType | Debit | Credit | Entity | Notes`
- Use **SubType** as primary mapping signal — match against `MASTER.sub_heading` (case-insensitive); on match, save WTB row with `confidence=1.0, source="SUBTYPE"`
- Add `_skip_balancing_line()` — drop rows whose ledger name matches `r"^(current year )?(loss|profit)\s*(transfer)?|P&L\s*Transfer"`
- Add optional `PY Net` column to FinStruct template generator
- Tally XML support remains unchanged

**Acceptance:** All 4 synthetic TBs auto-map ≥90% of ledgers without user touching the mapping grid.

---

## B. Previous Year (PY) entry (2 hours)

**Files:** `finstruct/gui/mapping_view.py`, `finstruct/core/tb_template_generator.py`

- Add editable **PY Net** column to the Mapping View grid (between confidence and is_confirmed)
- On cell-edit, save to `wtb.py_net` (column already exists)
- Excel template: add Col E "PY Net (optional)" — imported into `wtb.py_net` if present
- Verify existing `rollover.py` correctly carries CY → PY for BS items only (not P&L)

**Acceptance:** User can paste a PY column into the template, or type per-row in the GUI, or rollover from prior year — all three populate the same `wtb.py_net` field.

---

## C. Custom Notes / Annexures (4 hours)

**New file:** `finstruct/gui/annexures_view.py`
**New core file:** `finstruct/core/annexures.py`

New menu item between Step 5 (PPE) and Step 6 (Generate FS): **"5b. Custom Annexures"**.

Four annexure templates, each with **TB tie-out check** (your insight):

| Annexure | TB tie-out source | Tolerance |
|---|---|---|
| Trade Receivables ageing | `AS020 + AS021 - AS022` | ₹1 |
| Trade Payables ageing (MSME + Others) | `EL025 + EL026` | ₹1 |
| Share Capital working | `EL001 + EL002` | ₹1 |
| Borrowings disclosure | `EL010-EL015 + EL020-EL024` | ₹1 |

**UX flow per annexure:**
1. Form opens prefilled with TB total (read-only header row)
2. User enters bucket-wise breakup
3. Live recalc shows total at bottom + red/green pill: ✓ tallies / ✗ differs by ₹X
4. Save disabled until tie-out is green (with optional "Save with variance" override + reason)
5. Saved data lives in `note_data` table (already exists); rollover carries it forward

**Excel template export per annexure** for offline bulk entry → re-import.

**Acceptance:** Trade Payables annexure for Manufacturing TB shows total ₹2,00,00,000 (EL025=60L MSME + EL026=140L Others), user enters ageing buckets, tie-out passes.

---

## D. PPE Depreciation Auto-Post (1 hour)

**File:** `finstruct/gui/ppe_view.py`, `finstruct/core/ppe_engine.py`

- Add **"Post Depreciation Entry"** button in PPE View (matches xlsm "Pass Adj Entry")
- On click: for each PPE asset, create adjustments:
  - Dr PL025 (Tangible) or PL026 (Intangible) — depreciation charge
  - Cr AS002 (Tangible) or AS005 (Intangible) — accumulated dep
- Idempotent: each adj_id = `f"DEP_{asset_id}_{fy}"`. Re-posting REPLACES not adds.
- Status indicator: "Depreciation posted (X assets, ₹Y total)" or "Not posted"
- **If TB already includes depreciation, user simply doesn't click the button** — your 99% small-company scenario is handled by NOT requiring this step.

**Acceptance:** Posting dep on a fresh PPE register adds adjustments visible in WTB; total dep matches `summarize_ppe()` total; clicking again does not double-add.

---

## E. Audit Report Template (2 hours)

**Files:** `finstruct/gui/report_editor.py`, `finstruct/export/docx_exporter.py`

Replace freeform editor with template-driven form for **Company always + LLP if turnover > ₹40 lakhs**. Other entity types: hidden.

**Template sections (ICAI SA 700 format):**
1. To the Members of [Entity]
2. Report on the Audit of the Financial Statements
3. **Opinion** — Unmodified / Qualified / Adverse / Disclaimer (dropdown)
4. Basis for Opinion
5. Management's Responsibility
6. Auditor's Responsibility
7. Report on Other Legal and Regulatory Requirements

**Placeholders auto-substituted:**
- `{entity_name}`, `{fy}`, `{audit_period_end}`
- `{auditor_name}`, `{firm_name}`, `{firm_reg_no}`, `{membership_no}`, `{udin}`
- `{place_signing}`, `{date_signing}`
- `{opinion_type}` drives section 3 body
- CARO 2020 placeholder: `[CARO 2020 Annexure — see separate annexure]` (built later)

**Acceptance:** Generate DOCX for Manufacturing Pvt Ltd — auditor variables filled from `entity_master`, opinion section reads cleanly for "Unmodified" selection.

---

## F. End-to-End Smoke Test (2 hours)

For each of 4 synthetic TBs (Manufacturing, LLP, Proprietor, Partnership):
1. New project → enter basic data
2. Import TB → verify SubType auto-mapping ≥90%
3. Enter PY figures (use Manufacturing CY as proxy PY for testing)
4. PPE register: add 4 assets, click Post Depreciation
5. Annexures: fill Trade Receivables/Payables ageing — verify tie-out
6. Generate FS → confirm BS balances (CY diff ≤ ₹1)
7. Export PDF + XLSX

**Stop-ship test:** Manufacturing Pvt Ltd BS must balance to zero with all 4 annexures tied out.

---

## Time & Sequencing

| Block | Hours | Day |
|---|---|---|
| A. TB Importer (SubType + balancing skip) | 3 | Sat AM |
| B. PY column wiring | 2 | Sat AM |
| C. Annexures + tie-out (the big one) | 4 | Sat PM |
| D. Dep auto-post button | 1 | Sat eve |
| E. Audit Report template | 2 | Sun AM |
| F. Smoke test all 4 entities | 2 | Sun PM |
| PyInstaller build + sanity launch | 1 | Sun PM |
| **TOTAL** | **15** | **Sat+Sun** |

---

## Deferred (Post-Weekend)

- CARO 2020 questionnaire (21 clauses) — large feature, separate sprint
- Auto note numbering by sub-heading (xlsm dynamic numbering) — nice-to-have; current fixed numbers work
- ICFR Annexure (Sec 143(3)(i))
- Sch II + IT Schedule formatted printouts (data exists in `ppe` table; just needs PDF templates)
- AOP/Trust notes completion (currently 1-2 stub notes — your guidance: defer until Co/LLP/NCE are solid)

---

## Open Question for You

The **annexure tie-out tolerance** — your insight on tying back to TB is a CA gold standard. Should I default to ₹1 hard tolerance (refuse save above that), or a ₹100 / 0.1% soft tolerance with red flag? Small rounding diffs from Lakhs/Crores divisor can produce ₹3-5 variances that aren't real errors. Suggest ₹100 soft default with user-configurable threshold in Settings.
