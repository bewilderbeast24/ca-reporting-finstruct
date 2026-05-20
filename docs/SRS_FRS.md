# FinStruct — Software & Functional Requirements Specification

**Version:** 1.0 | **Date:** 2026-05-20

---

## Part A — Software Requirements (SRS)

### SRS-01: Platform
- Windows 10/11 x64
- Python 3.11+ runtime bundled via PyInstaller (standalone .exe, no Python install needed)
- Single-folder distribution: `dist/FinStruct/FinStruct.exe`

### SRS-02: Storage
- Per-client SQLite database at user-selected path (default: `%USERPROFILE%\FinStruct\projects\`)
- Global app settings: `%APPDATA%\FinStruct\settings.db`
- ML model cache: `%APPDATA%\FinStruct\models\`
- All PII fields encrypted using Fernet (AES-128-CBC + HMAC-SHA256)

### SRS-03: External Dependencies (bundled)
```
tkinter          — GUI (ships with Python)
sqlite3          — DB (ships with Python)
cryptography     — Fernet encryption
openpyxl         — XLSX import/export
reportlab        — PDF generation
python-docx      — DOCX export
scikit-learn     — TF-IDF ML mapping
sentence-transformers — Semantic ML mapping
anthropic        — Optional Claude API (lazy import)
lxml             — Tally XML parsing
```

### SRS-04: Performance
- TB import (200 rows): < 2 seconds
- ML mapping (200 ledgers): < 10 seconds (TF-IDF); < 30 seconds (sentence-transformers)
- FS generation (full set, all notes): < 5 seconds
- PDF export (50 pages): < 15 seconds

### SRS-05: Security
- No outbound network requests unless Claude API enabled by user
- Audit log for every material action (create, import, generate, export, finalize)
- Project lock state prevents further edits after finalization
- No hardcoded credentials anywhere in codebase

### SRS-06: Scalability Hooks
- `report_engine` module reserved for future Directors Report / Audit Report auto-generation
- `validator` module extensible for CARO/other regulatory checklists
- Entity type enum extensible (e.g., future: Cooperative Society, Nidhi)

---

## Part B — Functional Requirements (FRS)

### Module 1: Project Management

| ID | Requirement |
|----|-------------|
| F1.1 | Create project: entity type, subtype, FY, entity master fields |
| F1.2 | Open existing project from dashboard (recent projects list) |
| F1.3 | Duplicate project (same entity, new FY) |
| F1.4 | Rollover: create next-FY project with PY figures carried forward |
| F1.5 | Delete project with confirmation (hard delete, no recycle) |
| F1.6 | Project lock/unlock (locked = read-only, no edits) |
| F1.7 | Audit trail: all actions timestamped with user-visible log |

### Module 2: Entity Master

| ID | Requirement |
|----|-------------|
| F2.1 | Company: Name, CIN (21 chars validated), Registered Office, FY, Incorporation Date |
| F2.2 | Company: Directors (min 2) with DIN (8 chars), Designation |
| F2.3 | Company: CFO Name, CS Name + Membership No |
| F2.4 | Company: Small Company flag — auto-suggest based on Capital/Turnover input |
| F2.5 | LLP: LLPIN, Partners (name, contribution %, designation) |
| F2.6 | Partnership: Partners (name, profit-sharing ratio, capital) |
| F2.7 | Proprietorship: Proprietor name, PAN |
| F2.8 | AOP/Trust: Registration No, Governing Body members (President, Secretary, Treasurer) |
| F2.9 | Trust: Trust Deed date, Objects clause (text) |
| F2.10 | Auditor: Firm name, FRN (6 chars + suffix), Partner name, MRN, signing date/place |
| F2.11 | SMTP presets not needed — this is a standalone FS tool |

### Module 3: Trial Balance Import

| ID | Requirement |
|----|-------------|
| F3.1 | Import XLSX: auto-detect header row, map columns (ledger, group, opening, debit, credit, closing) |
| F3.2 | Import CSV: comma/tab/semicolon delimiter auto-detect |
| F3.3 | Import Tally XML: parse `<LEDGER>` elements, extract `CLOSINGBALANCE`, `PARENT` group |
| F3.4 | Column mapping UI: user confirms or overrides detected column assignments |
| F3.5 | Duplicate ledger detection: warn if same ledger name appears twice |
| F3.6 | PY figures import: separate import of prior year TB or manual entry column |
| F3.7 | Raw TB stored verbatim; original values never mutated |
| F3.8 | Import validation: debit total ≠ credit total → warning (not blocker) |

### Module 4: ML Mapping Engine

| ID | Requirement |
|----|-------------|
| F4.1 | Step 1: Exact match against `learned_mappings` table (same entity type, same FY or prior) |
| F4.2 | Step 2: TF-IDF cosine similarity against `mapping_master.lookup_name` |
| F4.3 | Step 3: Sentence-transformer embedding similarity (bundled model) |
| F4.4 | Step 4: Claude API batch (optional, user-enabled, requires API key) |
| F4.5 | Confidence display: ≥ 0.85 = Green auto-confirmed; 0.65–0.84 = Yellow review; < 0.65 = Red manual |
| F4.6 | Mapping grid: Ledger | Mapped Head | Note Ref | Confidence | Source | Override |
| F4.7 | Override via hierarchical dropdown: Group → Heading → Sub-Heading |
| F4.8 | Confirmed mapping saved to `learned_mappings` with entity_type tag |
| F4.9 | Batch confirm: select multiple yellow rows, confirm all |
| F4.10 | Export unmapped list to XLSX for offline review |

### Module 5: Working Trial Balance

| ID | Requirement |
|----|-------------|
| F5.1 | WTB computed: CY net = (Debit − Credit) per standard sign convention per head |
| F5.2 | PY figures: from rollover or manual PY TB import |
| F5.3 | Adjustment entries: inline Dr/Cr entry with narration; posted to `adjustments` table |
| F5.4 | WTB grid: sortable by Group, Heading; filterable by BS/PL tag |
| F5.5 | Balance validation: Total Assets = Total Equity + Liabilities (tolerance: ₹1) |
| F5.6 | P&L tie-out: Net Profit in P&L = movement in Retained Earnings in BS |
| F5.7 | All-mapped check: no row allowed in FS generation with NULL mapping_code |

### Module 6: Financial Statement Generation

#### 6A — Company (Schedule III)

| ID | Requirement |
|----|-------------|
| F6A.1 | Balance Sheet: Schedule III Part I format — Equity & Liabilities + Assets |
| F6A.2 | P&L: Schedule III Part II — Revenue, Other Income, Expenses, Tax, EPS |
| F6A.3 | Cash Flow: Indirect method (optional for small company) |
| F6A.4 | Small Company: suppress Cash Flow, segment, EPS; reduce note disclosures |
| F6A.5 | All amounts: configurable rounding (₹, Thousands, Lakhs, Crores) |
| F6A.6 | Comparative figures (PY) in all statements |

#### 6B — LLP

| ID | Requirement |
|----|-------------|
| F6B.1 | Balance Sheet: ICAI LLP format — Partners' Capital + Liabilities + Assets |
| F6B.2 | P&L: Revenue, Expenses, Net Profit, Appropriation to Partners |
| F6B.3 | Partners' Capital Account Schedule per partner |

#### 6C — Proprietorship / Partnership

| ID | Requirement |
|----|-------------|
| F6C.1 | BS: ICAI NCE format — Capital + Liabilities + Assets |
| F6C.2 | P&L: Trading A/c + P&L A/c |
| F6C.3 | Partnership: separate Capital & Current Account per partner |

#### 6D — AOP / RWA / BOI

| ID | Requirement |
|----|-------------|
| F6D.1 | BS: Members' Fund + Earmarked Funds + Loans + Current Liabilities + Assets |
| F6D.2 | Income & Expenditure Account |
| F6D.3 | Receipt & Payment Account |
| F6D.4 | Corpus Fund schedule |

#### 6E — Public Charitable Trust / Section 8

| ID | Requirement |
|----|-------------|
| F6E.1 | BS: Corpus + Liabilities + Assets (ICAI NCE NPO format) |
| F6E.2 | Income & Expenditure Account |
| F6E.3 | Receipt & Payment Account |
| F6E.4 | FCRA compliance fields (if applicable) |
| F6E.5 | Section 8: Companies Act FS format (modified Sch III) with I&E instead of P&L |

### Module 7: Notes to Accounts

| ID | Requirement |
|----|-------------|
| F7.1 | Notes 1–2: Accounting Policies (rich text template, editable) |
| F7.2 | Notes 3–9: Share Capital, Reserves, Borrowings, Provisions, Trade Payables, Other Liabilities |
| F7.3 | Notes 10–18: PPE, Investments, Loans, Current Assets, Inventories, Trade Receivables, Cash |
| F7.4 | Notes 19–26: Revenue, Other Income, COGS, Employee Cost, Finance Cost, Depreciation, Other Expenses |
| F7.5 | Notes 27–28: Earnings per Share, Related Party Disclosures |
| F7.6 | Ageing schedules: Trade Receivables (0-30, 31-60, 61-90, 91-180, >180, >1yr) |
| F7.7 | Trade Payables ageing: MSME vs Others |
| F7.8 | Deferred Tax calc table |
| F7.9 | Small Company: only mandatory notes generated |
| F7.10 | Note numbers configurable (reorder if needed) |

### Module 8: PPE Register

| ID | Requirement |
|----|-------------|
| F8.1 | Asset grid: Description, Category, Method, Useful Life |
| F8.2 | Gross Block: Opening, Additions, Disposals, Closing |
| F8.3 | Depreciation: Opening, Charge (auto-calculated per SLM/WDV + Sch II life), Closing |
| F8.4 | Net Block: CY and PY |
| F8.5 | IT Depreciation: WDV block per IT Act, half-year convention |
| F8.6 | Post depreciation to WTB as adjustment entry |
| F8.7 | Import assets from XLSX template |

### Module 9: Export

| ID | Requirement |
|----|-------------|
| F9.1 | PDF: all statements + notes in one file; page headers/footers; page numbering |
| F9.2 | XLSX: one sheet per statement; formatted with borders, fonts |
| F9.3 | DOCX: Directors Report + Audit Report with filled placeholders |
| F9.4 | Export folder: user selects; defaults to Desktop |
| F9.5 | File naming: `{EntityName}_{FY}_FS.pdf` etc. |
| F9.6 | Watermark: "DRAFT" stamp until project finalized |

### Module 10: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Project |
| Ctrl+O | Open Project |
| Ctrl+S | Save current state |
| Ctrl+Z / Ctrl+Y | Undo / Redo (mapping grid) |
| F1 | Help |
| F2 | Edit selected cell (mapping/WTB grid) |
| F5 | Generate FS (all statements) |
| F9 | Validate (balance check + mapping completeness) |
| F10 | Generate Notes |
| F12 | Export to PDF |
| Alt+B | Go to Balance Sheet |
| Alt+P | Go to P&L / I&E |
| Alt+N | Go to Notes |
| Alt+M | Go to Mapping Grid |
| Alt+W | Go to WTB |
| Alt+E | Export dialog |
| Alt+A | Go to PPE Register |
| Tab / Shift+Tab | Navigate cells in grid |
| Enter | Confirm cell edit |
| Escape | Cancel cell edit |
| Ctrl+Home | Go to first row |
| Ctrl+End | Go to last row |
| Ctrl+F | Find in current grid |
