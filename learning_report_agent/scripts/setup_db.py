"""Initialize SQLite Bronze/Silver/Gold databases and load mock data."""
import sys
import sqlite3
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, MOCK_DIR, DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn):
    conn.executescript("""
    -- -- BRONZE (raw landing) ------------------------------------------
    CREATE TABLE IF NOT EXISTS bronze_employees (
        raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        ingested_at TEXT DEFAULT (datetime('now')),
        data TEXT  -- JSON blob of raw row
    );
    CREATE TABLE IF NOT EXISTS bronze_enrollments (
        raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        ingested_at TEXT DEFAULT (datetime('now')),
        data TEXT
    );

    -- -- SILVER (cleaned, identity-resolved) --------------------------
    CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        department TEXT,
        role TEXT,
        location TEXT,
        hire_date TEXT,
        manager_id TEXT,
        employment_status TEXT,
        grade_level TEXT,
        years_at_company REAL,
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS lms_enrollments (
        enrollment_id TEXT PRIMARY KEY,
        employee_id TEXT,
        course_id TEXT,
        course_title TEXT,
        course_category TEXT,
        enrolled_date TEXT,
        completion_date TEXT,
        status TEXT,
        score REAL,
        duration_hours REAL,
        is_required INTEGER,
        lms_source TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS course_catalog (
        course_id TEXT PRIMARY KEY,
        title TEXT,
        category TEXT,
        duration_h REAL,
        required INTEGER
    );

    CREATE TABLE IF NOT EXISTS skill_assessments (
        assessment_id TEXT PRIMARY KEY,
        employee_id TEXT,
        skill TEXT,
        proficiency_level TEXT,
        self_rated INTEGER,
        manager_rated INTEGER,
        assessed_date TEXT
    );

    CREATE TABLE IF NOT EXISTS training_budget (
        department TEXT PRIMARY KEY,
        year INTEGER,
        budget_usd REAL,
        spent_usd REAL,
        headcount INTEGER,
        avg_training_hours_target INTEGER
    );

    -- -- GOLD (aggregated KPIs) ----------------------------------------
    CREATE TABLE IF NOT EXISTS gold_compliance_summary (
        department TEXT,
        course_id TEXT,
        course_title TEXT,
        total_enrolled INTEGER,
        completed INTEGER,
        completion_rate REAL,
        avg_score REAL,
        as_of TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (department, course_id)
    );

    CREATE TABLE IF NOT EXISTS gold_dept_learning_kpis (
        department TEXT PRIMARY KEY,
        headcount INTEGER,
        total_enrollments INTEGER,
        total_completions INTEGER,
        completion_rate REAL,
        avg_score REAL,
        required_completion_rate REAL,
        total_training_hours REAL,
        avg_hours_per_employee REAL,
        budget_usd REAL,
        spent_usd REAL,
        budget_utilization REAL,
        as_of TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS gold_skill_gap (
        department TEXT,
        skill TEXT,
        avg_self_rating REAL,
        avg_manager_rating REAL,
        gap REAL,
        employee_count INTEGER,
        PRIMARY KEY (department, skill)
    );

    -- -- AGENT MEMORY -------------------------------------------------
    CREATE TABLE IF NOT EXISTS agent_memory_episodic (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        query TEXT,
        response_summary TEXT,
        intent TEXT,
        entities TEXT,  -- JSON
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS agent_memory_procedural (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_name TEXT UNIQUE,
        description TEXT,
        steps TEXT,  -- JSON
        used_count INTEGER DEFAULT 0,
        last_used TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS generated_flows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flow_name TEXT,
        description TEXT,
        trigger_type TEXT,
        flow_json TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS generated_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_name TEXT,
        report_type TEXT,
        query TEXT,
        content TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS delivery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipients TEXT,
        report_title TEXT,
        report_type TEXT,
        status TEXT,
        detail TEXT,
        pdf_path TEXT,
        sent_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS schedule_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT NOT NULL,
        department TEXT,
        recipients TEXT NOT NULL,
        frequency TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        last_run TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()


def _log_fix(label: str, count: int, total: int):
    if count:
        print(f"    [FIX] {label}: {count} of {total} rows ({count/total*100:.1f}%)")


# -- canonical lookup maps (mirrors dirty variants in generate_mock_data.py) --
_DEPT_CANONICAL = {
    "engg": "Engineering", "engineering": "Engineering", "eng dept": "Engineering",
    "human resources": "HR", "h.r.": "HR", "human res": "HR",
    "fin": "Finance", "finance": "Finance", "financial dept": "Finance",
    "ops": "Operations", "operations": "Operations", "oper.": "Operations",
    "mktg": "Marketing", "marketing": "Marketing", "mkt": "Marketing",
    "sales": "Sales", "sales dept": "Sales",
    "legal": "Legal", "legal dept": "Legal",
    "information technology": "IT", "i.t.": "IT", "it": "IT",
    "hr": "HR",
}
_STATUS_CANONICAL = {
    "completed": "Completed", "complete": "Completed", "done": "Completed",
    "in progress": "In Progress", "in-progress": "In Progress",
    "in_progress": "In Progress", "ongoing": "In Progress",
    "not started": "Not Started", "not_started": "Not Started",
    "pending": "Not Started",
}
_PROFICIENCY_CANONICAL = {
    "beginner": "Beginner", "beg": "Beginner",
    "intermediate": "Intermediate", "inter": "Intermediate",
    "advanced": "Advanced", "adv": "Advanced",
    "expert": "Expert", "exp": "Expert",
}
_EMP_STATUS_CANONICAL = {
    "active": "Active", "on leave": "On Leave",
    "terminated": "Terminated",
}


def _normalise(series: pd.Series, canon: dict) -> pd.Series:
    return series.apply(lambda v: canon.get(str(v).strip().lower(), v) if pd.notna(v) else v)


def clean_and_load_silver(conn):
    """
    Bronze -> Silver pipeline:
      1. Load raw CSVs
      2. Log every data quality issue found
      3. Fix: nulls, variant spellings, duplicates, casing
      4. Write clean data to silver tables
    """
    print("\n-- Data Quality: Bronze -> Silver ---------------------------------")

    # -- EMPLOYEES ------------------------------------------------------------
    path = MOCK_DIR / "employees.csv"
    if not path.exists():
        print("  SKIP employees.csv (not found)")
    else:
        df = pd.read_csv(path)
        total = len(df)
        print(f"\n  employees.csv  raw: {total} rows")

        # Store raw in bronze
        conn.execute("DELETE FROM bronze_employees")
        import json
        for _, row in df.iterrows():
            conn.execute("INSERT INTO bronze_employees (source, data) VALUES (?,?)",
                         ("employees_csv", row.to_json()))

        # Fix: duplicate rows
        before = len(df)
        df = df.drop_duplicates(subset=["employee_id"])
        _log_fix("Duplicate employee_id rows removed", before - len(df), total)

        # Fix: inconsistent department spellings
        orig = df["department"].copy()
        df["department"] = _normalise(df["department"], _DEPT_CANONICAL)
        _log_fix("Inconsistent department names normalised", (orig != df["department"]).sum(), len(df))

        # Fix: employment_status casing
        orig = df["employment_status"].copy()
        df["employment_status"] = _normalise(df["employment_status"], _EMP_STATUS_CANONICAL)
        _log_fix("employment_status casing fixed", (orig != df["employment_status"]).sum(), len(df))

        # Fix: null emails
        null_email = df["email"].isna().sum()
        _log_fix("Null emails filled with placeholder", null_email, len(df))
        df["email"] = df["email"].fillna(
            df["employee_id"].apply(lambda eid: f"{eid.lower()}@unknown.internal")
        )

        # Fix: null locations
        null_loc = df["location"].isna().sum()
        _log_fix("Null locations filled with 'Unknown'", null_loc, len(df))
        df["location"] = df["location"].fillna("Unknown")

        # Fix: whitespace in text fields
        for col in ["name", "role", "department", "location"]:
            df[col] = df[col].astype(str).str.strip()

        df.to_sql("employees", conn, if_exists="replace", index=False)
        print(f"  OK employees loaded to silver: {len(df)} rows (removed {total - len(df)} dirty rows)")

    # -- LMS ENROLLMENTS ------------------------------------------------------
    path = MOCK_DIR / "lms_enrollments.csv"
    if not path.exists():
        print("  SKIP lms_enrollments.csv (not found)")
    else:
        df = pd.read_csv(path)
        total = len(df)
        print(f"\n  lms_enrollments.csv  raw: {total} rows")

        conn.execute("DELETE FROM bronze_enrollments")
        for _, row in df.iterrows():
            conn.execute("INSERT INTO bronze_enrollments (source, data) VALUES (?,?)",
                         ("lms_csv", row.to_json()))

        # Fix: duplicate enrollment_id rows
        before = len(df)
        df = df.drop_duplicates(subset=["enrollment_id"])
        _log_fix("Duplicate enrollment_id rows removed", before - len(df), total)

        # Fix: inconsistent status values
        orig = df["status"].copy()
        df["status"] = _normalise(df["status"], _STATUS_CANONICAL)
        _log_fix("Inconsistent status values normalised", (orig != df["status"]).sum(), len(df))

        # Fix: course_category casing
        orig = df["course_category"].copy()
        df["course_category"] = df["course_category"].astype(str).str.strip().str.title()
        _log_fix("course_category casing normalised", (orig != df["course_category"]).sum(), len(df))

        # Fix: null scores on completed rows
        completed_null_score = (df["status"] == "Completed") & df["score"].isna()
        _log_fix("Null scores on Completed rows filled with median", completed_null_score.sum(), len(df))
        median_score = df.loc[df["score"].notna(), "score"].median()
        df.loc[completed_null_score, "score"] = round(median_score, 0)

        df.to_sql("lms_enrollments", conn, if_exists="replace", index=False)
        print(f"  OK lms_enrollments loaded to silver: {len(df)} rows (removed {total - len(df)} dirty rows)")

    # -- SKILL ASSESSMENTS ----------------------------------------------------
    path = MOCK_DIR / "skill_assessments.csv"
    if not path.exists():
        print("  SKIP skill_assessments.csv (not found)")
    else:
        df = pd.read_csv(path)
        total = len(df)
        print(f"\n  skill_assessments.csv  raw: {total} rows")

        # Fix: duplicates
        before = len(df)
        df = df.drop_duplicates(subset=["assessment_id"])
        _log_fix("Duplicate assessment_id rows removed", before - len(df), total)

        # Fix: proficiency_level variants
        orig = df["proficiency_level"].copy()
        df["proficiency_level"] = _normalise(df["proficiency_level"], _PROFICIENCY_CANONICAL)
        _log_fix("proficiency_level variants normalised", (orig != df["proficiency_level"]).sum(), len(df))

        # Fix: null manager_rated - leave as NULL (valid - not all have manager ratings)
        null_mgr = df["manager_rated"].isna().sum()
        if null_mgr:
            print(f"    [INFO] {null_mgr} rows have no manager rating (expected - retained as NULL)")

        df.to_sql("skill_assessments", conn, if_exists="replace", index=False)
        print(f"  OK skill_assessments loaded to silver: {len(df)} rows (removed {total - len(df)} dirty rows)")

    # -- TRAINING BUDGET ------------------------------------------------------
    path = MOCK_DIR / "training_budget.csv"
    if not path.exists():
        print("  SKIP training_budget.csv (not found)")
    else:
        df = pd.read_csv(path)
        total = len(df)
        print(f"\n  training_budget.csv  raw: {total} rows")

        null_spend = df["spent_usd"].isna().sum()
        _log_fix("Null spent_usd filled with 0 (no spend recorded)", null_spend, total)
        df["spent_usd"] = df["spent_usd"].fillna(0)

        df.to_sql("training_budget", conn, if_exists="replace", index=False)
        print(f"  OK training_budget loaded to silver: {len(df)} rows")

    # -- COURSE CATALOG -------------------------------------------------------
    path = MOCK_DIR / "course_catalog.csv"
    if not path.exists():
        print("  SKIP course_catalog.csv (not found)")
    else:
        df = pd.read_csv(path)
        df.to_sql("course_catalog", conn, if_exists="replace", index=False)
        print(f"\n  OK course_catalog loaded to silver: {len(df)} rows")

    conn.commit()
    print("\n-- Silver layer ready ----------------------------------------------")


def build_gold(conn):
    print("  Building Gold layer KPIs...")

    conn.execute("DELETE FROM gold_compliance_summary")
    conn.execute("""
        INSERT INTO gold_compliance_summary
            (department, course_id, course_title, total_enrolled, completed, completion_rate, avg_score)
        SELECT
            e.department,
            l.course_id,
            l.course_title,
            COUNT(*) AS total_enrolled,
            SUM(CASE WHEN l.status='Completed' THEN 1 ELSE 0 END) AS completed,
            ROUND(SUM(CASE WHEN l.status='Completed' THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) AS completion_rate,
            ROUND(AVG(CASE WHEN l.score IS NOT NULL THEN l.score END), 1) AS avg_score
        FROM lms_enrollments l
        JOIN employees e ON l.employee_id = e.employee_id
        WHERE l.is_required = 1
        GROUP BY e.department, l.course_id
    """)

    conn.execute("DELETE FROM gold_dept_learning_kpis")
    conn.execute("""
        INSERT INTO gold_dept_learning_kpis
            (department, headcount, total_enrollments, total_completions, completion_rate,
             avg_score, required_completion_rate, total_training_hours, avg_hours_per_employee,
             budget_usd, spent_usd, budget_utilization)
        SELECT
            e.department,
            COUNT(DISTINCT e.employee_id) AS headcount,
            COUNT(l.enrollment_id) AS total_enrollments,
            SUM(CASE WHEN l.status='Completed' THEN 1 ELSE 0 END) AS total_completions,
            ROUND(SUM(CASE WHEN l.status='Completed' THEN 1.0 ELSE 0 END)/NULLIF(COUNT(*),0)*100, 1) AS completion_rate,
            ROUND(AVG(CASE WHEN l.score IS NOT NULL THEN l.score END), 1) AS avg_score,
            ROUND(SUM(CASE WHEN l.is_required=1 AND l.status='Completed' THEN 1.0 ELSE 0 END) /
                  NULLIF(SUM(CASE WHEN l.is_required=1 THEN 1 ELSE 0 END),0)*100, 1) AS required_completion_rate,
            ROUND(SUM(CASE WHEN l.status='Completed' THEN l.duration_hours ELSE 0 END), 1) AS total_training_hours,
            ROUND(SUM(CASE WHEN l.status='Completed' THEN l.duration_hours ELSE 0 END)/
                  NULLIF(COUNT(DISTINCT e.employee_id),0), 1) AS avg_hours_per_employee,
            tb.budget_usd,
            tb.spent_usd,
            ROUND(tb.spent_usd / NULLIF(tb.budget_usd,0)*100, 1) AS budget_utilization
        FROM employees e
        LEFT JOIN lms_enrollments l ON e.employee_id = l.employee_id
        LEFT JOIN training_budget tb ON e.department = tb.department
        WHERE e.employment_status != 'Terminated'
        GROUP BY e.department
    """)

    conn.execute("DELETE FROM gold_skill_gap")
    conn.execute("""
        INSERT INTO gold_skill_gap (department, skill, avg_self_rating, avg_manager_rating, gap, employee_count)
        SELECT
            e.department,
            s.skill,
            ROUND(AVG(s.self_rated), 2) AS avg_self_rating,
            ROUND(AVG(s.manager_rated), 2) AS avg_manager_rating,
            ROUND(AVG(s.self_rated) - AVG(s.manager_rated), 2) AS gap,
            COUNT(*) AS employee_count
        FROM skill_assessments s
        JOIN employees e ON s.employee_id = e.employee_id
        WHERE e.employment_status != 'Terminated'
        GROUP BY e.department, s.skill
    """)

    conn.commit()
    print("  Gold KPIs built.")


def main():
    print(f"Setting up database at {DB_PATH}...")
    conn = get_conn()
    create_schema(conn)
    print("Schema created.")
    clean_and_load_silver(conn)
    build_gold(conn)
    conn.close()
    print("\nDatabase setup complete.")


if __name__ == "__main__":
    main()
