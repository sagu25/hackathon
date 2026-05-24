"""All tool definitions available to agents (OpenAI function-calling format)."""

LMS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dept_kpis",
            "description": "Get learning KPIs for one or all departments (completion rate, training hours, budget).",
            "parameters": {
                "type": "object",
                "properties": {"department": {"type": "string", "description": "Department name, or omit for all"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_compliance_summary",
            "description": "Get required-course completion rates by department.",
            "parameters": {
                "type": "object",
                "properties": {"department": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_learners",
            "description": "Get employees who haven't completed required/compliance courses.",
            "parameters": {
                "type": "object",
                "properties": {"department": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_enrollments",
            "description": "Get all course enrollments for a specific employee.",
            "parameters": {
                "type": "object",
                "required": ["employee_id"],
                "properties": {"employee_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_catalog",
            "description": "Get the course catalog, optionally filtered by category.",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
            },
        },
    },
]

HR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_employee_profile",
            "description": "Get a full employee profile including skills and training history.",
            "parameters": {
                "type": "object",
                "required": ["employee_id"],
                "properties": {"employee_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_skill_gap_report",
            "description": "Get skill gap analysis showing divergence between self and manager ratings.",
            "parameters": {
                "type": "object",
                "properties": {"department": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workforce_summary",
            "description": "Get headcount and workforce composition by department.",
            "parameters": {
                "type": "object",
                "properties": {"department": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_employees",
            "description": "Search employees by name, department, or role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "department": {"type": "string"},
                    "role": {"type": "string"},
                },
            },
        },
    },
]

POWERBI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_semantic_model",
            "description": "Query a Power BI dataset. Use list_datasets to see options.",
            "parameters": {
                "type": "object",
                "required": ["dataset_name"],
                "properties": {
                    "dataset_name": {"type": "string", "enum": ["compliance_summary", "dept_kpis", "skill_gap", "enrollment_trends", "top_courses"]},
                    "filters": {"type": "string", "description": "JSON string of filter key-values"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_report",
            "description": "Generate a Power BI report from a dataset.",
            "parameters": {
                "type": "object",
                "required": ["title", "dataset_name", "chart_type"],
                "properties": {
                    "title": {"type": "string"},
                    "dataset_name": {"type": "string"},
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "table", "scorecard", "map"]},
                    "filters": {"type": "string"},
                },
            },
        },
    },
]

AUTOMATE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_flow",
            "description": "Create a Power Automate flow from natural language description.",
            "parameters": {
                "type": "object",
                "required": ["name", "description", "trigger_type", "actions"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "trigger_type": {"type": "string"},
                    "actions": {"type": "string", "description": "JSON array of action description strings"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flow_from_template",
            "description": "Create a flow from a pre-defined template.",
            "parameters": {
                "type": "object",
                "required": ["template_id"],
                "properties": {
                    "template_id": {
                        "type": "string",
                        "enum": ["compliance_reminder", "completion_notification", "weekly_report_delivery", "skill_gap_alert"],
                    },
                },
            },
        },
    },
]

ALL_TOOLS = LMS_TOOLS + HR_TOOLS + POWERBI_TOOLS + AUTOMATE_TOOLS
