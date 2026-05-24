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
    -- ── BRONZE (raw landing) ──────────────────────────────────────────
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

    -- ── SILVER (cleaned, identity-resolved) ──────────────────────────
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

    -- ── GOLD (aggregated KPIs) ────────────────────────────────────────
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

    -- ── AGENT MEMORY ─────────────────────────────────────────────────
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
        content TEXT,  -- JSON/HTML
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()


def load_silver(conn):
    def load_csv(path, table, dtype_map=None):
        if not path.exists():
            print(f"  SKIP {path.name} (not found — run generate_mock_data.py first)")
            return
        df = pd.read_csv(path)
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  Loaded {len(df)} rows -> {table}")

    load_csv(MOCK_DIR / "employees.csv", "employees")
    load_csv(MOCK_DIR / "lms_enrollments.csv", "lms_enrollments")
    load_csv(MOCK_DIR / "course_catalog.csv", "course_catalog")
    load_csv(MOCK_DIR / "skill_assessments.csv", "skill_assessments")
    load_csv(MOCK_DIR / "training_budget.csv", "training_budget")


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
    load_silver(conn)
    build_gold(conn)
    conn.close()
    print("\nDatabase setup complete.")


if __name__ == "__main__":
    main()
