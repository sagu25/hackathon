"""Knowledge graph: People → Skills → Roles (NetworkX, simulates Cosmos DB Gremlin)."""
import sqlite3
from functools import lru_cache

import networkx as nx

from config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


@lru_cache(maxsize=1)
def build_graph() -> nx.DiGraph:
    """Build in-memory knowledge graph from Silver layer data."""
    G = nx.DiGraph()
    conn = _conn()

    # Employee nodes
    for emp in conn.execute("SELECT employee_id, name, department, role, grade_level FROM employees WHERE employment_status != 'Terminated'"):
        G.add_node(emp["employee_id"], type="employee", **dict(emp))

    # Department nodes
    for dept in conn.execute("SELECT DISTINCT department FROM employees"):
        G.add_node(dept["department"], type="department")

    # Skill nodes
    for skill_row in conn.execute("SELECT DISTINCT skill FROM skill_assessments"):
        G.add_node(skill_row["skill"], type="skill")

    # Edges: employee → department, employee → skill
    for emp in conn.execute("SELECT employee_id, department FROM employees WHERE employment_status != 'Terminated'"):
        G.add_edge(emp["employee_id"], emp["department"], relation="belongs_to")

    for s in conn.execute("SELECT employee_id, skill, proficiency_level FROM skill_assessments"):
        G.add_edge(s["employee_id"], s["skill"], relation="has_skill", level=s["proficiency_level"])

    # Manager → report edges
    for emp in conn.execute("SELECT employee_id, manager_id FROM employees WHERE manager_id IS NOT NULL AND employment_status != 'Terminated'"):
        if emp["manager_id"] in G:
            G.add_edge(emp["manager_id"], emp["employee_id"], relation="manages")

    conn.close()
    return G


def invalidate_graph():
    build_graph.cache_clear()


def employees_with_skill(skill: str) -> list[dict]:
    """Find all employees who have a given skill."""
    G = build_graph()
    result = []
    for node, data in G.nodes(data=True):
        if data.get("type") == "employee" and G.has_edge(node, skill):
            edge = G.edges[node, skill]
            result.append({**data, "proficiency": edge.get("level", "Unknown")})
    return result


def skill_gap_for_department(department: str) -> list[dict]:
    """Return skills present in a department and their coverage."""
    G = build_graph()
    dept_employees = [n for n, d in G.nodes(data=True) if d.get("type") == "employee" and d.get("department") == department]
    skill_counts: dict[str, int] = {}
    for emp in dept_employees:
        for _, skill in G.out_edges(emp):
            if G.nodes[skill].get("type") == "skill":
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
    total = len(dept_employees) or 1
    return sorted(
        [{"skill": s, "employees_with_skill": c, "coverage_pct": round(c / total * 100, 1)} for s, c in skill_counts.items()],
        key=lambda x: x["coverage_pct"],
    )


def shortest_skill_path(employee_id: str, target_skill: str) -> dict:
    """Find what courses/skills an employee needs to reach a target skill."""
    G = build_graph()
    if not G.has_node(employee_id):
        return {"error": f"Employee {employee_id} not found in graph"}
    if G.has_edge(employee_id, target_skill):
        return {"message": f"Employee already has skill: {target_skill}", "path": []}
    try:
        path = nx.shortest_path(G.to_undirected(), employee_id, target_skill)
        return {"path": path, "hops": len(path) - 1}
    except nx.NetworkXNoPath:
        return {"message": "No learning path found", "suggestion": f"Enrol in courses covering {target_skill}"}


def get_team_under_manager(manager_id: str) -> list[str]:
    """Return all employee IDs reporting (directly or indirectly) to a manager."""
    G = build_graph()
    if not G.has_node(manager_id):
        return []
    manages_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "manages"]
    manages_graph = nx.DiGraph(manages_edges)
    if not manages_graph.has_node(manager_id):
        return []
    return list(nx.descendants(manages_graph, manager_id))
