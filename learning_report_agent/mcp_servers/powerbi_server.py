"""Power BI MCP Server — query datasets and simulate report generation."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from mcp_servers.db_tools import query, to_json

mcp = FastMCP("Power BI Server")

AVAILABLE_DATASETS = {
    "compliance_summary": "Compliance training completion by department and course",
    "dept_kpis": "Learning KPIs per department (completion rate, hours, budget)",
    "skill_gap": "Skill gap analysis across departments",
    "enrollment_trends": "Enrollment and completion trends over time",
    "top_courses": "Top courses by completion rate and enrollment",
}


@mcp.tool()
def list_datasets() -> str:
    """List available Power BI semantic model datasets."""
    return to_json(AVAILABLE_DATASETS)


@mcp.tool()
def query_semantic_model(dataset_name: str, filters: str = "{}") -> str:
    """Query a Power BI semantic model dataset. filters is a JSON string."""
    f = json.loads(filters) if filters else {}

    if dataset_name == "compliance_summary":
        dept = f.get("department")
        if dept:
            return to_json(query("SELECT * FROM gold_compliance_summary WHERE department=?", (dept,)))
        return to_json(query("SELECT * FROM gold_compliance_summary ORDER BY completion_rate"))

    elif dataset_name == "dept_kpis":
        return to_json(query("SELECT * FROM gold_dept_learning_kpis ORDER BY completion_rate DESC"))

    elif dataset_name == "skill_gap":
        dept = f.get("department")
        if dept:
            return to_json(query("SELECT * FROM gold_skill_gap WHERE department=? ORDER BY ABS(gap) DESC", (dept,)))
        return to_json(query("SELECT * FROM gold_skill_gap ORDER BY ABS(gap) DESC LIMIT 30"))

    elif dataset_name == "enrollment_trends":
        return to_json(query("""
            SELECT strftime('%Y-%m', enrolled_date) as month,
                   COUNT(*) as enrollments,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completions
            FROM lms_enrollments
            GROUP BY month ORDER BY month
        """))

    elif dataset_name == "top_courses":
        return to_json(query("""
            SELECT course_title, course_category,
                   COUNT(*) as enrollments,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completions,
                   ROUND(SUM(CASE WHEN status='Completed' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as completion_rate,
                   ROUND(AVG(CASE WHEN score IS NOT NULL THEN score END),1) as avg_score
            FROM lms_enrollments
            GROUP BY course_title ORDER BY completion_rate DESC
        """))

    return to_json({"error": f"Unknown dataset: {dataset_name}. Use list_datasets() to see options."})


@mcp.tool()
def create_report(title: str, dataset_name: str, chart_type: str, filters: str = "{}") -> str:
    """Simulate creating a Power BI report. Returns a report definition."""
    report = {
        "report_id": f"RPT_{title[:20].replace(' ', '_').upper()}",
        "title": title,
        "dataset": dataset_name,
        "chart_type": chart_type,
        "filters": json.loads(filters) if filters else {},
        "status": "generated",
        "embed_url": f"https://app.powerbi.com/reportEmbed?reportId=mock-{title[:10].lower().replace(' ','-')}",
        "message": "Report generated successfully (mock). In production, this would call the Power BI REST API.",
    }
    return to_json(report)


@mcp.tool()
def embed_visual(visual_type: str, dataset_name: str, x_axis: str, y_axis: str) -> str:
    """Get embed config for a Power BI visual."""
    return to_json({
        "visual_type": visual_type,
        "dataset": dataset_name,
        "config": {"x": x_axis, "y": y_axis},
        "embed_token": "mock-embed-token",
        "embed_url": "https://app.powerbi.com/visualEmbed?mock=true",
    })


if __name__ == "__main__":
    mcp.run()
