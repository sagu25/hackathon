"""Reports page — generate and view structured reports."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
st.title("📊 Reports")
st.caption("Generate compliance, KPI, and skill gap reports on demand")

report_type = st.selectbox(
    "Report Type",
    ["Compliance Training Report", "Learning KPI Report", "Skill Gap Analysis"],
    key="report_type_select",
)

DEPARTMENTS = ["All Departments", "Engineering", "Sales", "HR", "Finance", "Operations", "Marketing", "Legal", "IT"]
dept = st.selectbox("Department", DEPARTMENTS, key="report_dept_select")
dept_filter = None if dept == "All Departments" else dept

col1, col2, col3 = st.columns([2, 2, 6])
with col1:
    generate = st.button("Generate Report", type="primary", use_container_width=True)
with col2:
    save_btn = st.button("Save Report", use_container_width=True)

# PDF + Word downloads — shown only after a report has been generated
if "current_report" in st.session_state:
    base_name = (st.session_state.current_report.get("title", "report")
                 .replace(" ", "_").replace("—", "-")[:60])
    dl1, dl2 = col3.columns(2)

    try:
        from output.pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(st.session_state.current_report)
        dl1.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=base_name + ".pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as _err:
        dl1.warning(f"PDF unavailable: {_err}")

    try:
        from output.word_generator import generate_word
        docx_bytes = generate_word(st.session_state.current_report)
        dl2.download_button(
            label="Download Word",
            data=docx_bytes,
            file_name=base_name + ".docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    except Exception as _err:
        dl2.warning(f"Word unavailable: {_err}")

if generate or "current_report" in st.session_state:
    if generate:
        try:
            from output.report_generator import (
                generate_compliance_report, generate_learning_kpi_report,
                generate_skill_gap_report, save_report
            )
            with st.spinner("Generating report..."):
                if report_type == "Compliance Training Report":
                    report = generate_compliance_report(dept_filter)
                elif report_type == "Learning KPI Report":
                    report = generate_learning_kpi_report(dept_filter)
                else:
                    report = generate_skill_gap_report(dept_filter)
                st.session_state.current_report = report
        except Exception as e:
            st.error(f"Error generating report: {e}")
            st.stop()

    report = st.session_state.get("current_report", {})
    if not report:
        st.stop()

    if save_btn:
        try:
            from output.report_generator import save_report
            rid = save_report(report)
            st.success(f"Report saved (ID: {rid})")
        except Exception as e:
            st.warning(f"Could not save: {e}")

    st.divider()
    st.subheader(report.get("title", "Report"))
    st.caption(f"Generated: {report.get('generated_at', '')[:19]}")

    rtype = report.get("report_type")

    if rtype == "compliance":
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Compliance Rate", f"{report.get('avg_compliance_rate', 0)}%")
        c2.metric("At-Risk Groups", len(report.get("at_risk_departments", [])))
        c3.metric("Overdue Learners", report.get("total_at_risk", 0))

        if report.get("summary"):
            df = pd.DataFrame(report["summary"])
            if not df.empty:
                st.subheader("Completion by Department & Course")
                st.dataframe(df, use_container_width=True)

                import plotly.express as px
                fig = px.bar(df, x="course_title", y="completion_rate", color="department",
                             barmode="group", title="Completion Rate by Course & Department",
                             labels={"completion_rate": "Completion %", "course_title": "Course"})
                st.plotly_chart(fig, use_container_width=True)

        if report.get("overdue_learners"):
            st.subheader(f"Overdue Learners ({len(report['overdue_learners'])})")
            st.dataframe(pd.DataFrame(report["overdue_learners"]), use_container_width=True)

    elif rtype == "learning_kpis":
        if report.get("kpis"):
            df = pd.DataFrame(report["kpis"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Org Avg Completion", f"{report.get('org_avg_completion', 0)}%")
            c2.metric("Org Avg Hours/Employee", f"{report.get('org_avg_hours', 0)}h")
            c3.metric("Top Dept", report.get("top_performing", {}).get("department", "N/A"))

            st.subheader("Department KPIs")
            st.dataframe(df, use_container_width=True)

            import plotly.express as px
            fig = px.bar(df, x="department", y=["completion_rate", "required_completion_rate"],
                         barmode="group", title="Completion Rate by Department",
                         labels={"value": "%", "variable": "Metric"})
            st.plotly_chart(fig, use_container_width=True)

            fig2 = px.scatter(df, x="avg_hours_per_employee", y="completion_rate",
                              size="headcount", color="department",
                              title="Training Hours vs Completion Rate",
                              labels={"avg_hours_per_employee": "Avg Hours/Employee", "completion_rate": "Completion %"})
            st.plotly_chart(fig2, use_container_width=True)

    elif rtype == "skill_gap":
        if report.get("gaps"):
            df = pd.DataFrame(report["gaps"])
            st.metric("Skill Areas Analysed", report.get("total_skill_areas", 0))

            st.subheader("Skill Gap Detail")
            st.dataframe(df, use_container_width=True)

            import plotly.express as px
            top_gaps = df.nlargest(15, "gap") if "gap" in df.columns else df.head(15)
            if not top_gaps.empty:
                fig = px.bar(top_gaps, x="skill", y="gap", color="department",
                             title="Top Skill Gaps (Self rating − Manager rating)",
                             labels={"gap": "Gap Score"})
                st.plotly_chart(fig, use_container_width=True)

# Saved reports
st.divider()
st.subheader("Saved Reports")
try:
    from output.report_generator import list_saved_reports
    saved = list_saved_reports()
    if saved:
        st.dataframe(pd.DataFrame(saved), use_container_width=True)
    else:
        st.info("No saved reports yet.")
except Exception:
    st.info("Generate and save a report to see it here.")
