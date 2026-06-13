# Learning Report Agent — Complete App Guide

**LTM – HackToFuture 2026**
Built for: Unified Analytics for Learning & Development

---

## What is this app?

The Learning Report Agent is an AI-powered analytics pipeline that eliminates manual reporting
for Learning & Development teams.

**The problem it solves:**
L&D managers pull data from 3–5 disconnected systems every week — LMS platforms, HR tools,
skill trackers, budget sheets. The data is messy (wrong spellings, duplicates, missing values),
the process is manual, and reports are stale by the time they reach a decision-maker.

**What this app does:**
It connects to all those systems automatically, cleans the data, and delivers structured
reports and live dashboards to stakeholders — on a schedule, with zero manual effort.

---

## The 7-tier pipeline

```
SOURCE SYSTEMS          TIER 1            TIER 2             TIER 3
──────────────          ──────            ──────             ──────
LMS (Cornerstone)  ─┐
LMS (SAP SF)       ─┤   BRONZE           SILVER             GOLD
HR / Employees     ─┼── Raw landing  --> Cleaned &   -->   KPI
Skill Assessments  ─┤   (audit trail)    standardised       aggregates
Training Budget    ─┘

                              │
              ┌───────────────┼────────────────┐
              │               │                │
           TIER 4          TIER 5           TIER 6
           AI Agent        Reports          Dashboard
        (Chat, tools)   (PDF / Word)    (Streamlit + Power BI)
              │               │                │
              └───────────────┴────────────────┘
                                    │
                                 TIER 7
                            Scheduled Delivery
                        (auto email to stakeholders)
```

---

## Tier 1 — Multi-Source Data Ingestion

The pipeline connects to **5 distinct source systems**:

| Source | What it contains |
|---|---|
| LMS — Cornerstone | Course enrollments, completions, scores for Engineering/IT/Finance |
| LMS — SAP SuccessFactors Learning | Enrollments and completions for HR/Sales/Marketing |
| HR / Workforce system | Employee profiles, org hierarchy, departments, grade levels, locations |
| Skill Assessment platform | Self-rated and manager-rated skill scores across 15 skill domains |
| Training Budget system | Per-department budget, actual spend, headcount targets |

All raw data lands in the **Bronze layer** — stored exactly as-is with source tag and
ingestion timestamp. Nothing is changed. This is the audit trail.

---

## Tier 2 — Data Cleaning (Bronze → Silver)

This is the core differentiator. Every data quality issue is detected, fixed, and logged
with exact counts. Nothing enters the Silver layer dirty.

**Types of issues handled:**

| Issue | Example | Fix applied |
|---|---|---|
| Inconsistent department names | "Engg", "Human Resources", "Fin", "Ops" | Normalised to "Engineering", "HR", "Finance", "Operations" |
| Mixed-case status values | "completed", "COMPLETED", "Done", "IN_PROGRESS" | Normalised to "Completed", "In Progress", "Not Started" |
| Duplicate records | Same employee_id appearing twice | Duplicates removed, first occurrence kept |
| Null email addresses | ~6% of employees had no email | Filled with placeholder (empid@unknown.internal) |
| Null location values | ~5% of employees had no location | Filled with "Unknown" |
| Null spend values | Some departments had no spend recorded | Filled with 0 |
| Proficiency level variants | "beginner", "ADVANCED", "Adv" | Normalised to "Beginner", "Advanced" |

**What the log looks like when the pipeline runs:**
```
  employees.csv  raw: 510 rows
    [FIX] Duplicate employee_id rows removed: 10 of 510 rows (2.0%)
    [FIX] Inconsistent department names normalised: 59 of 500 rows (11.8%)
    [FIX] employment_status casing fixed: 35 of 500 rows (7.0%)
    [FIX] Null emails filled with placeholder: 35 of 500 rows (7.0%)
    [FIX] Null locations filled with Unknown: 30 of 500 rows (6.0%)
  OK employees loaded to silver: 500 rows (removed 10 dirty rows)

  lms_enrollments.csv  raw: 3872 rows
    [FIX] Duplicate enrollment_id rows removed: 57 of 3872 rows (1.5%)
    [FIX] Inconsistent status values normalised: 356 of 3815 rows (9.3%)
    [FIX] course_category casing normalised: 301 of 3815 rows (7.9%)
    [FIX] Null scores on Completed rows filled with median: 110 of 3815 rows (2.9%)
  OK lms_enrollments loaded to silver: 3815 rows
```

---

## Tier 3 — Gold Layer (Aggregated KPIs)

Three pre-computed analytical tables, joined across all source systems:

### gold_dept_learning_kpis
One row per department. Contains: headcount, total enrollments, total completions,
completion rate %, required compliance rate %, average hours per employee,
budget USD, spend USD, budget utilisation %.

### gold_compliance_summary
One row per department × required course. Contains: total enrolled, completed,
completion rate %, average score.

### gold_skill_gap
One row per department × skill. Contains: average self-rating, average manager-rating,
gap score (self − manager), employee count.

---

## Tier 4 — AI Agent (Chat Interface)

**Page: Chat Agent**

Powered by Azure OpenAI (GPT-4o). The agent understands natural language questions
and uses tools to query the Gold layer.

**How it works:**
1. You type a question in plain English
2. The agent identifies the intent (compliance query, skill gap, report request, automation)
3. It calls the right MCP tools (LMS Server, HR Server, Power BI Server, Power Automate Server)
4. Tools execute SQL queries against the Gold/Silver layers and return data
5. The agent synthesises a specific, cited answer with real numbers
6. The conversation is saved to memory so similar future queries can reference it

**Example questions you can ask:**
- "Which departments have compliance below 80%?"
- "Who are the top 5 overdue learners in Engineering?"
- "Show me the skill gaps across all departments"
- "Generate a weekly learning report for the HR team"
- "Create a compliance reminder flow for managers"
- "What is the training budget utilisation in Finance?"

**Without Azure OpenAI configured:** The agent explains that credentials are needed and
shows what it would do. All other pages work fully without it.

---

## Tier 5 — Report Generation

**Page: Reports**

Three report types, available for any department or all departments combined:

| Report | What it shows |
|---|---|
| Compliance Training Report | Avg compliance rate, at-risk departments, overdue learners table, completion % by course and dept |
| Learning KPI Report | Org avg completion, top/bottom department, per-dept headcount/hours/completion/budget table |
| Skill Gap Analysis | Self vs manager ratings, overrated skills, underrated skills, gap scores |

**Output formats:**
- **PDF** — branded A4 document with Microsoft-blue header/footer, metric summary band, styled tables. Generated by reportlab.
- **Word (.docx)** — same content as a formatted Word document. Generated by python-docx.

Both available via download button immediately after generating a report.

---

## Tier 6 — Dashboards

**Page: Dashboards**

Interactive Plotly charts with a **full filter sidebar**. All 8 charts respond to filters simultaneously.

**Available filters (sidebar):**
| Filter | What it controls |
|---|---|
| Department / Team | Filter all charts to one or more departments |
| From month / To month | Narrow enrollment trends and completion metrics to a time period |
| Course | Filter compliance heatmap and course charts to specific courses |
| Course category | Filter to Compliance / Technical / Leadership / Sales / etc. |
| Skill domain | Filter skill gap chart to specific skills |

**Charts on the page:**
1. Completion rate by department — horizontal bar, red-to-green colour scale
2. Training hours vs compliance rate — scatter plot sized by headcount
3. Monthly enrollment vs completion trends — dual-line chart
4. Compliance heatmap — department × course colour matrix
5. Course-level completion top-N — horizontal bar by course
6. Training budget vs spend — grouped bar per department
7. Headcount + completion treemap — area = headcount, colour = completion rate
8. Skill gap analysis — bar chart (self − manager rating) per skill and department

**Power BI integration:**
From Admin → Power BI, the Gold layer data is pushed to a live Power BI Push Dataset
(4 tables: DeptLearningKPIs, ComplianceSummary, SkillGap, EnrollmentTrends).
Stakeholders can build their own Power BI dashboards on top of this live data.

---

## Tier 7 — Scheduled Delivery

**Page: Admin → Scheduled Delivery**

A background daemon thread starts when the app launches and checks every 60 seconds
whether any scheduled report is due to be delivered.

**Schedule options:**
- Daily (8am)
- Weekly — Monday 8am
- Monthly — 1st of each month

**When a schedule fires:**
1. The report is generated from the latest Gold layer data
2. It is rendered as a PDF
3. The PDF is emailed to the configured recipient list (if SMTP is set up)
4. If SMTP is not configured: PDF is saved to `data/sent_reports/` instead (dry-run mode)
5. The delivery is logged to `delivery_log` table with status, timestamp, and detail

**How to set up a schedule:**
1. Go to Admin → Scheduled Delivery
2. Choose report type, department, frequency, and enter recipient emails
3. Click Save Schedule
4. The scheduler picks it up within 60 seconds

**Send Now button:** Triggers an immediate delivery for testing or on-demand distribution.

---

## The Admin Console

**Page: Admin** (6 tabs)

| Tab | What you do here |
|---|---|
| Setup | Generate mock data, rebuild the database, view table row counts |
| Configuration | Enter Azure OpenAI credentials, check connection status |
| Agent Memory | Browse past chat queries, view procedural recipe memory |
| Data Explorer | Browse any database table — Bronze, Silver, Gold, or logs |
| Scheduled Delivery | Create/delete schedules, Send Now, view delivery log |
| Power BI | Enter Power BI credentials, push Gold layer, view dashboard build guide |

---

## Flow Library

**Page: Flow Library**

The AI agent can generate Power Automate flow definitions. These are stored in the database
and visible in the Flow Library.

**Built-in templates:**
- Compliance Training Reminder — weekly email to non-compliant employees
- Course Completion Notification — manager alert when employee completes a course
- Weekly Learning Report Delivery — Monday morning report email to department heads
- Skill Gap Alert — monthly Teams notification when gaps exceed threshold

The agent generates the full flow JSON definition, which can be imported into Power Automate.

---

## Credential setup (what needs to be configured)

All credentials go in the `.env` file (copy from `.env.example`).

| Credential | Used for | Required? |
|---|---|---|
| AZURE_OPENAI_ENDPOINT + API_KEY | Chat Agent AI responses | Optional — mock mode works without it |
| POWERBI_TENANT_ID + CLIENT_ID + CLIENT_SECRET + WORKSPACE_ID | Pushing data to Power BI | Optional — Streamlit dashboard works without it |
| SMTP_HOST + SMTP_USER + SMTP_PASSWORD | Sending real emails | Optional — dry-run saves PDFs to disk |

**The app works fully without any credentials.** Azure OpenAI enables real AI responses,
Power BI enables the enterprise dashboard, and SMTP enables real email delivery.

---

## System status indicators

The app homepage shows 4 status indicators:
- **Database** — green if Bronze/Silver/Gold is ready
- **Azure OpenAI** — green if endpoint + key are configured
- **Email Delivery** — green if SMTP is configured (orange = dry-run mode)
- **Power BI** — green if all 4 Power BI credentials are configured

---

## Files and what they do

```
start.py                     One-command launcher. Skips data gen if DB exists.
                             Use --reset flag to force a full rebuild.

scripts/
  generate_mock_data.py      Creates 5 source CSV files with intentional dirty data injected.
  setup_db.py                Bronze -> Silver cleaning pipeline + Gold KPI aggregation.

agents/
  orchestrator.py            Main AI agent loop: intent -> tools -> response -> memory.
  llm_client.py              Azure OpenAI client with mock fallback.
  tools_registry.py          All tool definitions exposed to the LLM.
  tool_executor.py           Dispatches tool calls to the right MCP server.

mcp_servers/
  lms_server.py              Tools: completions, enrollments, compliance, overdue learners.
  hr_server.py               Tools: employees, skill gaps, org chart, manager briefings.
  powerbi_server.py          Tools: dataset queries, report creation.
  automate_server.py         Tools: flow list, create flow, trigger flow, templates.

output/
  report_generator.py        Generates compliance / KPI / skill gap report dicts from Gold layer.
  pdf_generator.py           Renders report dicts as branded A4 PDFs (reportlab).
  word_generator.py          Renders report dicts as branded Word documents (python-docx).
  email_sender.py            Sends PDF by email via SMTP. Dry-run fallback saves to disk.
  scheduler.py               Background daemon thread. Checks and fires schedules every 60s.
  powerbi_connector.py       MSAL auth + creates Push Dataset + pushes Gold layer rows.
  proactive_engine.py        Daily compliance scan + manager team briefings.

memory/
  agent_memory.py            Episodic memory (ChromaDB) + procedural recipes (SQLite).
  knowledge_graph.py         Org hierarchy as a NetworkX graph.

ui/
  app.py                     Homepage with live KPI metrics and system status.
  pages/
    1_Chat_Agent.py          Natural language query interface.
    2_Reports.py             Report generator with PDF + Word download.
    3_Dashboards.py          Interactive Plotly charts with full filter sidebar.
    4_Flow_Library.py        Power Automate flow viewer and creator.
    5_Admin.py               Admin console with 6 tabs.
```

---

## 5-minute demo script (for judges)

**1. Show the dirty data (30 sec)**
Admin → Data Explorer → select `bronze_employees`
Point out: "Engg", "Human Resources", "active" (lowercase), duplicate rows.
Switch to `employees` (Silver): same data, now clean.
"The pipeline logged exactly what it fixed — 59 department names, 10 duplicates removed."

**2. Show the pipeline (30 sec)**
Admin → Setup → Database Status.
"500 employees from 5 sources, 3,800+ enrollments, Gold layer with pre-computed KPIs — all automated."

**3. Chat Agent (1 min)**
Ask: "Which departments are below 80% compliance? List overdue learners in Engineering."
Show the agent calling tools and returning specific cited numbers.
Ask: "Create a weekly compliance reminder flow."
Show the flow appearing in the Flow Library.

**4. Generate a PDF report (30 sec)**
Reports → Compliance Training Report → All Departments → Generate Report.
Point out the metrics, charts, and overdue learners table.
Click Download PDF. Open it. Show the branded layout.
Click Download Word. Show the .docx version.

**5. Dashboard filters (1 min)**
Dashboards → sidebar → set Department to "Engineering".
All 8 charts update instantly.
Change time period to last 3 months. Trend chart narrows.
Add a course filter. Compliance heatmap filters.
"Team, time period, course, skill domain — all 4 filters the challenge asks for."

**6. Scheduled delivery (30 sec)**
Admin → Scheduled Delivery.
Show or create a schedule: Daily, Compliance, any email.
Click Send Now. Show PDF saved or email sent.
Scroll to Delivery Log. Every send is recorded.

**7. Power BI (30 sec, if credentials set)**
Admin → Power BI → Push Data Now.
Show tables pushed with row counts.
Open workspace URL. Live data ready for dashboard build.

---

*Learning Report Agent — LTM HackToFuture 2026*
