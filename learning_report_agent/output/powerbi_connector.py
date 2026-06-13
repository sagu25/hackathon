"""Power BI connector — authenticates via MSAL and pushes Gold layer data to a Push Dataset."""
import sqlite3
import requests
from datetime import datetime

from config import DB_PATH, settings

_API = "https://api.powerbi.com/v1.0/myorg"
_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]
_DATASET_NAME = "Learning Analytics — Agent"

# ── Push Dataset schema (mirrors Gold layer) ──────────────────────────────────
_DATASET_DEF = {
    "name": _DATASET_NAME,
    "defaultMode": "Push",
    "tables": [
        {
            "name": "DeptLearningKPIs",
            "columns": [
                {"name": "department",               "dataType": "string"},
                {"name": "headcount",                "dataType": "Int64"},
                {"name": "total_enrollments",        "dataType": "Int64"},
                {"name": "total_completions",        "dataType": "Int64"},
                {"name": "completion_rate",          "dataType": "Double"},
                {"name": "avg_score",                "dataType": "Double"},
                {"name": "required_completion_rate", "dataType": "Double"},
                {"name": "total_training_hours",     "dataType": "Double"},
                {"name": "avg_hours_per_employee",   "dataType": "Double"},
                {"name": "budget_usd",               "dataType": "Double"},
                {"name": "spent_usd",                "dataType": "Double"},
                {"name": "budget_utilization",       "dataType": "Double"},
            ],
        },
        {
            "name": "ComplianceSummary",
            "columns": [
                {"name": "department",      "dataType": "string"},
                {"name": "course_id",       "dataType": "string"},
                {"name": "course_title",    "dataType": "string"},
                {"name": "total_enrolled",  "dataType": "Int64"},
                {"name": "completed",       "dataType": "Int64"},
                {"name": "completion_rate", "dataType": "Double"},
                {"name": "avg_score",       "dataType": "Double"},
            ],
        },
        {
            "name": "SkillGap",
            "columns": [
                {"name": "department",         "dataType": "string"},
                {"name": "skill",              "dataType": "string"},
                {"name": "avg_self_rating",    "dataType": "Double"},
                {"name": "avg_manager_rating", "dataType": "Double"},
                {"name": "gap",                "dataType": "Double"},
                {"name": "employee_count",     "dataType": "Int64"},
            ],
        },
        {
            "name": "EnrollmentTrends",
            "columns": [
                {"name": "month",        "dataType": "string"},
                {"name": "enrollments",  "dataType": "Int64"},
                {"name": "completions",  "dataType": "Int64"},
            ],
        },
    ],
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    """Acquire an access token using client credentials (service principal)."""
    import msal
    app = msal.ConfidentialClientApplication(
        client_id=settings.powerbi_client_id,
        client_credential=settings.powerbi_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.powerbi_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=_SCOPE)
    if "access_token" not in result:
        raise RuntimeError(
            f"MSAL token error: {result.get('error_description', result.get('error', 'unknown'))}"
        )
    return result["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Dataset management ────────────────────────────────────────────────────────

def _workspace_url(path: str = "") -> str:
    return f"{_API}/groups/{settings.powerbi_workspace_id}{path}"


def _find_dataset(token: str) -> str | None:
    """Return dataset id if the push dataset already exists in the workspace."""
    r = requests.get(_workspace_url("/datasets"), headers=_headers(token), timeout=30)
    r.raise_for_status()
    for ds in r.json().get("value", []):
        if ds.get("name") == _DATASET_NAME:
            return ds["id"]
    return None


def _create_dataset(token: str) -> str:
    """Create the push dataset and return its id."""
    r = requests.post(
        _workspace_url("/datasets?defaultRetentionPolicy=basicFIFO"),
        headers=_headers(token),
        json=_DATASET_DEF,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["id"]


def _clear_table(token: str, dataset_id: str, table: str):
    r = requests.delete(
        _workspace_url(f"/datasets/{dataset_id}/tables/{table}/rows"),
        headers=_headers(token),
        timeout=30,
    )
    r.raise_for_status()


def _push_rows(token: str, dataset_id: str, table: str, rows: list[dict]):
    """Push rows in batches of 9,999 (Power BI REST API limit)."""
    BATCH = 9_999
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        r = requests.post(
            _workspace_url(f"/datasets/{dataset_id}/tables/{table}/rows"),
            headers=_headers(token),
            json={"rows": batch},
            timeout=60,
        )
        r.raise_for_status()


# ── Data extraction from Gold layer ──────────────────────────────────────────

def _gold_rows(sql: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql).fetchall()]
    conn.close()
    # Replace None with 0 for numeric fields (Power BI rejects nulls in push datasets)
    cleaned = []
    for row in rows:
        cleaned.append({
            k: (0 if v is None and not isinstance(v, str) else ("" if v is None else v))
            for k, v in row.items()
        })
    return cleaned


# ── Main entry point ─────────────────────────────────────────────────────────

def push_to_powerbi() -> dict:
    """
    Full push: authenticate -> get/create dataset -> clear tables -> push all gold data.
    Returns a status dict with counts and a workspace URL.
    """
    if not settings.is_powerbi_configured:
        return {
            "status": "not_configured",
            "message": (
                "Power BI credentials not set. Add POWERBI_TENANT_ID, POWERBI_CLIENT_ID, "
                "POWERBI_CLIENT_SECRET, POWERBI_WORKSPACE_ID to your .env file."
            ),
        }

    log: list[str] = []
    try:
        log.append("Acquiring access token...")
        token = _get_token()
        log.append("Token acquired.")

        dataset_id = _find_dataset(token)
        if dataset_id:
            log.append(f"Found existing dataset: {dataset_id}")
        else:
            log.append("Dataset not found — creating...")
            dataset_id = _create_dataset(token)
            log.append(f"Dataset created: {dataset_id}")

        pushes: dict[str, int] = {}

        # DeptLearningKPIs
        rows = _gold_rows("SELECT department, headcount, total_enrollments, total_completions, "
                          "completion_rate, avg_score, required_completion_rate, total_training_hours, "
                          "avg_hours_per_employee, budget_usd, spent_usd, budget_utilization "
                          "FROM gold_dept_learning_kpis")
        _clear_table(token, dataset_id, "DeptLearningKPIs")
        _push_rows(token, dataset_id, "DeptLearningKPIs", rows)
        pushes["DeptLearningKPIs"] = len(rows)
        log.append(f"Pushed {len(rows)} rows -> DeptLearningKPIs")

        # ComplianceSummary
        rows = _gold_rows("SELECT department, course_id, course_title, total_enrolled, "
                          "completed, completion_rate, avg_score FROM gold_compliance_summary")
        _clear_table(token, dataset_id, "ComplianceSummary")
        _push_rows(token, dataset_id, "ComplianceSummary", rows)
        pushes["ComplianceSummary"] = len(rows)
        log.append(f"Pushed {len(rows)} rows -> ComplianceSummary")

        # SkillGap
        rows = _gold_rows("SELECT department, skill, avg_self_rating, avg_manager_rating, "
                          "gap, employee_count FROM gold_skill_gap")
        _clear_table(token, dataset_id, "SkillGap")
        _push_rows(token, dataset_id, "SkillGap", rows)
        pushes["SkillGap"] = len(rows)
        log.append(f"Pushed {len(rows)} rows -> SkillGap")

        # EnrollmentTrends
        rows = _gold_rows("""
            SELECT strftime('%Y-%m', enrolled_date) as month,
                   COUNT(*) as enrollments,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completions
            FROM lms_enrollments GROUP BY month ORDER BY month
        """)
        _clear_table(token, dataset_id, "EnrollmentTrends")
        _push_rows(token, dataset_id, "EnrollmentTrends", rows)
        pushes["EnrollmentTrends"] = len(rows)
        log.append(f"Pushed {len(rows)} rows -> EnrollmentTrends")

        workspace_url = (
            f"https://app.powerbi.com/groups/{settings.powerbi_workspace_id}/datasets/{dataset_id}"
        )
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "tables_pushed": pushes,
            "total_rows": sum(pushes.values()),
            "workspace_url": workspace_url,
            "pushed_at": datetime.now().isoformat(),
            "log": log,
        }

    except Exception as exc:
        log.append(f"ERROR: {exc}")
        return {"status": "error", "message": str(exc), "log": log}


def get_workspace_url() -> str:
    return f"https://app.powerbi.com/groups/{settings.powerbi_workspace_id}"
