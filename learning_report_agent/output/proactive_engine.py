"""Proactive Engine — daily scan, threshold watchers, manager briefings."""
import sqlite3
from datetime import datetime

from config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


COMPLIANCE_THRESHOLD = 80.0  # % below which we flag a dept
OVERDUE_THRESHOLD = 5        # count of overdue learners before alerting


def daily_scan() -> dict:
    """Run a daily scan and return proactive alerts."""
    alerts = []
    conn = _conn()

    # Check depts below compliance threshold
    low_compliance = conn.execute(
        "SELECT department, required_completion_rate FROM gold_dept_learning_kpis "
        "WHERE required_completion_rate < ? ORDER BY required_completion_rate",
        (COMPLIANCE_THRESHOLD,)
    ).fetchall()
    for row in low_compliance:
        alerts.append({
            "type": "compliance_risk",
            "severity": "high" if row["required_completion_rate"] < 60 else "medium",
            "department": row["department"],
            "message": f"{row['department']} compliance rate is {row['required_completion_rate']}% — below {COMPLIANCE_THRESHOLD}% threshold",
        })

    # Check overdue counts per dept
    overdue = conn.execute("""
        SELECT e.department, COUNT(*) as overdue_count
        FROM lms_enrollments l JOIN employees e ON l.employee_id=e.employee_id
        WHERE l.is_required=1 AND l.status != 'Completed'
          AND e.employment_status = 'Active'
        GROUP BY e.department HAVING overdue_count > ?
        ORDER BY overdue_count DESC
    """, (OVERDUE_THRESHOLD,)).fetchall()
    for row in overdue:
        alerts.append({
            "type": "overdue_learners",
            "severity": "high" if row["overdue_count"] > 20 else "medium",
            "department": row["department"],
            "message": f"{row['department']} has {row['overdue_count']} employees with overdue required training",
        })

    conn.close()

    return {
        "scan_time": datetime.now().isoformat(),
        "total_alerts": len(alerts),
        "high_severity": sum(1 for a in alerts if a["severity"] == "high"),
        "alerts": alerts,
    }


def get_manager_briefing(manager_id: str) -> dict:
    """Generate a briefing for a specific manager covering their team."""
    conn = _conn()
    team = conn.execute(
        "SELECT employee_id, name FROM employees WHERE manager_id=? AND employment_status='Active'",
        (manager_id,)
    ).fetchall()
    team_ids = [r["employee_id"] for r in team]

    if not team_ids:
        conn.close()
        return {"error": f"No active reports found for manager {manager_id}"}

    placeholders = ",".join("?" * len(team_ids))
    completions = conn.execute(f"""
        SELECT status, COUNT(*) as cnt FROM lms_enrollments
        WHERE employee_id IN ({placeholders})
        GROUP BY status
    """, team_ids).fetchall()

    overdue = conn.execute(f"""
        SELECT e.name, l.course_title FROM lms_enrollments l
        JOIN employees e ON l.employee_id=e.employee_id
        WHERE l.employee_id IN ({placeholders}) AND l.is_required=1 AND l.status!='Completed'
    """, team_ids).fetchall()

    conn.close()

    comp_map = {r["status"]: r["cnt"] for r in completions}
    total = sum(comp_map.values())
    completed = comp_map.get("Completed", 0)

    return {
        "manager_id": manager_id,
        "team_size": len(team_ids),
        "generated_at": datetime.now().isoformat(),
        "team_completion_rate": round(completed / total * 100, 1) if total else 0,
        "overdue_required_courses": [dict(r) for r in overdue],
        "summary": (
            f"Your team of {len(team_ids)} has a {round(completed/total*100,1) if total else 0}% overall completion rate. "
            f"{len(overdue)} required-course enrollments are overdue."
        ),
    }
