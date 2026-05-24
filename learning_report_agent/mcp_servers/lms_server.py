"""LMS MCP Server — exposes learning data as tools."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from mcp_servers.db_tools import query, query_one, to_json

mcp = FastMCP("LMS Server")


@mcp.tool()
def get_completions(
    department: str | None = None,
    course_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> str:
    """Get LMS completion records. Filter by department, course_id, or status."""
    conditions, params = [], []
    if department:
        conditions.append("e.department = ?"); params.append(department)
    if course_id:
        conditions.append("l.course_id = ?"); params.append(course_id)
    if status:
        conditions.append("l.status = ?"); params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT l.*, e.department, e.name, e.role
        FROM lms_enrollments l JOIN employees e ON l.employee_id = e.employee_id
        {where} LIMIT ?
    """
    return to_json(query(sql, tuple(params) + (limit,)))


@mcp.tool()
def get_enrollments(employee_id: str) -> str:
    """Get all enrollments for a specific employee."""
    return to_json(query(
        "SELECT * FROM lms_enrollments WHERE employee_id = ? ORDER BY enrolled_date DESC",
        (employee_id,)
    ))


@mcp.tool()
def get_course_catalog(category: str | None = None) -> str:
    """Get the full course catalog, optionally filtered by category."""
    if category:
        return to_json(query("SELECT * FROM course_catalog WHERE category = ?", (category,)))
    return to_json(query("SELECT * FROM course_catalog"))


@mcp.tool()
def get_compliance_summary(department: str | None = None) -> str:
    """Get compliance training completion summary by department."""
    if department:
        return to_json(query(
            "SELECT * FROM gold_compliance_summary WHERE department = ? ORDER BY completion_rate",
            (department,)
        ))
    return to_json(query("SELECT * FROM gold_compliance_summary ORDER BY department, completion_rate"))


@mcp.tool()
def get_dept_kpis(department: str | None = None) -> str:
    """Get learning KPIs for a department or all departments."""
    if department:
        return to_json(query_one("SELECT * FROM gold_dept_learning_kpis WHERE department = ?", (department,)))
    return to_json(query("SELECT * FROM gold_dept_learning_kpis ORDER BY completion_rate DESC"))


@mcp.tool()
def get_overdue_learners(department: str | None = None) -> str:
    """Get employees who have not completed required courses (compliance risk)."""
    conditions = ["l.is_required = 1", "l.status != 'Completed'"]
    params = []
    if department:
        conditions.append("e.department = ?"); params.append(department)
    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT e.employee_id, e.name, e.department, e.role,
               l.course_id, l.course_title, l.enrolled_date, l.status
        FROM lms_enrollments l JOIN employees e ON l.employee_id = e.employee_id
        {where}
        ORDER BY e.department, e.name
    """
    return to_json(query(sql, tuple(params)))


if __name__ == "__main__":
    mcp.run()
