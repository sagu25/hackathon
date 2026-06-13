# Learning Report Agent — Full Pipeline Flow

## LTM – HackToFuture 2026

---

## Overview

The Learning Report Agent is a 7-tier automated analytics pipeline that eliminates manual reporting
for Learning & Development teams. Raw data from multiple disconnected systems enters one end;
clean, standardised reports and live dashboards come out the other — automatically, on schedule,
with no human assembly required.

```
SOURCE SYSTEMS          INGESTION          CLEANING           ANALYTICS
─────────────────       ─────────          ────────           ─────────
LMS (Cornerstone)  ──┐                ┌── Silver layer ──┐
LMS (SAP SF)       ──┤  Bronze layer  │   (clean data)   │  Gold layer
HR / Employees     ──┼─ (raw landing) ┤                  ├─ (KPIs + aggregates)
Skill Assessments  ──┤                │   Cleaning log   │
Training Budget    ──┘                └──────────────────┘
                                                │
                        ┌───────────────────────┼─────────────────────────────┐
                        │                       │                             │
                   AI AGENT               REPORTS                      DASHBOARDS
                   (Chat)            PDF / Word (.docx)           Streamlit + Power BI
                        │                       │                             │
                        └───────────────────────┴──── SCHEDULED DELIVERY ────┘
                                                         (email + delivery log)
```

---

## Tier 1 — Multi-Source Data Ingestion

### Source systems simulated

| Source | File | What it represents |
|---|---|---|
| LMS — Cornerstone | `employees.csv` + `lms_enrollments.csv` (lms_source=Cornerstone) | Primary LMS used by Engineering, IT, Finance |
| LMS — SAP SuccessFactors Learning | `lms_enrollments.csv` (lms_source=SAP SF Learning) | Secondary LMS for HR, Sales, Marketing |
| HR / Workforce system | `employees.csv` | Employee profiles, org hierarchy, grades, locations |
| Skill Assessment platform | `skill_assessments.csv` | Self + manager skill ratings across 15 skill domains |
| Training Budget system | `training_budget.csv` | Per-department budget, spend, headcount targets |

All sources land as CSV files in `data/mock/` — simulating exports from real enterprise systems.

**Intentional data quality issues injected at source:**

| Issue type | Where | Examples |
|---|---|---|
| Inconsistent naming | employees.department | "Engg", "Human Resources", "Fin", "Ops", "Mktg" |
| Inconsistent status | lms_enrollments.status | "completed", "COMPLETED", "Done", "IN_PROGRESS", "Pending" |
| Null values | email, location, spent_usd | ~5–7% of rows |
| Duplicate records | employees, enrollments, skills | ~1–2% of rows |
| Mixed casing | employment_status, proficiency_level | "active", "ADVANCED", "Beg" |

---

## Tier 2 — Bronze Layer (Raw Landing)

**File:** `scripts/setup_db.py` → `clean_and_load_silver()`

Every raw row from every source CSV is stored as a JSON blob in Bronze tables:
- `bronze_employees` — raw employee rows with source tag + ingestion timestamp
- `bronze_enrollments` — raw enrollment rows with source tag + ingestion timestamp

**Purpose:** Audit trail. You can always trace a Silver row back to its original raw form.

---

## Tier 3 — Silver Layer (Cleaned & Standardised)

**File:** `scripts/setup_db.py` → `clean_and_load_silver()`

Each data quality issue is detected, logged, and fixed before writing to Silver:

```
-- Data Quality: Bronze -> Silver ---------------------------------

  employees.csv  raw: 510 rows
    [FIX] Duplicate employee_id rows removed: 10 of 510 rows (2.0%)
    [FIX] Inconsistent department names normalised: 59 of 500 rows (11.8%)
    [FIX] employment_status casing fixed: 35 of 500 rows (7.0%)
    [FIX] Null emails filled with placeholder: 35 of 500 rows (7.0%)
    [FIX] Null locations filled with 'Unknown': 30 of 500 rows (6.0%)
  OK employees loaded to silver: 500 rows (removed 10 dirty rows)

  lms_enrollments.csv  raw: 3872 rows
    [FIX] Duplicate enrollment_id rows removed: 57 of 3872 rows (1.5%)
    [FIX] Inconsistent status values normalised: 356 of 3815 rows (9.3%)
    [FIX] course_category casing normalised: 301 of 3815 rows (7.9%)
    [FIX] Null scores on Completed rows filled with median: 110 of 3815 rows (2.9%)
  OK lms_enrollments loaded to silver: 3815 rows (removed 57 dirty rows)
  ...
```

**Silver tables (unified schema):**
- `employees` — 500 clean employee records
- `lms_enrollments` — 3,800+ clean enrollment records
- `skill_assessments` — 2,300+ clean skill ratings
- `training_budget` — 8 department budget records
- `course_catalog` — 15 courses

**Canonical lookups used for normalisation:**
- Department variants → `_DEPT_CANONICAL` (27 variant → 8 canonical depts)
- Status variants → `_STATUS_CANONICAL` (12 variant → 3 canonical statuses)
- Proficiency variants → `_PROFICIENCY_CANONICAL` (12 variant → 4 levels)

---

## Tier 4 — Gold Layer (Aggregated KPIs)

**File:** `scripts/setup_db.py` → `build_gold()`

Three pre-computed analytical tables built from Silver:

### `gold_dept_learning_kpis`
Per-department rollup: headcount, completion rate, required completion rate,
avg hours per employee, budget USD, spend USD, budget utilisation %.

### `gold_compliance_summary`
Per-department × per-required-course: total enrolled, completed, completion rate, avg score.

### `gold_skill_gap`
Per-department × per-skill: avg self rating, avg manager rating, gap score (self − manager),
employee count.

Gold layer is rebuilt every time `setup_db.py` runs (also triggerable from Admin UI).

---

## Tier 5 — AI Agent (Natural Language Interface)

**Files:** `agents/orchestrator.py`, `agents/llm_client.py`, `mcp_servers/`

### How a query is processed

```
User types: "Which departments have compliance below 80%?"
        │
        ▼
Orchestrator (orchestrator.py)
  1. Recalls similar past queries from ChromaDB memory
  2. Builds message list [system_prompt + memory_context + user_message]
  3. Calls Azure OpenAI (gpt-4o) with tool definitions
        │
        ▼
  LLM decides to call: get_compliance_summary()
        │
        ▼
  Tool executor (tool_executor.py) → LMS MCP server (lms_server.py)
    → SQL: SELECT * FROM gold_compliance_summary WHERE completion_rate < 80
    → Returns JSON rows
        │
        ▼
  LLM synthesises: "Engineering (74%), Legal (71%), and Operations (68%)
                    are below the 80% compliance threshold. Engineering
                    has 23 overdue learners for Cybersecurity Awareness..."
        │
        ▼
  Memory saved: session_id + query + summary + intent → ChromaDB + SQLite
        │
        ▼
User sees the response in the Chat Agent page
```

### Available tools (via MCP servers)

| Server | Tools |
|---|---|
| LMS Server | get_completions, get_overdue_learners, get_compliance_summary, get_dept_kpis |
| HR Server | get_employees, get_skill_gaps, get_org_chart, get_manager_briefing |
| Power BI Server | list_datasets, query_semantic_model, create_report |
| Power Automate Server | list_flows, create_flow, trigger_flow, get_flow_from_template |

### Memory system
- **Episodic:** past queries + responses stored in ChromaDB, recalled by semantic similarity
- **Procedural:** named recipes for common report patterns
- **Knowledge graph:** org hierarchy modelled as NetworkX graph

---

## Tier 6 — Report Generation

**Files:** `output/report_generator.py`, `output/pdf_generator.py`, `output/word_generator.py`

### Report types

| Report | Contents |
|---|---|
| Compliance Training Report | Avg compliance rate, at-risk depts, overdue learners table |
| Learning KPI Report | Org avg completion, top/bottom dept, per-dept KPI table |
| Skill Gap Analysis | Self vs manager ratings, overrated/underrated skills |

### Output formats

Both formats are generated from the same report dict:

**PDF (reportlab):**
- Branded A4 — Microsoft blue header/footer bar
- Metric summary band (large numbers + labels)
- Styled data tables with alternating row shading
- All 3 report types supported

**Word (.docx) (python-docx):**
- Branded heading with blue title
- Metric band as a formatted table
- Data tables with blue header rows
- All 3 report types supported

Both formats downloadable from the **Reports** page with one click.

---

## Tier 7 — Dashboards, Delivery & Power BI

### Interactive Streamlit Dashboard

**File:** `ui/pages/3_Dashboards.py`

Full filter sidebar — every chart responds to all 4 filters simultaneously:

| Filter | What it does |
|---|---|
| Department / Team | Filter all charts to selected departments |
| From/To month | Filter enrollment trends and completion metrics to a date range |
| Course | Filter compliance and course-level charts to specific courses |
| Course category | Filter to Compliance / Technical / Leadership / etc. |
| Skill domain | Filter skill gap chart to specific skills |

Charts included:
- Completion rate by department (horizontal bar, RdYlGn colour scale)
- Training hours vs compliance rate (scatter, sized by headcount)
- Monthly enrollment vs completion trends (line chart)
- Compliance heatmap — department × course (colour matrix)
- Course-level completion top-N bar chart
- Training budget vs spend (grouped bar)
- Headcount + completion treemap
- Skill gap bar chart (self − manager rating)

### Power BI Integration

**File:** `output/powerbi_connector.py`

Push 4 tables to a live Power BI Push Dataset in your workspace:

| Step | What happens |
|---|---|
| 1 | MSAL client credentials auth → access token |
| 2 | Find or create Push Dataset named "Learning Analytics — Agent" |
| 3 | Clear old rows from all 4 tables |
| 4 | Push DeptLearningKPIs, ComplianceSummary, SkillGap, EnrollmentTrends |
| 5 | Return workspace URL to open directly |

**Azure AD App Registration setup:**
1. Azure Portal → Azure Active Directory → App registrations → New registration
2. Copy: Application (client) ID → `POWERBI_CLIENT_ID`
3. Copy: Directory (tenant) ID → `POWERBI_TENANT_ID`
4. Certificates & secrets → New client secret → copy value → `POWERBI_CLIENT_SECRET`
5. Power BI Admin portal → Tenant settings → Enable "Allow service principals to use Power BI APIs"
6. Create workspace → copy GUID from URL → `POWERBI_WORKSPACE_ID`
7. Add service principal to workspace as Member

**Recommended Power BI visuals:**
- Bar: department vs completion_rate (slicer on department)
- Gauge: avg of required_completion_rate (org compliance)
- Table: ComplianceSummary filtered to completion_rate < 80
- Bar: skill vs gap coloured by department
- Line: EnrollmentTrends month vs enrollments + completions

### Scheduled Report Delivery

**Files:** `output/scheduler.py`, `output/email_sender.py`

#### How the scheduler works

```
App startup (start.py)
        │
        ▼
start_scheduler() → daemon thread starts, loops every 60 seconds
        │
        ▼ every 60 s
_tick() → reads schedule_config table
        │
        ├── for each enabled schedule:
        │       _should_fire(frequency, last_run)?
        │           Daily    → True if last_run.date < today
        │           Weekly   → True if Monday AND last_run < this Monday
        │           Monthly  → True if 1st of month AND last_run.month < this month
        │
        ▼ if True:
_run_schedule(row)
  1. Generate report dict (compliance / kpi / skill_gap)
  2. Render PDF via pdf_generator
  3. send_report_email(recipients, report, pdf)
        │
        ├── SMTP configured → send real email with PDF attachment
        └── SMTP not set    → save PDF to data/sent_reports/ (dry-run)
  4. Update schedule_config.last_run = now
  5. Write to delivery_log table
```

#### Configuring a schedule (via Admin → Scheduled Delivery)

1. Choose report type, department, frequency, recipient emails
2. Click **Save Schedule** → stored in `schedule_config` table
3. Scheduler picks it up within 60 seconds on next tick
4. Use **Send Now** for immediate on-demand delivery

#### Delivery log

Every send attempt is recorded in `delivery_log`:
- status: `sent` / `dry_run` / `error`
- recipients, report title, timestamp, PDF path (dry-run), detail message

---

## Demo Script (for judges)

**Goal:** Show the full pipeline in ~5 minutes.

### 1. Show the dirty data problem (30 s)
- Open `data/mock/employees.csv` — point out "Engg", "Human Resources", "active" (lowercase)
- Open `data/mock/lms_enrollments.csv` — point out "completed", "IN_PROGRESS", duplicates

### 2. Run the cleaning pipeline (1 min)
```bash
python start.py --reset
```
- Show the `[FIX]` log output: "59 department names normalised", "57 duplicate enrollments removed"
- Explain Bronze → Silver → Gold architecture

### 3. Chat Agent (1 min)
- Open http://localhost:8501 → Chat Agent
- Ask: *"Which departments are below 80% compliance? List overdue learners."*
- Show the AI pulling from Gold layer via tools, citing specific numbers

### 4. Generate and download a PDF report (30 s)
- Go to Reports page
- Select: Compliance Training Report → All Departments → Generate Report
- Click **Download PDF** — open the file to show branded layout

### 5. Show the interactive dashboard (1 min)
- Go to Dashboards page
- Set Department filter to "Engineering" — all charts update instantly
- Set time period to last 6 months — trend chart narrows
- Change Course filter — compliance heatmap filters

### 6. Scheduled delivery demo (30 s)
- Go to Admin → Scheduled Delivery
- Show a saved schedule (or create one live: daily, any email)
- Click **Send Now** — show dry-run PDF downloaded or real email sent

### 7. Power BI (if credentials configured) (30 s)
- Go to Admin → Power BI
- Click **Push Data Now**
- Open the workspace URL — show live data in Power BI dataset ready for dashboard build

---

## Data Flow Summary

```
CSV files (dirty)
      │
      ▼ setup_db.py
Bronze (raw JSON blobs, audit trail)
      │
      ▼ clean_and_load_silver()
Silver (clean, normalised, deduped)
      │
      ▼ build_gold()
Gold (KPI aggregates — dept, course, skill)
      │
      ├──────────────────────────────────────────┐
      ▼                                          ▼
AI Agent (Chat)                          Reports + Dashboard
  → MCP tools query Gold                   → PDF / Word download
  → ChromaDB memory                        → Streamlit charts (filtered)
  → Azure OpenAI synthesis                 → Power BI push (live dataset)
      │                                          │
      └──────────────────────────────────────────┘
                            │
                            ▼
                  Scheduled Delivery
                  → Background scheduler (daemon thread)
                  → Email with PDF attachment (SMTP / dry-run)
                  → Delivery log in SQLite
```
