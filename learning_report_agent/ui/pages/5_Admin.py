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

tab1, tab2, tab3, tab4 = st.tabs(["Setup", "Configuration", "Agent Memory", "Data Explorer"])

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
