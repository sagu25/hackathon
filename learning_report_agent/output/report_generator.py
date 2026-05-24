"""Report Generator — builds structured HTML/JSON reports from data."""
import json
import sqlite3
from datetime import datetime

from config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def generate_compliance_report(department: str | None = None) -> dict:
    conn = _conn()
    if department:
        rows = conn.execute("SELECT * FROM gold_compliance_summary WHERE department=? ORDER BY completion_rate", (department,)).fetchall()
        overdue = conn.execute(
            "SELECT e.name, e.role, l.course_title, l.status FROM lms_enrollments l "
            "JOIN employees e ON l.employee_id=e.employee_id "
            "WHERE l.is_required=1 AND l.status!='Completed' AND e.department=? LIMIT 20",
            (department,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gold_compliance_summary ORDER BY department, completion_rate").fetchall()
        overdue = conn.execute(
            "SELECT e.name, e.department, e.role, l.course_title, l.status FROM lms_enrollments l "
            "JOIN employees e ON l.employee_id=e.employee_id "
            "WHERE l.is_required=1 AND l.status!='Completed' LIMIT 50"
        ).fetchall()
    conn.close()

    summary_data = [dict(r) for r in rows]
    overdue_data = [dict(r) for r in overdue]

    at_risk = [r for r in summary_data if r["completion_rate"] < 80]

    return {
        "report_type": "compliance",
        "title": f"Compliance Training Report — {department or 'All Departments'}",
        "generated_at": datetime.now().isoformat(),
        "summary": summary_data,
        "overdue_learners": overdue_data,
        "at_risk_departments": at_risk,
        "total_at_risk": len(overdue_data),
        "avg_compliance_rate": round(sum(r["completion_rate"] or 0 for r in summary_data) / len(summary_data), 1) if summary_data else 0,
    }


def generate_learning_kpi_report(department: str | None = None) -> dict:
    conn = _conn()
    if department:
        rows = conn.execute("SELECT * FROM gold_dept_learning_kpis WHERE department=?", (department,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gold_dept_learning_kpis ORDER BY completion_rate DESC").fetchall()
    conn.close()

    kpi_data = [dict(r) for r in rows]
    if not kpi_data:
        return {"error": "No KPI data found"}

    top_dept = max(kpi_data, key=lambda x: x["completion_rate"] or 0)
    bottom_dept = min(kpi_data, key=lambda x: x["completion_rate"] or 0)

    return {
        "report_type": "learning_kpis",
        "title": f"Learning KPI Report — {department or 'All Departments'}",
        "generated_at": datetime.now().isoformat(),
        "kpis": kpi_data,
        "top_performing": top_dept,
        "needs_attention": bottom_dept,
        "org_avg_completion": round(sum(r["completion_rate"] or 0 for r in kpi_data) / len(kpi_data), 1),
        "org_avg_hours": round(sum(r["avg_hours_per_employee"] or 0 for r in kpi_data) / len(kpi_data), 1),
    }


def generate_skill_gap_report(department: str | None = None) -> dict:
    conn = _conn()
    if department:
        rows = conn.execute(
            "SELECT * FROM gold_skill_gap WHERE department=? ORDER BY ABS(gap) DESC",
            (department,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gold_skill_gap ORDER BY ABS(gap) DESC LIMIT 40").fetchall()
    conn.close()

    gap_data = [dict(r) for r in rows]
    overrated = [g for g in gap_data if (g["gap"] or 0) > 0.5]
    underrated = [g for g in gap_data if (g["gap"] or 0) < -0.5]

    return {
        "report_type": "skill_gap",
        "title": f"Skill Gap Analysis — {department or 'Organisation-Wide'}",
        "generated_at": datetime.now().isoformat(),
        "gaps": gap_data,
        "overrated_skills": overrated[:5],
        "underrated_skills": underrated[:5],
        "total_skill_areas": len(set(g["skill"] for g in gap_data)),
    }


def save_report(report: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO generated_reports (report_name, report_type, query, content) VALUES (?,?,?,?)",
        (report.get("title", "Untitled"), report.get("report_type", "unknown"), "", json.dumps(report, default=str))
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    return report_id


def list_saved_reports() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT id, report_name, report_type, created_at FROM generated_reports ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]
