"""Power Automate MCP Server — list, trigger, and generate PA flows."""
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from mcp_servers.db_tools import query, execute, to_json
from config import DB_PATH

mcp = FastMCP("Power Automate Server")

FLOW_TEMPLATES = {
    "compliance_reminder": {
        "name": "Compliance Training Reminder",
        "description": "Sends reminders to employees who haven't completed required courses",
        "trigger": "Scheduled (weekly)",
        "actions": ["Query LMS for non-compliant employees", "Send Teams/email reminder", "Log to SharePoint"],
    },
    "completion_notification": {
        "name": "Course Completion Notification",
        "description": "Notifies manager when employee completes a course",
        "trigger": "LMS event: course_completed",
        "actions": ["Get employee details", "Get manager email", "Send congratulations email"],
    },
    "weekly_report_delivery": {
        "name": "Weekly Learning Report Delivery",
        "description": "Emails weekly learning summary to department heads",
        "trigger": "Scheduled (Monday 8am)",
        "actions": ["Run report query", "Generate PDF", "Email to distribution list"],
    },
    "skill_gap_alert": {
        "name": "Skill Gap Alert",
        "description": "Alerts L&D team when skill gaps exceed threshold",
        "trigger": "Scheduled (monthly)",
        "actions": ["Query skill assessments", "Calculate gaps", "Create Teams notification"],
    },
}


@mcp.tool()
def list_flows() -> str:
    """List all saved Power Automate flows."""
    saved = query("SELECT id, flow_name, description, trigger_type, status, created_at FROM generated_flows ORDER BY created_at DESC")
    templates = [{"template_id": k, **v} for k, v in FLOW_TEMPLATES.items()]
    return to_json({"saved_flows": saved, "available_templates": templates})


@mcp.tool()
def trigger_flow(flow_id: int) -> str:
    """Trigger a saved flow (simulated run)."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM generated_flows WHERE id=?", (flow_id,)).fetchone()
    conn.close()
    if not row:
        return to_json({"error": f"Flow {flow_id} not found"})
    return to_json({
        "run_id": f"RUN_{flow_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "flow_id": flow_id,
        "status": "triggered",
        "message": "Flow triggered successfully (mock). In production, this calls the Power Automate REST API.",
    })


@mcp.tool()
def create_flow(
    name: str,
    description: str,
    trigger_type: str,
    actions: str,  # JSON list of action strings
) -> str:
    """Generate and save a Power Automate flow definition."""
    action_list = json.loads(actions) if isinstance(actions, str) else actions
    flow_json = {
        "definition": {
            "contentVersion": "1.0.0.0",
            "name": name,
            "description": description,
            "triggers": {
                "manual_or_scheduled": {
                    "type": trigger_type,
                    "recurrence": {"frequency": "Week", "interval": 1} if "week" in trigger_type.lower() else {},
                }
            },
            "actions": {
                f"step_{i+1}_{act[:20].replace(' ', '_')}": {
                    "type": "Action",
                    "description": act,
                    "inputs": {},
                }
                for i, act in enumerate(action_list)
            },
        },
        "_generated_by": "Learning Report Agent",
        "_generated_at": datetime.now().isoformat(),
    }

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO generated_flows (flow_name, description, trigger_type, flow_json, status) VALUES (?,?,?,?,?)",
        (name, description, trigger_type, json.dumps(flow_json), "draft")
    )
    flow_id = cur.lastrowid
    conn.commit()
    conn.close()

    return to_json({
        "flow_id": flow_id,
        "flow_name": name,
        "status": "created",
        "flow_definition": flow_json,
        "message": "Flow created and saved. Review in Flow Library, then trigger to activate.",
    })


@mcp.tool()
def get_flow_from_template(template_id: str) -> str:
    """Generate a flow using a pre-defined template."""
    tpl = FLOW_TEMPLATES.get(template_id)
    if not tpl:
        return to_json({"error": f"Unknown template. Available: {list(FLOW_TEMPLATES.keys())}"})
    return create_flow(
        name=tpl["name"],
        description=tpl["description"],
        trigger_type=tpl["trigger"],
        actions=json.dumps(tpl["actions"]),
    )


if __name__ == "__main__":
    mcp.run()
