"""Dashboards page — interactive KPI visualisations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import DB_PATH

st.set_page_config(page_title="Dashboards", page_icon="📈", layout="wide")
st.title("📈 Learning Dashboards")
st.caption("Live KPI visualisations from the Gold layer")

if not DB_PATH.exists():
    st.warning("Database not initialised. Go to Admin → Setup.")
    st.stop()


@st.cache_data(ttl=300)
def load_kpis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    kpis = [dict(r) for r in conn.execute("SELECT * FROM gold_dept_learning_kpis").fetchall()]
    compliance = [dict(r) for r in conn.execute("SELECT * FROM gold_compliance_summary").fetchall()]
    skill_gap = [dict(r) for r in conn.execute("SELECT * FROM gold_skill_gap").fetchall()]
    trends = [dict(r) for r in conn.execute("""
        SELECT strftime('%Y-%m', enrolled_date) as month,
               COUNT(*) as enrollments,
               SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completions
        FROM lms_enrollments GROUP BY month ORDER BY month
    """).fetchall()]
    conn.close()
    return kpis, compliance, skill_gap, trends


try:
    kpis, compliance, skill_gap, trends = load_kpis()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

kpi_df = pd.DataFrame(kpis)
comp_df = pd.DataFrame(compliance)
gap_df = pd.DataFrame(skill_gap)
trend_df = pd.DataFrame(trends)

# ── KPI scorecards ────────────────────────────────────────────────────────────
if not kpi_df.empty:
    st.subheader("Organisation-wide KPIs")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Headcount", f"{kpi_df['headcount'].sum():,}")
    c2.metric("Org Completion Rate", f"{kpi_df['completion_rate'].mean():.1f}%")
    c3.metric("Compliance Rate", f"{kpi_df['required_completion_rate'].mean():.1f}%")
    c4.metric("Avg Hours/Employee", f"{kpi_df['avg_hours_per_employee'].mean():.1f}h")
    c5.metric("Budget Utilisation", f"{kpi_df['budget_utilization'].mean():.1f}%")

    st.divider()

    # Completion rate bar chart
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            kpi_df.sort_values("completion_rate", ascending=True),
            x="completion_rate", y="department", orientation="h",
            color="completion_rate", color_continuous_scale="RdYlGn",
            title="Completion Rate by Department (%)",
            range_color=[0, 100],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            kpi_df, x="avg_hours_per_employee", y="required_completion_rate",
            size="headcount", color="department",
            title="Training Hours vs Required Compliance Rate",
            labels={"avg_hours_per_employee": "Avg Hours/Employee", "required_completion_rate": "Compliance %"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Budget utilisation
    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(
            kpi_df.sort_values("budget_utilization", ascending=False),
            x="department", y=["budget_usd", "spent_usd"],
            barmode="group", title="Training Budget vs Spend ($)",
            labels={"value": "USD", "variable": ""},
            color_discrete_map={"budget_usd": "#93c5fd", "spent_usd": "#1d4ed8"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.treemap(
            kpi_df, path=["department"], values="headcount",
            color="completion_rate", color_continuous_scale="RdYlGn",
            title="Headcount & Completion Rate (treemap)",
            range_color=[50, 100],
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Enrollment trends ─────────────────────────────────────────────────────────
if not trend_df.empty:
    st.subheader("Enrollment & Completion Trends")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend_df["month"], y=trend_df["enrollments"], name="Enrollments",
                             mode="lines+markers", line=dict(color="#3b82f6")))
    fig.add_trace(go.Scatter(x=trend_df["month"], y=trend_df["completions"], name="Completions",
                             mode="lines+markers", line=dict(color="#10b981")))
    fig.update_layout(title="Monthly Enrollments vs Completions", xaxis_title="Month", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

# ── Compliance heatmap ────────────────────────────────────────────────────────
if not comp_df.empty:
    st.subheader("Compliance Completion Heatmap")
    pivot = comp_df.pivot_table(index="department", columns="course_title", values="completion_rate", fill_value=0)
    fig = px.imshow(pivot, color_continuous_scale="RdYlGn", title="Required Course Completion % by Dept",
                    zmin=0, zmax=100, text_auto=True)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# ── Skill gap chart ───────────────────────────────────────────────────────────
if not gap_df.empty:
    st.subheader("Skill Gap Analysis")
    dept_filter = st.selectbox("Filter by department", ["All"] + sorted(gap_df["department"].unique().tolist()))
    display_df = gap_df if dept_filter == "All" else gap_df[gap_df["department"] == dept_filter]

    top_gaps = display_df.nlargest(20, "gap") if "gap" in display_df.columns else display_df.head(20)
    if not top_gaps.empty:
        fig = px.bar(
            top_gaps, x="skill", y="gap", color="department",
            title="Skill Gaps (Self − Manager rating; higher = overrated)",
            labels={"gap": "Gap (Self − Manager)"},
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
