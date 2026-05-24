"""Execute tool calls dispatched by agent LLM decisions."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.db_tools import query, query_one, to_json
from mcp_servers.lms_server import (
    get_completions, get_enrollments, get_course_catalog,
    get_compliance_summary, get_dept_kpis, get_overdue_learners,
)
from mcp_servers.hr_server import (
    get_employee_profile, get_org_hierarchy, get_role_skills,
    get_workforce_summary, get_skill_gap_report, search_employees,
)
from mcp_servers.powerbi_server import query_semantic_model, create_report, embed_visual, list_datasets
from mcp_servers.automate_server import create_flow, get_flow_from_template, list_flows, trigger_flow


TOOL_MAP = {
    # LMS
    "get_completions": get_completions,
    "get_enrollments": get_enrollments,
    "get_course_catalog": get_course_catalog,
    "get_compliance_summary": get_compliance_summary,
    "get_dept_kpis": get_dept_kpis,
    "get_overdue_learners": get_overdue_learners,
    # HR
    "get_employee_profile": get_employee_profile,
    "get_org_hierarchy": get_org_hierarchy,
    "get_role_skills": get_role_skills,
    "get_workforce_summary": get_workforce_summary,
    "get_skill_gap_report": get_skill_gap_report,
    "search_employees": search_employees,
    # Power BI
    "list_datasets": list_datasets,
    "query_semantic_model": query_semantic_model,
    "create_report": create_report,
    "embed_visual": embed_visual,
    # Power Automate
    "list_flows": list_flows,
    "trigger_flow": trigger_flow,
    "create_flow": create_flow,
    "get_flow_from_template": get_flow_from_template,
}


def execute_tool_call(name: str, arguments: str | dict) -> str:
    """Execute a named tool with JSON arguments. Returns string result."""
    fn = TOOL_MAP.get(name)
    if fn is None:
        return to_json({"error": f"Unknown tool: {name}"})
    args = arguments if isinstance(arguments, dict) else json.loads(arguments or "{}")
    try:
        return fn(**args)
    except Exception as exc:
        return to_json({"error": str(exc), "tool": name, "args": args})
