"""HR MCP Server — exposes workforce data as tools."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from mcp_servers.db_tools import query, query_one, to_json

mcp = FastMCP("HR Server")


@mcp.tool()
def get_employee_profile(employee_id: str) -> str:
    """Get a specific employee's full profile."""
    emp = query_one("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    if not emp:
        return to_json({"error": f"Employee {employee_id} not found"})
    skills = query("SELECT * FROM skill_assessments WHERE employee_id = ?", (employee_id,))
    enrollments = query(
        "SELECT course_title, status, score, completion_date FROM lms_enrollments WHERE employee_id = ?",
        (employee_id,)
    )
    return to_json({"profile": emp, "skills": skills, "training": enrollments})


@mcp.tool()
def get_org_hierarchy(department: str | None = None) -> str:
    """Get org hierarchy — employees with their managers and direct reports."""
    if department:
        return to_json(query(
            "SELECT employee_id, name, role, manager_id, grade_level, employment_status "
            "FROM employees WHERE department = ? AND employment_status != 'Terminated' ORDER BY grade_level",
            (department,)
        ))
    return to_json(query(
        "SELECT employee_id, name, department, role, manager_id, grade_level "
        "FROM employees WHERE employment_status != 'Terminated' ORDER BY department, grade_level"
    ))


@mcp.tool()
def get_role_skills(role: str) -> str:
    """Get skill profiles for employees in a specific role."""
    return to_json(query("""
        SELECT s.skill, s.proficiency_level, AVG(s.self_rated) as avg_self,
               AVG(s.manager_rated) as avg_manager, COUNT(*) as employees
        FROM skill_assessments s
        JOIN employees e ON s.employee_id = e.employee_id
        WHERE e.role = ?
        GROUP BY s.skill, s.proficiency_level
        ORDER BY s.skill
    """, (role,)))


@mcp.tool()
def get_workforce_summary(department: str | None = None) -> str:
    """Get headcount and workforce composition summary."""
    if department:
        rows = query(
            "SELECT department, employment_status, COUNT(*) as count FROM employees "
            "WHERE department = ? GROUP BY employment_status",
            (department,)
        )
    else:
        rows = query(
            "SELECT department, employment_status, COUNT(*) as count FROM employees "
            "GROUP BY department, employment_status ORDER BY department"
        )
    return to_json(rows)


@mcp.tool()
def get_skill_gap_report(department: str | None = None) -> str:
    """Get skill gap analysis showing where manager ratings diverge from self-ratings."""
    if department:
        return to_json(query(
            "SELECT * FROM gold_skill_gap WHERE department = ? ORDER BY gap DESC",
            (department,)
        ))
    return to_json(query(
        "SELECT * FROM gold_skill_gap ORDER BY ABS(gap) DESC LIMIT 50"
    ))


@mcp.tool()
def search_employees(name: str | None = None, department: str | None = None, role: str | None = None) -> str:
    """Search employees by name, department, or role."""
    conditions, params = [], []
    if name:
        conditions.append("name LIKE ?"); params.append(f"%{name}%")
    if department:
        conditions.append("department = ?"); params.append(department)
    if role:
        conditions.append("role LIKE ?"); params.append(f"%{role}%")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return to_json(query(f"SELECT * FROM employees {where} LIMIT 50", tuple(params)))


if __name__ == "__main__":
    mcp.run()
