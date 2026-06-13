# Learning Report Agent — Setup Guide

## Quick Start (one command after prerequisites)

```bash
pip install -r requirements.txt
python start.py
```

Open: **http://localhost:8501**

> `start.py` generates data and sets up the database **only on first run**.
> On subsequent runs it launches the UI directly (your saved schedules, reports, and flows are preserved).
> To force a full rebuild: `python start.py --reset`

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| pip | 24+ | `pip --version` |
| ~500 MB disk | — | for DB + vector store |
| Azure OpenAI | Optional | app works in mock mode without it |

**Windows:** Download Python from python.org. During install, tick **"Add Python to PATH"**.  
**Mac:** `brew install python@3.11`

---

## Step-by-Step Setup

### 1. Get the project

Copy the `learning_report_agent/` folder to your machine.

### 2. Open a terminal inside the folder

**Windows:** Right-click the folder → "Open in Terminal"  
**Mac:** `cd ~/path/to/learning_report_agent`

### 3. (Recommended) Create a virtual environment

```bash
python -m venv venv

# Activate — Windows:
venv\Scripts\activate

# Activate — Mac/Linux:
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
# Takes 2–5 minutes on first install
```

### 5. Configure credentials (all optional — app runs without them)

```bash
# Windows:
copy .env.example .env

# Mac/Linux:
cp .env.example .env
```

Edit `.env` with the values you have. Leave any section blank to skip it.

#### Azure OpenAI (Chat Agent)
```
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```
Where to find: Azure Portal → your OpenAI resource → Keys and Endpoint.  
Without this: Chat Agent returns a mock response explaining credentials are needed.

#### Power BI (live dashboard push)
```
POWERBI_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POWERBI_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POWERBI_CLIENT_SECRET=your-secret-value
POWERBI_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
Where to find: Azure Portal → Azure Active Directory → App registrations (see FLOW.md for full setup steps).  
Without this: Power BI push button is disabled; all other features work normally.

#### SMTP Email Delivery (scheduled reports)
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```
Gmail: use an App Password (myaccount.google.com → Security → App passwords).  
Without this: Scheduled delivery runs in **dry-run mode** — PDFs are saved to `data/sent_reports/` instead of emailed.

### 6. Launch the app

```bash
# Normal start (skips data generation if already done):
python start.py

# Force full rebuild (re-generates dirty data + re-runs cleaning pipeline):
python start.py --reset

# UI only (if DB already exists):
python -m streamlit run ui/app.py

# Different port:
python -m streamlit run ui/app.py --server.port 8502
```

---

## What Happens on First Run

```
Step 1/2: Generating mock data
  → employees.csv       510 rows  (with injected dirty data)
  → lms_enrollments.csv 3872 rows (with status variants, duplicates)
  → skill_assessments.csv 2336 rows
  → training_budget.csv   8 rows
  → course_catalog.csv   15 rows

Step 2/2: Setting up database (Bronze → Silver → Gold)
  [FIX] Duplicate employee_id rows removed: 10 of 510
  [FIX] Inconsistent department names normalised: 59 of 500
  [FIX] employment_status casing fixed: 35 of 500
  [FIX] Null emails filled with placeholder: 35 of 500
  ...
  Gold KPIs built.

Background scheduler started — checks every 60 s
Launching Streamlit UI → http://localhost:8501
```

On **subsequent runs**, steps 1 and 2 are skipped automatically.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt`. Activate venv if using one. |
| Port 8501 already in use | Add `--server.port 8502` |
| "Azure OpenAI not configured" | Copy `.env.example` to `.env`, fill credentials, restart app |
| Empty dashboards / no data | Go to Admin → Setup → Generate Mock Data → Setup Database |
| `UnicodeEncodeError` on Windows | `set PYTHONIOENCODING=utf-8` before running scripts |
| ChromaDB install fails on Windows | Install Visual C++ Build Tools from visualstudio.microsoft.com |
| Power BI push button greyed out | Add Power BI credentials to `.env`, restart app |
| Reports emailed as dry-run | Add SMTP credentials to `.env`, restart app |

---

## Project Structure

```
learning_report_agent/
├── config.py                    # All settings (Azure, SMTP, Power BI, paths)
├── start.py                     # One-command launcher (smart: skips regen if DB exists)
├── requirements.txt
├── .env.example                 # Copy to .env and fill credentials
├── SETUP.md                     # This file
├── FLOW.md                      # Full pipeline flow documentation
│
├── scripts/
│   ├── generate_mock_data.py    # Creates CSV source files with injected dirty data
│   └── setup_db.py              # Bronze→Silver→Gold pipeline with cleaning log
│
├── mcp_servers/                 # MCP tool servers
│   ├── lms_server.py            # LMS completions, enrollments, compliance
│   ├── hr_server.py             # Employee profiles, org hierarchy, skill gaps
│   ├── powerbi_server.py        # Semantic model queries
│   └── automate_server.py       # Power Automate flow generation
│
├── agents/
│   ├── orchestrator.py          # Main agent loop (intent → tools → response)
│   ├── llm_client.py            # Azure OpenAI / mock fallback
│   ├── tools_registry.py        # All tool definitions
│   └── tool_executor.py         # Tool dispatch
│
├── memory/
│   ├── agent_memory.py          # Episodic + procedural memory (ChromaDB + SQLite)
│   └── knowledge_graph.py       # Org knowledge graph (NetworkX)
│
├── output/
│   ├── report_generator.py      # Compliance / KPI / Skill Gap report dicts
│   ├── pdf_generator.py         # Branded A4 PDF (reportlab)
│   ├── word_generator.py        # Branded .docx (python-docx)
│   ├── email_sender.py          # SMTP delivery with PDF attachment + dry-run
│   ├── scheduler.py             # Background daemon thread — auto-delivers on schedule
│   ├── powerbi_connector.py     # MSAL auth + Push Dataset + row push
│   └── proactive_engine.py      # Daily compliance scans + manager briefings
│
├── ui/
│   ├── app.py                   # Homepage with live KPI scorecards
│   └── pages/
│       ├── 1_Chat_Agent.py      # Natural language queries
│       ├── 2_Reports.py         # Generate + Download PDF/Word reports
│       ├── 3_Dashboards.py      # Interactive charts with full filter sidebar
│       ├── 4_Flow_Library.py    # Power Automate flow viewer
│       └── 5_Admin.py           # Setup / Config / Memory / Power BI / Scheduled Delivery
│
└── data/                        # Created at runtime (git-ignored)
    ├── mock/                    # Raw CSV source files
    ├── learning_agent.db        # SQLite (Bronze + Silver + Gold + logs)
    ├── sent_reports/            # PDFs saved by dry-run scheduler
    └── chroma/                  # ChromaDB vector index
```

---

## Pages Quick Reference

| Page | What it does |
|---|---|
| Home | Live KPI scorecards pulled from Gold layer |
| Chat Agent | Natural language queries over all learning data |
| Reports | Generate Compliance / KPI / Skill Gap reports — download as PDF or Word |
| Dashboards | Interactive charts — filter by team, time period, course, skill domain |
| Flow Library | View, create, and trigger Power Automate flow definitions |
| Admin → Setup | Regenerate data, rebuild database, view table row counts |
| Admin → Configuration | Azure OpenAI status + config instructions |
| Admin → Power BI | Push Gold layer to Power BI Push Dataset (needs credentials) |
| Admin → Scheduled Delivery | Configure recipients + frequency, Send Now, view delivery log |
