"""Dashboards page — interactive KPI visualisations with full stakeholder filters."""
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
st.caption("Live KPI visualisations — filter by team, time period, course, or skill domain")

if not DB_PATH.exists():
    st.warning("Database not initialised. Go to Admin → Setup.")
    st.stop()


@st.cache_data(ttl=300)
def load_all():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    kpis       = pd.DataFrame([dict(r) for r in conn.execute("SELECT * FROM gold_dept_learning_kpis").fetchall()])
    compliance = pd.DataFrame([dict(r) for r in conn.execute("SELECT * FROM gold_compliance_summary").fetchall()])
    skill_gap  = pd.DataFrame([dict(r) for r in conn.execute("SELECT * FROM gold_skill_gap").fetchall()])

    # Raw enrollments for time-period and course filtering
    enrollments = pd.DataFrame([dict(r) for r in conn.execute(
        "SELECT e.department, l.course_id, l.course_title, l.course_category, "
        "l.enrolled_date, l.status, l.score, l.duration_hours, l.is_required "
        "FROM lms_enrollments l JOIN employees e ON l.employee_id=e.employee_id"
    ).fetchall()])

    conn.close()
    return kpis, compliance, skill_gap, enrollments


try:
    kpi_df, comp_df, gap_df, enroll_df = load_all()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Convert date column
enroll_df["enrolled_date"] = pd.to_datetime(enroll_df["enrolled_date"], errors="coerce")

# ── Global filters sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    all_depts   = sorted(enroll_df["department"].dropna().unique().tolist())
    all_courses = sorted(enroll_df["course_title"].dropna().unique().tolist())

    sel_depts = st.multiselect("Department / Team", all_depts, default=[], key="f_dept",
                               placeholder="All departments")

    all_months = sorted(enroll_df["enrolled_date"].dt.to_period("M").dropna().unique().astype(str).tolist())
    if all_months:
        start_month = st.selectbox("From month", all_months, index=0, key="f_start")
        end_month   = st.selectbox("To month",   all_months, index=len(all_months)-1, key="f_end")
    else:
        start_month = end_month = None

    sel_courses = st.multiselect("Course", all_courses, default=[], key="f_course",
                                 placeholder="All courses")

    sel_category = st.selectbox(
        "Course category",
        ["All"] + sorted(enroll_df["course_category"].dropna().unique().tolist()),
        key="f_cat",
    )

    st.divider()
    st.caption("Filters apply to all charts below.")


# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = enroll_df.copy()

if sel_depts:
    filtered = filtered[filtered["department"].isin(sel_depts)]
    kpi_df   = kpi_df[kpi_df["department"].isin(sel_depts)]
    comp_df  = comp_df[comp_df["department"].isin(sel_depts)]
    gap_df   = gap_df[gap_df["department"].isin(sel_depts)]

if start_month and end_month:
    filtered = filtered[
        (filtered["enrolled_date"].dt.to_period("M").astype(str) >= start_month) &
        (filtered["enrolled_date"].dt.to_period("M").astype(str) <= end_month)
    ]

if sel_courses:
    filtered = filtered[filtered["course_title"].isin(sel_courses)]
    comp_df  = comp_df[comp_df["course_title"].isin(sel_courses)]

if sel_category != "All":
    filtered = filtered[filtered["course_category"] == sel_category]

# ── Active filter chips ───────────────────────────────────────────────────────
active = []
if sel_depts:    active.append(f"Dept: {', '.join(sel_depts)}")
if start_month:  active.append(f"Period: {start_month} → {end_month}")
if sel_courses:  active.append(f"Courses: {len(sel_courses)} selected")
if sel_category != "All": active.append(f"Category: {sel_category}")

if active:
    st.info("Active filters: " + "  |  ".join(active))

# ── KPI scorecards ────────────────────────────────────────────────────────────
st.subheader("Organisation-wide KPIs")

total_enrolled   = len(filtered)
total_completed  = (filtered["status"] == "Completed").sum()
comp_rate        = round(total_completed / total_enrolled * 100, 1) if total_enrolled else 0
avg_score        = round(filtered.loc[filtered["score"].notna(), "score"].mean(), 1) if not filtered.empty else 0
avg_hours        = round(filtered.loc[filtered["status"] == "Completed", "duration_hours"].mean(), 1) if not filtered.empty else 0
req_comp_rate    = round(
    filtered.loc[(filtered["is_required"]==1) & (filtered["status"]=="Completed")].shape[0] /
    max(filtered[filtered["is_required"]==1].shape[0], 1) * 100, 1
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Enrollments",        f"{total_enrolled:,}")
c2.metric("Overall Completion", f"{comp_rate}%")
c3.metric("Compliance Rate",    f"{req_comp_rate}%")
c4.metric("Avg Score",          f"{avg_score}")
c5.metric("Avg Hours (Completed)", f"{avg_hours}h")

st.divider()

# ── Completion by department ──────────────────────────────────────────────────
if not filtered.empty:
    dept_summary = (
        filtered.groupby("department")
        .apply(lambda g: pd.Series({
            "enrollments":       len(g),
            "completions":       (g["status"] == "Completed").sum(),
            "completion_rate":   round((g["status"] == "Completed").mean() * 100, 1),
            "avg_score":         round(g.loc[g["score"].notna(), "score"].mean(), 1),
        }))
        .reset_index()
    )

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            dept_summary.sort_values("completion_rate"),
            x="completion_rate", y="department", orientation="h",
            color="completion_rate", color_continuous_scale="RdYlGn",
            title="Completion Rate by Department (%)", range_color=[0, 100],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not kpi_df.empty:
            fig = px.scatter(
                kpi_df, x="avg_hours_per_employee", y="required_completion_rate",
                size="headcount", color="department",
                title="Training Hours vs Compliance Rate",
                labels={"avg_hours_per_employee": "Avg Hrs/Employee",
                        "required_completion_rate": "Compliance %"},
            )
            st.plotly_chart(fig, use_container_width=True)

# ── Enrollment trends (time-period filtered) ──────────────────────────────────
st.subheader("Enrollment & Completion Trends")
if not filtered.empty and filtered["enrolled_date"].notna().any():
    trend = (
        filtered.assign(month=filtered["enrolled_date"].dt.to_period("M").astype(str))
        .groupby("month")
        .apply(lambda g: pd.Series({
            "enrollments": len(g),
            "completions": (g["status"] == "Completed").sum(),
        }))
        .reset_index()
        .sort_values("month")
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["month"], y=trend["enrollments"],
                             name="Enrollments", mode="lines+markers",
                             line=dict(color="#3b82f6")))
    fig.add_trace(go.Scatter(x=trend["month"], y=trend["completions"],
                             name="Completions", mode="lines+markers",
                             line=dict(color="#10b981")))
    fig.update_layout(title="Monthly Enrollments vs Completions",
                      xaxis_title="Month", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No trend data for selected filters.")

# ── Compliance heatmap (course-filtered) ─────────────────────────────────────
st.subheader("Compliance Completion Heatmap")
st.caption("Filter by course or category using the sidebar.")

disp_comp = comp_df.copy()
if not disp_comp.empty:
    pivot = disp_comp.pivot_table(
        index="department", columns="course_title",
        values="completion_rate", fill_value=0,
    )
    if not pivot.empty:
        fig = px.imshow(pivot, color_continuous_scale="RdYlGn",
                        title="Required Course Completion % by Department",
                        zmin=0, zmax=100, text_auto=True)
        fig.update_layout(height=max(350, len(pivot) * 45))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No compliance data for selected filters.")

# ── Course-level breakdown ────────────────────────────────────────────────────
st.subheader("Course-level Completion")
if not filtered.empty:
    course_summary = (
        filtered.groupby(["course_title", "course_category"])
        .apply(lambda g: pd.Series({
            "enrollments":     len(g),
            "completions":     (g["status"] == "Completed").sum(),
            "completion_rate": round((g["status"] == "Completed").mean() * 100, 1),
            "avg_score":       round(g.loc[g["score"].notna(), "score"].mean(), 1),
        }))
        .reset_index()
        .sort_values("completion_rate", ascending=False)
    )
    top_n = st.slider("Show top N courses", 5, 30, 15, key="top_n_courses")
    fig = px.bar(
        course_summary.head(top_n),
        x="completion_rate", y="course_title", orientation="h",
        color="course_category",
        title=f"Top {top_n} Courses by Completion Rate",
        labels={"completion_rate": "Completion %", "course_title": "Course"},
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Budget (unaffected by enrollment filters) ─────────────────────────────────
if not kpi_df.empty:
    st.subheader("Training Budget vs Spend")
    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(
            kpi_df.sort_values("budget_utilization", ascending=False),
            x="department", y=["budget_usd", "spent_usd"],
            barmode="group", title="Training Budget vs Spend by Department ($)",
            labels={"value": "USD", "variable": ""},
            color_discrete_map={"budget_usd": "#93c5fd", "spent_usd": "#1d4ed8"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        fig = px.treemap(
            kpi_df, path=["department"], values="headcount",
            color="completion_rate", color_continuous_scale="RdYlGn",
            title="Headcount & Completion Rate (treemap)", range_color=[50, 100],
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Skill gap (skill domain filter) ──────────────────────────────────────────
st.subheader("Skill Gap Analysis")
if not gap_df.empty:
    all_skills = sorted(gap_df["skill"].unique().tolist())
    sel_skills = st.multiselect("Filter by skill domain", all_skills, default=[], key="f_skill",
                                placeholder="All skills")

    disp_gap = gap_df if not sel_skills else gap_df[gap_df["skill"].isin(sel_skills)]
    top_gaps = disp_gap.nlargest(20, "gap") if "gap" in disp_gap.columns else disp_gap.head(20)

    if not top_gaps.empty:
        fig = px.bar(
            top_gaps, x="skill", y="gap", color="department",
            title="Skill Gaps (Self − Manager rating)",
            labels={"gap": "Gap score"},
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
