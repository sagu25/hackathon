"""Admin page — setup, configuration, memory inspection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import subprocess
import sqlite3
import streamlit as st
import pandas as pd

from config import DB_PATH, MOCK_DIR, settings

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")
st.title("⚙️ Admin Console")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Setup", "Configuration", "Agent Memory", "Data Explorer", "Scheduled Delivery", "Power BI"])

# ── Setup tab ─────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Data Initialisation")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Step 1: Generate Mock Data**")
        st.caption("Creates 500 employees, 8,000+ enrollments, skill assessments, and budget data.")
        if st.button("Generate Mock Data", type="primary", key="gen_data"):
            scripts_dir = Path(__file__).parent.parent.parent / "scripts"
            with st.spinner("Generating..."):
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / "generate_mock_data.py")],
                    capture_output=True, text=True, cwd=str(scripts_dir.parent)
                )
            if result.returncode == 0:
                st.success("Mock data generated!")
                st.code(result.stdout)
            else:
                st.error("Failed to generate mock data")
                st.code(result.stderr)

    with col2:
        st.markdown("**Step 2: Setup Database**")
        st.caption("Creates Bronze/Silver/Gold schema, loads mock data, builds KPI aggregates.")
        if st.button("Setup Database", type="primary", key="setup_db"):
            scripts_dir = Path(__file__).parent.parent.parent / "scripts"
            with st.spinner("Setting up..."):
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / "setup_db.py")],
                    capture_output=True, text=True, cwd=str(scripts_dir.parent)
                )
            if result.returncode == 0:
                st.success("Database setup complete!")
                st.code(result.stdout)
                st.cache_data.clear()
            else:
                st.error("Setup failed")
                st.code(result.stderr)

    st.divider()
    st.subheader("Database Status")
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        tables = ["employees", "lms_enrollments", "course_catalog", "skill_assessments",
                  "gold_dept_learning_kpis", "gold_compliance_summary", "gold_skill_gap",
                  "generated_flows", "generated_reports", "agent_memory_episodic"]
        status_data = []
        for t in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                status_data.append({"Table": t, "Rows": count, "Status": "✅"})
            except Exception:
                status_data.append({"Table": t, "Rows": 0, "Status": "❌ Missing"})
        conn.close()
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    else:
        st.warning("Database not found. Run setup above.")

# ── Configuration tab ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("Azure OpenAI Configuration")

    configured = settings.is_azure_configured
    if configured:
        st.success("Azure OpenAI is configured")
    else:
        st.warning("Azure OpenAI not configured — agent will use mock responses")

    st.markdown("Edit your `.env` file (at the project root) with:")
    st.code("""AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large""")

    st.divider()
    st.subheader("Current Settings")
    st.json({
        "endpoint_set": bool(settings.azure_openai_endpoint),
        "key_set": bool(settings.azure_openai_api_key),
        "deployment": settings.azure_openai_deployment,
        "embedding_deployment": settings.azure_openai_embedding_deployment,
        "env": settings.app_env,
    })

# ── Agent Memory tab ──────────────────────────────────────────────────────────
with tab3:
    st.subheader("Episodic Memory (recent agent queries)")
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        episodes = [dict(r) for r in conn.execute(
            "SELECT id, session_id, query, intent, created_at FROM agent_memory_episodic ORDER BY created_at DESC LIMIT 50"
        ).fetchall()]
        conn.close()
        if episodes:
            st.dataframe(pd.DataFrame(episodes), use_container_width=True)
        else:
            st.info("No episodes yet. Use the Chat Agent to generate some.")
    else:
        st.warning("Database not set up.")

    st.divider()
    st.subheader("Procedural Memory (recipes)")
    try:
        from memory.agent_memory import list_recipes, ensure_default_recipes
        ensure_default_recipes()
        recipes = list_recipes()
        if recipes:
            st.dataframe(pd.DataFrame(recipes), use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load recipes: {e}")

# ── Data Explorer tab ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("Raw Data Explorer")
    if not DB_PATH.exists():
        st.warning("Database not set up.")
        st.stop()

    conn = sqlite3.connect(DB_PATH)
    available_tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    conn.close()

    selected_table = st.selectbox("Select table", available_tables)
    limit = st.slider("Rows to show", 10, 500, 50)

    if selected_table:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(f"SELECT * FROM {selected_table} LIMIT {limit}", conn)
            conn.close()
            st.dataframe(df, use_container_width=True)
            st.caption(f"Showing {len(df)} rows from {selected_table}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Scheduled Delivery tab ────────────────────────────────────────────────────
with tab5:
    st.subheader("Scheduled Report Delivery")

    smtp_ok = settings.is_smtp_configured
    if smtp_ok:
        st.success("SMTP configured — reports will be emailed to recipients")
    else:
        st.info(
            "SMTP not configured — reports will be saved to `data/sent_reports/` as PDFs. "
            "Add SMTP_HOST / SMTP_USER / SMTP_PASSWORD to your .env to enable real email."
        )

    st.divider()

    # ── Create / edit a schedule ─────────────────────────────────────────────
    st.subheader("Add Delivery Schedule")

    REPORT_TYPES = {
        "Compliance Training Report": "compliance",
        "Learning KPI Report":        "learning_kpis",
        "Skill Gap Analysis":         "skill_gap",
    }
    DEPARTMENTS = ["All Departments", "Engineering", "Sales", "HR", "Finance",
                   "Operations", "Marketing", "Legal", "IT"]
    FREQUENCIES = ["Daily (8am)", "Weekly — Monday 8am", "Monthly — 1st of month"]

    with st.form("schedule_form"):
        col1, col2 = st.columns(2)
        with col1:
            sched_report = st.selectbox("Report Type", list(REPORT_TYPES.keys()), key="sched_report")
            sched_dept   = st.selectbox("Department",  DEPARTMENTS, key="sched_dept")
        with col2:
            sched_freq   = st.selectbox("Frequency", FREQUENCIES, key="sched_freq")
            sched_emails = st.text_area(
                "Recipients (one per line or comma-separated)",
                placeholder="manager@company.com\ncto@company.com",
                height=100,
                key="sched_emails",
            )
        submitted = st.form_submit_button("Save Schedule", type="primary")

    if submitted:
        raw_emails = [e.strip() for e in sched_emails.replace(",", "\n").splitlines() if e.strip()]
        if not raw_emails:
            st.error("Enter at least one recipient email.")
        else:
            dept_val = None if sched_dept == "All Departments" else sched_dept
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO schedule_config (report_type, department, recipients, frequency, enabled) VALUES (?,?,?,?,1)",
                (REPORT_TYPES[sched_report], dept_val, ", ".join(raw_emails), sched_freq),
            )
            conn.commit()
            conn.close()
            st.success(f"Schedule saved: {sched_report} → {sched_freq} → {len(raw_emails)} recipient(s)")
            st.rerun()

    # ── Existing schedules ───────────────────────────────────────────────────
    st.divider()
    st.subheader("Active Schedules")

    try:
        conn = sqlite3.connect(DB_PATH)
        scheds = pd.read_sql_query(
            "SELECT id, report_type, department, recipients, frequency, enabled, last_run, created_at "
            "FROM schedule_config ORDER BY created_at DESC",
            conn
        )
        conn.close()
    except Exception:
        scheds = pd.DataFrame()

    if scheds.empty:
        st.info("No schedules yet. Add one above.")
    else:
        st.dataframe(scheds, use_container_width=True)

        del_id = st.number_input("Delete schedule by ID", min_value=1, step=1, key="del_sched_id")
        if st.button("Delete Schedule", key="del_sched_btn"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM schedule_config WHERE id=?", (int(del_id),))
            conn.commit()
            conn.close()
            st.success(f"Schedule {del_id} deleted.")
            st.rerun()

    # ── Manual / test send ───────────────────────────────────────────────────
    st.divider()
    st.subheader("Send Report Now")
    st.caption("Trigger an immediate delivery — useful for testing or on-demand distribution.")

    with st.form("send_now_form"):
        col1, col2 = st.columns(2)
        with col1:
            now_report = st.selectbox("Report Type", list(REPORT_TYPES.keys()), key="now_report")
            now_dept   = st.selectbox("Department",  DEPARTMENTS, key="now_dept")
        with col2:
            now_emails = st.text_area(
                "Recipients",
                placeholder="manager@company.com",
                height=80,
                key="now_emails",
            )
        send_now = st.form_submit_button("Send Now", type="primary")

    if send_now:
        raw_emails = [e.strip() for e in now_emails.replace(",", "\n").splitlines() if e.strip()]
        if not raw_emails:
            st.error("Enter at least one recipient email.")
        else:
            dept_val = None if now_dept == "All Departments" else now_dept
            with st.spinner("Generating report and sending..."):
                try:
                    from output.report_generator import (
                        generate_compliance_report, generate_learning_kpi_report,
                        generate_skill_gap_report,
                    )
                    from output.pdf_generator import generate_pdf
                    from output.email_sender import send_report_email

                    rtype = REPORT_TYPES[now_report]
                    if rtype == "compliance":
                        report = generate_compliance_report(dept_val)
                    elif rtype == "learning_kpis":
                        report = generate_learning_kpi_report(dept_val)
                    else:
                        report = generate_skill_gap_report(dept_val)

                    pdf_bytes = generate_pdf(report)
                    result    = send_report_email(raw_emails, report, pdf_bytes)

                    if result["status"] == "sent":
                        st.success(f"Sent! {result['detail']}")
                    elif result["status"] == "dry_run":
                        st.warning(f"Dry run (SMTP not configured). {result['detail']}")
                        pdf_path = result.get("pdf_path", "")
                        if pdf_path:
                            st.download_button(
                                "Download the generated PDF",
                                data=open(pdf_path, "rb").read(),
                                file_name=Path(pdf_path).name,
                                mime="application/pdf",
                            )
                    else:
                        st.error(f"Failed: {result['detail']}")

                except Exception as exc:
                    st.error(f"Error: {exc}")

    # ── Delivery log ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Delivery Log")
    try:
        from output.email_sender import list_delivery_log
        log = list_delivery_log(limit=30)
        if log:
            df_log = pd.DataFrame(log)
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("No deliveries yet.")
    except Exception as exc:
        st.info(f"Log unavailable: {exc}")

# ── Power BI tab ──────────────────────────────────────────────────────────────
with tab6:
    st.subheader("Power BI Integration")
    st.caption("Push your Gold layer data (KPIs, compliance, skill gaps) to a live Power BI Push Dataset.")

    from output.powerbi_connector import get_workspace_url

    pbi_configured = settings.is_powerbi_configured
    if pbi_configured:
        st.success("Power BI credentials configured — ready to push data.")
        st.markdown(f"**Workspace:** [{get_workspace_url()}]({get_workspace_url()})")
    else:
        st.warning(
            "Power BI not configured. Add these to your `.env` file:\n\n"
            "```\n"
            "POWERBI_TENANT_ID=...\n"
            "POWERBI_CLIENT_ID=...\n"
            "POWERBI_CLIENT_SECRET=...\n"
            "POWERBI_WORKSPACE_ID=...\n"
            "```"
        )

    st.divider()

    # ── Dataset schema preview ────────────────────────────────────────────────
    with st.expander("Dataset schema (what gets pushed to Power BI)", expanded=False):
        st.markdown("""
**4 tables will be created in a Push Dataset named `Learning Analytics — Agent`:**

| Table | Key columns |
|---|---|
| `DeptLearningKPIs` | department, headcount, completion_rate, required_completion_rate, avg_hours_per_employee, budget_usd, budget_utilization |
| `ComplianceSummary` | department, course_title, total_enrolled, completed, completion_rate, avg_score |
| `SkillGap` | department, skill, avg_self_rating, avg_manager_rating, gap, employee_count |
| `EnrollmentTrends` | month, enrollments, completions |

Build slicers by **department**, **course**, **skill** — exactly what the challenge requires.
        """)

    st.divider()

    # ── Push button ───────────────────────────────────────────────────────────
    st.subheader("Push Gold Layer Data to Power BI")
    st.caption("Clears existing rows in the dataset and re-pushes fresh data from the local Gold layer.")

    if st.button("Push Data Now", type="primary", key="pbi_push", disabled=not pbi_configured):
        with st.spinner("Connecting to Power BI and pushing data..."):
            from output.powerbi_connector import push_to_powerbi
            result = push_to_powerbi()

        if result["status"] == "success":
            st.success(f"Push complete! {result['total_rows']} total rows pushed.")

            cols = st.columns(len(result["tables_pushed"]))
            for col, (table, count) in zip(cols, result["tables_pushed"].items()):
                col.metric(table, f"{count} rows")

            st.markdown(f"**Open in Power BI:** [{result['workspace_url']}]({result['workspace_url']})")
            st.caption(f"Pushed at: {result['pushed_at'][:19]}")

            with st.expander("Push log"):
                for line in result.get("log", []):
                    st.text(line)

        elif result["status"] == "not_configured":
            st.warning(result["message"])
        else:
            st.error(f"Push failed: {result['message']}")
            with st.expander("Error log"):
                for line in result.get("log", []):
                    st.text(line)

    if not pbi_configured:
        st.info("Fill in Power BI credentials in your .env file, then restart the app to enable this button.")

    st.divider()

    # ── Dashboard building guide ──────────────────────────────────────────────
    st.subheader("Build Your Dashboard (after first push)")
    st.markdown("""
**After pushing data, build the dashboard in Power BI Service:**

1. Go to your workspace → find dataset **Learning Analytics — Agent**
2. Click **Create report** → select the dataset
3. **Recommended visuals for the challenge:**

| Visual | Table | Fields |
|---|---|---|
| Bar chart — Completion by dept | DeptLearningKPIs | department vs completion_rate |
| Gauge — Org avg compliance | DeptLearningKPIs | avg of required_completion_rate |
| Table — Overdue risk | ComplianceSummary | filter completion_rate < 80 |
| Bar chart — Skill gaps | SkillGap | skill vs gap, colour by department |
| Line chart — Enrollment trends | EnrollmentTrends | month vs enrollments + completions |

4. Add **slicers** on: `department`, `course_title`, `skill`
5. Publish the report, pin visuals to a **dashboard**
6. Share the dashboard URL in your submission
    """)
