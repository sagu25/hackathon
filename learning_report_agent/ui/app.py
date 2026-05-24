"""Learning Report Agent — Main Streamlit App."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Learning Report Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 28px; font-weight: 700; color: #0f1923; }
    .sub-header { font-size: 14px; color: #6b7280; margin-top: -10px; }
    .metric-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
    .status-good { color: #059669; font-weight: 600; }
    .status-warn { color: #d97706; font-weight: 600; }
    .status-bad { color: #dc2626; font-weight: 600; }
    .tier-badge { background: #1e293b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
</style>
""", unsafe_allow_html=True)


def show_home():
    st.markdown('<div class="main-header">🎓 Learning Report Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Unified analytics platform for learning & development</div>', unsafe_allow_html=True)
    st.divider()

    col1, col2, col3 = st.columns(3)

    from config import DB_PATH
    import sqlite3

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            emp_count = conn.execute("SELECT COUNT(*) FROM employees WHERE employment_status='Active'").fetchone()[0]
            enroll_count = conn.execute("SELECT COUNT(*) FROM lms_enrollments").fetchone()[0]
            comp_rate = conn.execute("SELECT ROUND(AVG(completion_rate),1) FROM gold_dept_learning_kpis").fetchone()[0]
            with col1:
                st.metric("Active Employees", f"{emp_count:,}")
            with col2:
                st.metric("Total Enrollments", f"{enroll_count:,}")
            with col3:
                st.metric("Avg Completion Rate", f"{comp_rate or 0}%")
        except Exception:
            st.info("Database not set up yet. Run the setup script first.")
        finally:
            conn.close()
    else:
        st.warning("Database not initialised. Go to **Admin** → **Setup** to initialise.")

    st.divider()
    st.subheader("Navigate")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("### 💬 Chat Agent\nAsk questions in natural language about learning data")
    with c2:
        st.markdown("### 📊 Reports\nGenerate compliance, KPI and skill gap reports")
    with c3:
        st.markdown("### 📈 Dashboards\nInteractive charts and KPI visualisations")
    with c4:
        st.markdown("### ⚡ Flow Library\nView and trigger Power Automate flows built by the agent")
    with c5:
        st.markdown("### ⚙️ Admin\nSetup, source onboarding, configuration")


show_home()
