# FinStruct — Design Document

**Version:** 1.0 | **Date:** 2026-05-20

---

## 1. Architecture Overview

```
FinStruct (Windows .exe)
├── GUI Layer (Tkinter/ttk)         ← User interaction
├── Core Layer (Pure Python)        ← Business logic, no GUI dependency
├── Data Layer (SQLite)             ← Per-client encrypted DB
└── Export Layer (ReportLab/openpyxl/python-docx)
```

**Design principles:**
- Core layer has zero GUI imports — testable standalone
- GUI calls Core via plain Python functions (no events/signals)
- All DB access goes through `project_db.py` only
- PII fields encrypted before write, decrypted after read

---

## 2. Module Dependency Graph

```
main.py
  └── gui/main_window.py
        ├── gui/dashboard.py
        ├── gui/company_master.py
        ├── gui/tb_import_view.py  ──→ core/tb_importer.py
        ├── gui/mapping_view.py    ──→ core/mapper.py
        ├── gui/wtb_view.py        ──→ core/wtb_engine.py
        ├── gui/fs_grid_view.py    ──→ core/fs_engine.py
        ├── gui/notes_editor.py    ──→ core/notes_engine.py
        ├── gui/ppe_view.py        ──→ core/ppe_engine.py
        ├── gui/report_editor.py
        └── gui/export_dialog.py   ──→ export/{pdf,xlsx,docx}_exporter.py

core/master_db.py   ← Schedule III + ICAI NCE data (static, no DB)
core/entity_types.py
core/validator.py
core/rollover.py
data/project_db.py  ← SQLite CRUD
data/encryption.py  ← Fernet
```

---

## 3. Database Schema

### Global Settings DB (`%APPDATA%\FinStruct\settings.db`)

```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
-- Keys: theme, claude_api_key (encrypted), default_export_path,
--       rounding_default, last_project_path

CREATE TABLE recent_projects (
  path TEXT PRIMARY KEY,
  entity_name TEXT,
  entity_type TEXT,
  fy TEXT,
  last_opened TEXT
);

CREATE TABLE learned_mappings (
  ledger_name TEXT,
  entity_type TEXT,
  mapping_code TEXT,
  confirmed_count INTEGER DEFAULT 1,
  PRIMARY KEY (ledger_name, entity_type)
);
```

### Per-Client Project DB (`*.finstruct`)

```sql
CREATE TABLE project_meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
-- Keys: entity_type, entity_subtype, financial_year, created_at,
--       updated_at, is_locked, is_finalized, rounding_divisor

CREATE TABLE entity_master (
  key TEXT PRIMARY KEY,
  value TEXT  -- encrypted for: pan, cin, address, director names/DIN
);

CREATE TABLE raw_tb (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ledger_name TEXT NOT NULL,
  group_name TEXT,
  cy_debit REAL DEFAULT 0,
  cy_credit REAL DEFAULT 0,
  cy_net REAL DEFAULT 0,  -- closing = debit - credit (sign per ledger nature)
  py_net REAL DEFAULT 0,
  source TEXT             -- 'XLSX'|'CSV'|'XML'|'MANUAL'
);

CREATE TABLE mapping_master (
  code TEXT PRIMARY KEY,
  entity_types TEXT,      -- JSON list: ["COMPANY","SEC8"] or ["ALL"]
  group_name TEXT,
  heading TEXT,
  sub_heading TEXT,
  fs_tag TEXT,            -- 'BS'|'PL'|'IE'|'RP'
  sign_convention TEXT,   -- 'DR_POSITIVE'|'CR_POSITIVE'
  small_co_exempt INTEGER DEFAULT 0,
  lookup_name TEXT,       -- full hierarchical label for ML
  note_number INTEGER
);

CREATE TABLE wtb (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_tb_id INTEGER REFERENCES raw_tb(id),
  mapping_code TEXT REFERENCES mapping_master(code),
  confidence REAL,
  confidence_source TEXT,  -- 'EXACT'|'LEARNED'|'TFIDF'|'SBERT'|'API'|'MANUAL'
  cy_net REAL DEFAULT 0,
  py_net REAL DEFAULT 0,
  is_confirmed INTEGER DEFAULT 0
);

CREATE TABLE adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  adj_id TEXT UNIQUE,      -- 'AJE-001' etc.
  ledger_name TEXT,
  mapping_code TEXT,
  dr_amount REAL DEFAULT 0,
  cr_amount REAL DEFAULT 0,
  narration TEXT,
  created_at TEXT
);

CREATE TABLE ppe (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_name TEXT NOT NULL,
  category TEXT,
  method TEXT DEFAULT 'SLM',
  useful_life_yrs INTEGER,
  gross_op REAL DEFAULT 0,
  additions REAL DEFAULT 0,
  disposals REAL DEFAULT 0,
  gross_cl REAL GENERATED ALWAYS AS (gross_op + additions - disposals) VIRTUAL,
  dep_op REAL DEFAULT 0,
  dep_charge REAL DEFAULT 0,
  dep_disposal REAL DEFAULT 0,
  dep_cl REAL GENERATED ALWAYS AS (dep_op + dep_charge - dep_disposal) VIRTUAL,
  nbv_cy REAL GENERATED ALWAYS AS (gross_op + additions - disposals - dep_op - dep_charge + dep_disposal) VIRTUAL,
  nbv_py REAL DEFAULT 0,
  it_wdv_op REAL DEFAULT 0,
  it_rate REAL DEFAULT 15,
  it_dep REAL DEFAULT 0,
  it_wdv_cl REAL DEFAULT 0
);

CREATE TABLE fs_overrides (
  section TEXT,           -- 'BS'|'PL'|'IE'|'NOTE_10' etc.
  line_code TEXT,
  cy_value REAL,
  py_value REAL,
  override_reason TEXT,
  PRIMARY KEY (section, line_code)
);

CREATE TABLE note_data (
  note_no INTEGER,
  sequence INTEGER,
  label TEXT,
  cy_value REAL DEFAULT 0,
  py_value REAL DEFAULT 0,
  row_type TEXT DEFAULT 'DATA',  -- 'DATA'|'SUBTOTAL'|'TOTAL'|'HEADER'|'TEXT'
  PRIMARY KEY (note_no, sequence)
);

CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT DEFAULT (datetime('now','localtime')),
  action TEXT,
  detail TEXT
);
```

---

## 4. UI Layout (ASCII Wireframe)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [FinStruct Logo]  FinStruct v1.0    [FY: 2024-25] [Entity: XYZ Ltd] │
│ File  Project  View  Generate  Export  Tools  Help                   │
├──────────────┬──────────────────────────────────────────────────────┤
│ STEPS        │                                                       │
│ ─────────    │  ┌─── MAPPING GRID ──────────────────────────────┐   │
│ ✅ 1. Entity │  │ Ledger Name    │ Mapped Head    │ Conf │ Src   │   │
│ ✅ 2. Import │  ├────────────────┼────────────────┼──────┼───── │   │
│ ▶ 3. Mapping │  │ Cash in Hand   │ Cash & Bank    │ 0.98 │ LRND │   │
│ ○ 4. WTB     │  │ SBI OD A/c    │ Short Borr...  │ 0.82 │ TFIDF│   │
│ ○ 5. PPE     │  │ Misc Expenses │ ─ Select ─     │ 0.44 │ RED  │   │
│ ○ 6. FS      │  ├────────────────┴────────────────┴──────┴──────┤   │
│ ○ 7. Notes   │  │ 187 mapped ✅  11 review ⚠  2 unresolved 🔴   │   │
│ ○ 8. Reports │  └────────────────────────────────────────────────┘   │
│ ○ 9. Export  │                                                       │
│              │  [F9 Validate]  [F5 Generate FS]  [F12 Export PDF]    │
│ ─────────    │                                                       │
│ Status:      │  Status Bar: ✅ 200 ledgers imported | ⚠ 2 unmapped  │
│ 200 ledgers  │                                                       │
└──────────────┴──────────────────────────────────────────────────────┘
```

---

## 5. Theme Specification

```python
THEME = {
    # MS Office Blue palette
    'primary':        '#0078D4',   # Office blue (accent buttons, headers)
    'primary_dark':   '#106EBE',   # Hover state
    'primary_light':  '#C7E0F4',   # Soft blue background for sections
    'bg':             '#F3F2F1',   # Office light gray (main window bg)
    'bg_white':       '#FFFFFF',   # Panel/card backgrounds
    'bg_alt':         '#EFF6FC',   # Alternating row color
    'text':           '#201F1E',   # Near-black
    'text_secondary': '#605E5C',   # Gray text
    'border':         '#EDEBE9',   # Light border
    'success':        '#107C10',   # Green (confirmed mapping)
    'warning':        '#D83B01',   # Orange (review needed)
    'error':          '#A4262C',   # Red (unresolved / error)
    'header_bg':      '#0078D4',   # Grid header bg
    'header_fg':      '#FFFFFF',   # Grid header text
    'total_bg':       '#106EBE',   # Total row bg
    'total_fg':       '#FFFFFF',   # Total row text
    'section_bg':     '#C7E0F4',   # Section row bg
    'section_fg':     '#003087',   # Section row text
    'font_family':    'Segoe UI',  # MS Office default font
    'font_size':      10,
    'font_size_head': 11,
    'font_size_title':13,
}
```

---

## 6. ML Mapping Pipeline

```
Ledger Name Input
      │
      ▼
[1] Exact match vs learned_mappings (global + entity-type filtered)
      │ hit → confidence=1.0, source='LEARNED'
      │ miss ↓
[2] TF-IDF cosine similarity vs mapping_master.lookup_name
      │ best_score ≥ 0.65 → candidate
      │ score < 0.65 ↓
[3] Sentence-BERT similarity (bundled MiniLM model)
      │ best_score → candidate (or improve TF-IDF candidate)
      │ still < 0.65 ↓
[4] Claude API (if key set) — batch 20 at a time
      │
      ▼
Mapping Grid Display
  ≥ 0.85 → Green (auto-confirmed)
  0.65–0.84 → Yellow (needs review)
  < 0.65 → Red (manual required)
      │
      ▼
User confirms/overrides → saved to learned_mappings
```

---

## 7. Entity-Specific FS Format Reference

| Entity | BS Title | Income Statement Title | Cash Flow |
|--------|----------|----------------------|-----------|
| COMPANY | Balance Sheet (Sch III Pt I) | Statement of Profit & Loss (Sch III Pt II) | Yes (No for small co) |
| LLP | Balance Sheet (ICAI LLP) | Profit & Loss Account | Optional |
| PROP | Balance Sheet (ICAI NCE) | Profit & Loss Account | No |
| PART | Balance Sheet (ICAI NCE) | Profit & Loss Account | No |
| AOP | Balance Sheet (ICAI NCE) | Income & Expenditure Account | Optional |
| TRUST/NPO | Balance Sheet (ICAI NCE) | Income & Expenditure Account | Optional |
| SEC8 | Balance Sheet (Modified Sch III) | Income & Expenditure Account | Yes |

---

## 8. File Naming & Paths

```
%APPDATA%\FinStruct\
├── settings.db              ← global settings + recent projects + learned mappings
├── models\
│   └── all-MiniLM-L6-v2\   ← bundled sentence-transformer model

%USERPROFILE%\Documents\FinStruct\
└── Projects\
    └── XYZ_Ltd_2024-25\
        ├── XYZ_Ltd_2024-25.finstruct    ← per-client SQLite (renamed .db)
        └── exports\
            ├── XYZ_Ltd_2024-25_FS.pdf
            ├── XYZ_Ltd_2024-25_FS.xlsx
            └── XYZ_Ltd_2024-25_Reports.docx
```

---

## 9. Build & Packaging

```bash
pip install pyinstaller
pyinstaller finstruct.spec
# Produces: dist/FinStruct/FinStruct.exe
```

`finstruct.spec` includes:
- `sentence_transformers` model files as `datas`
- `reportlab` font files
- `ca_reminder` excluded (separate app)
