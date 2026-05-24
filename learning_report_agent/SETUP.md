# Learning Report Agent — Setup Guide

## Quick Start (3 commands after prerequisites)

```
pip install -r requirements.txt
python scripts/generate_mock_data.py
python scripts/setup_db.py
python -m streamlit run ui/app.py
```

Open: http://localhost:8501

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| pip | 24+ | `pip --version` |
| ~500 MB disk | — | — |
| Azure OpenAI | Optional | App works without it in mock mode |

### Install Python 3.11

**Windows:** Download from python.org. During install, tick **"Add Python to PATH"**.

**Mac:**
```bash
brew install python@3.11
```

---

## Step-by-Step Setup

### 1. Get the project files

Copy the `learning_report_agent/` folder to your machine.

Recommended path:
- Windows: `C:\Projects\learning_report_agent\`
- Mac/Linux: `~/projects/learning_report_agent/`

### 2. Open a terminal in the project folder

**Windows:** Right-click in the folder → "Open in Terminal" (or PowerShell)  
**Mac:** Terminal → `cd ~/projects/learning_report_agent`

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
# Takes 2-5 minutes
```

### 5. Configure Azure OpenAI (optional)

```bash
# Windows:
copy .env.example .env

# Mac/Linux:
cp .env.example .env
```

Edit `.env` and fill in:
```
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

**Where to find these:** Azure Portal → your Azure OpenAI resource → Keys and Endpoint

Skip this step to run in mock mode (all features work except real AI responses in Chat Agent).

### 6. Generate mock data

```bash
python scripts/generate_mock_data.py
```

Creates in `data/mock/`: employees.csv (500 rows), lms_enrollments.csv (~3,700 rows), skill_assessments.csv (~2,200 rows), training_budget.csv, course_catalog.csv

### 7. Set up the database

```bash
python scripts/setup_db.py
```

Creates `data/learning_agent.db` with Bronze/Silver/Gold tables and pre-computed KPIs.

### 8. Launch the app

```bash
# Option A: Full launcher (runs all setup + UI)
python start.py

# Option B: UI only (if data already set up)
python -m streamlit run ui/app.py

# If port 8501 is busy:
python -m streamlit run ui/app.py --server.port 8502
```

Open in browser: **http://localhost:8501**

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again. Activate venv if using one. |
| Port already in use | Add `--server.port 8502` to the run command |
| "Azure OpenAI not configured" in Chat | Copy `.env.example` to `.env` and fill credentials. Restart app. |
| Empty dashboards / no data | Go to Admin → Setup → click Generate Mock Data then Setup Database |
| `UnicodeEncodeError` on Windows | Run `set PYTHONIOENCODING=utf-8` before running scripts |
| ChromaDB install fails | Install Visual C++ Build Tools (Windows) or `brew install cmake` (Mac) |

---

## Project Structure (quick reference)

```
learning_report_agent/
├── config.py              # Settings and paths
├── start.py               # One-command launcher
├── requirements.txt       # Dependencies
├── .env.example           # Copy to .env
├── scripts/
│   ├── generate_mock_data.py   # Creates CSV mock data
│   └── setup_db.py             # Creates SQLite DB + Gold KPIs
├── mcp_servers/           # MCP tool servers (LMS, HR, Power BI, Automate)
├── agents/                # Orchestrator + tool executor + LLM client
├── memory/                # Episodic/semantic/procedural memory + knowledge graph
├── output/                # Report generator + proactive engine
├── ui/
│   ├── app.py             # Homepage
│   └── pages/             # Chat, Reports, Dashboards, Flow Library, Admin
└── data/                  # Created at runtime
    ├── mock/              # CSV files
    ├── learning_agent.db  # SQLite database
    └── chroma/            # Vector index
```

---

## Pages Quick Reference

| Page | What it does |
|---|---|
| 🏠 Home | Live KPI scorecards (employees, enrollments, completion rate) |
| 💬 Chat Agent | Natural language queries — ask anything about learning data |
| 📊 Reports | Generate Compliance / KPI / Skill Gap reports with charts |
| 📈 Dashboards | Interactive Plotly charts from the Gold data layer |
| ⚡ Flow Library | View, create, and trigger Power Automate flows |
| ⚙️ Admin | Database setup, Azure config, memory inspector, data explorer |
