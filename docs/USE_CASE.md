# FinStruct — Use Case Document

**Version:** 1.0 | **Date:** 2026-05-20 | **Author:** CA/CS Developer

---

## 1. Overview

FinStruct is a Windows desktop application that automates the preparation of ICAI/Companies Act–compliant Financial Statements from imported Trial Balance data.

**Primary Users:** Chartered Accountants (CAs) and Company Secretaries (CS) operating in practice or industry.

**Problem Solved:** FS preparation currently takes 8–20 hours per client per year. FinStruct targets ≤ 2 hours (80% reduction) by eliminating manual ledger classification, note computation, and formatting.

---

## 2. Actors

| Actor | Description |
|-------|-------------|
| CA / CS (Primary) | Creates projects, imports TB, reviews mapping, generates and exports FS |
| Article / Staff | May assist with TB import and mapping review under CA supervision |
| System (Auto) | ML engine suggests mappings; rollover engine carries PY figures |

---

## 3. Use Cases

### UC-01: Create New Client Project
**Actor:** CA  
**Flow:**
1. Launch FinStruct → Dashboard → New Project
2. Select entity type (Company / LLP / Prop / Part / AOP / Trust / Sec8)
3. Enter entity master: name, PAN, CIN/LLPIN, address, FY, auditor details
4. System creates per-client SQLite DB
5. Project appears on dashboard

**Entity subtypes:**
- Company → Small Company flag (paid-up ≤ ₹4 Cr, turnover ≤ ₹40 Cr)
- AOP subtype: RWA | Club | AOP_General | BOI
- Trust subtype: Public Charitable | Private Trust

---

### UC-02: Import Trial Balance
**Actor:** CA / Article  
**Precondition:** Project created  
**Flow:**
1. Step 2 → Import TB
2. Select source format: XLSX | CSV | Tally XML
3. System auto-detects column headers (Ledger, Debit, Credit, Group)
4. Preview imported rows with detected columns highlighted
5. Confirm → rows saved to `raw_tb` table
6. System flags unrecognized columns for manual column mapping

**Supported sources:** Tally Prime XML, Zoho Books XLSX, QuickBooks CSV, manual Excel

---

### UC-03: Map Ledgers to ICAI/Schedule III Heads
**Actor:** CA (reviews ML suggestions)  
**Precondition:** TB imported  
**Flow:**
1. System runs ML mapping (TF-IDF + sentence-transformers) on all ledger names
2. Mapping grid displays: Ledger | Suggested Head | Confidence | Source
3. Green = confirmed (confidence ≥ 0.85), Yellow = review (0.65–0.84), Red = unresolved (< 0.65)
4. CA clicks any row to override via hierarchical dropdown
5. Confirmed mappings saved to `learned_mappings` — reused automatically in next FY
6. Optional: Claude API for batch resolution of red-flagged rows (requires API key in settings)

---

### UC-04: Review Working Trial Balance
**Actor:** CA  
**Flow:**
1. Step 4 → WTB View
2. Spreadsheet grid: mapped ledgers grouped by Schedule III head
3. CY net amounts and PY comparative figures
4. Balance check: Total Debit = Total Credit; BS must balance
5. Adjustment entries can be passed directly in the WTB view (Dr/Cr cells)
6. Validation errors shown inline

---

### UC-05: Manage Fixed Assets (PPE)
**Actor:** CA  
**Flow:**
1. Step 5 → PPE Register
2. Enter/import: Asset name, Category (Sch II), Method (SLM/WDV), Opening Gross Block, Additions, Disposals, Opening Accum Dep
3. System calculates: Closing Gross Block, Depreciation for year (SLM/WDV per Sch II useful life), Net Block
4. IT depreciation columns computed separately
5. Post depreciation to WTB as adjustment entry
6. Generate Note 10 (PPE Schedule) automatically

---

### UC-06: Generate Financial Statements
**Actor:** CA  
**Precondition:** All ledgers mapped, WTB balanced  
**Flow:**
1. Step 6 → Generate FS
2. System generates entity-appropriate statements:
   - Company/Sec8: BS (Sch III Part I) + P&L (Sch III Part II)
   - LLP: ICAI LLP format BS + P&L + Partners' Capital
   - Prop/Part: ICAI NCE BS + P&L + Capital Account
   - AOP/Trust: ICAI NCE BS + Income & Expenditure + Receipt & Payment
3. FS Grid opens — editable spreadsheet view with all line items
4. Manual cell overrides are tracked with reason in `fs_overrides`
5. BS balance check auto-runs; discrepancies highlighted

---

### UC-07: Generate Notes to Accounts
**Actor:** CA  
**Flow:**
1. Step 7 → Notes
2. System generates all applicable notes from WTB mapping
3. Each note opens in inline grid editor
4. Notes 1–2 (Accounting Policies) use a template editor — customizable rich text
5. PPE note (Note 10/11) pulled from PPE Register
6. Ageing schedules (Trade Rec / Trade Pay) — CA enters ageing buckets
7. Small Company: mandatory notes reduced automatically (no segment, no cash flow, etc.)

---

### UC-08: Edit Directors Report / Audit Report
**Actor:** CA  
**Flow:**
1. Step 8 → Reports
2. Word-processor editor opens with pre-populated template
3. Placeholders: {{COMPANY_NAME}}, {{FY}}, {{PROFIT}}, {{DIRECTOR_1}} etc. auto-filled
4. CA edits narrative, changes audit opinion (Unmodified / Qualified / Disclaimer)
5. Export as DOCX

---

### UC-09: Export Financial Statements
**Actor:** CA  
**Flow:**
1. Step 9 → Export
2. Choose: PDF (FS only) | XLSX (FS + WTB) | DOCX (Reports) | All
3. PDF: professional print-ready, page-numbered, entity header/footer
4. XLSX: formatted Excel with separate sheets per statement
5. DOCX: Directors Report + Audit Report in a single Word file
6. Saved to user-selected folder; path logged in audit trail

---

### UC-10: Year Rollover
**Actor:** CA  
**Flow:**
1. Dashboard → Rollover to Next FY
2. System creates new project for FY+1
3. Closing balances of CY → Opening balances of PY (comparative figures)
4. Confirmed ledger mappings carried forward (auto-learning)
5. PPE closing block → opening block of new year
6. Entity master data copied (update FY, auditor date fields)

---

## 4. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Performance | FS generation from 200-line TB in < 5 seconds |
| Offline | 100% offline; no internet required (API optional) |
| Security | PII encrypted at rest (Fernet AES-128) |
| Compliance | ICAI NCE formats 2023, Companies Act 2013 Schedule III (amended 2021) |
| Accessibility | Keyboard-navigable (Excel-like shortcuts); high-contrast optional |
| Scalability | Designed for future audit report auto-generation module |
