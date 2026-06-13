"""Generate realistic mock data for LMS, HR, and training systems.

Data is intentionally dirtied before saving to simulate real-world source
system inconsistencies (nulls, variant spellings, duplicates, mixed casing).
The setup_db.py cleaning step fixes all of these and logs every fix.
"""
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MOCK_DIR

fake = Faker()
random.seed(42)
Faker.seed(42)

# ── dirty-data variant maps ───────────────────────────────────────────────────
_DEPT_VARIANTS = {
    "Engineering": ["Engg", "ENGINEERING", "Eng Dept"],
    "HR":          ["Human Resources", "H.R.", "Human Res"],
    "Finance":     ["Fin", "FINANCE", "Financial Dept"],
    "Operations":  ["Ops", "OPERATIONS", "Oper."],
    "Marketing":   ["Mktg", "MARKETING", "Mkt"],
    "Sales":       ["SALES", "Sales Dept"],
    "Legal":       ["LEGAL", "Legal Dept"],
    "IT":          ["Information Technology", "I.T."],
}
_STATUS_VARIANTS = {
    "Completed":   ["completed", "COMPLETED", "Complete", "Done"],
    "In Progress": ["in progress", "IN_PROGRESS", "In-Progress", "Ongoing"],
    "Not Started": ["not started", "NOT_STARTED", "Pending", "pending"],
}
_PROFICIENCY_VARIANTS = {
    "Beginner":     ["beginner", "BEGINNER", "Beg"],
    "Intermediate": ["intermediate", "INTERMEDIATE", "Inter"],
    "Advanced":     ["advanced", "ADVANCED", "Adv"],
    "Expert":       ["expert", "EXPERT", "Exp"],
}

DEPARTMENTS = ["Engineering", "Sales", "HR", "Finance", "Operations", "Marketing", "Legal", "IT"]
ROLES = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Tech Lead", "DevOps Engineer"],
    "Sales": ["Account Executive", "Sales Manager", "SDR", "VP Sales"],
    "HR": ["HR Business Partner", "Recruiter", "L&D Specialist", "HR Director"],
    "Finance": ["Financial Analyst", "Controller", "CFO", "Accountant"],
    "Operations": ["Operations Manager", "Project Manager", "Analyst", "Coordinator"],
    "Marketing": ["Marketing Manager", "Content Strategist", "Digital Marketer", "CMO"],
    "Legal": ["Legal Counsel", "Paralegal", "Compliance Officer", "General Counsel"],
    "IT": ["IT Admin", "Security Analyst", "Network Engineer", "CTO"],
}
LOCATIONS = ["New York", "London", "Mumbai", "Singapore", "Sydney", "Toronto", "Dublin", "Dubai"]
COURSES = [
    {"id": "C001", "title": "Data Privacy & GDPR Fundamentals", "category": "Compliance", "duration_h": 2, "required": True},
    {"id": "C002", "title": "Workplace Safety & Health", "category": "Compliance", "duration_h": 1.5, "required": True},
    {"id": "C003", "title": "Code of Conduct & Ethics", "category": "Compliance", "duration_h": 1, "required": True},
    {"id": "C004", "title": "Cybersecurity Awareness", "category": "Compliance", "duration_h": 2, "required": True},
    {"id": "C005", "title": "Anti-Harassment & Inclusion", "category": "Compliance", "duration_h": 1.5, "required": True},
    {"id": "C006", "title": "Python for Data Science", "category": "Technical", "duration_h": 8, "required": False},
    {"id": "C007", "title": "Azure Cloud Fundamentals", "category": "Technical", "duration_h": 6, "required": False},
    {"id": "C008", "title": "Leadership & Influence", "category": "Leadership", "duration_h": 4, "required": False},
    {"id": "C009", "title": "Project Management (PMP Prep)", "category": "Professional", "duration_h": 10, "required": False},
    {"id": "C010", "title": "Advanced Excel & Power BI", "category": "Technical", "duration_h": 5, "required": False},
    {"id": "C011", "title": "Communication Skills", "category": "Soft Skills", "duration_h": 3, "required": False},
    {"id": "C012", "title": "Sales Techniques & CRM", "category": "Sales", "duration_h": 4, "required": False},
    {"id": "C013", "title": "Financial Modelling", "category": "Finance", "duration_h": 6, "required": False},
    {"id": "C014", "title": "Agile & Scrum Practitioner", "category": "Technical", "duration_h": 4, "required": False},
    {"id": "C015", "title": "AI & Machine Learning Basics", "category": "Technical", "duration_h": 5, "required": False},
]
SKILLS = [
    "Python", "SQL", "Power BI", "Azure", "Excel", "Leadership",
    "Communication", "Project Management", "Data Analysis", "Machine Learning",
    "Sales", "Negotiation", "Finance", "Compliance", "Agile",
]


def _rand_date(start_days_ago=365, end_days_ago=0):
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))


def generate_employees(n=500):
    rows = []
    for i in range(1, n + 1):
        dept = random.choice(DEPARTMENTS)
        hire_date = _rand_date(start_days_ago=2000, end_days_ago=30)
        rows.append({
            "employee_id": f"EMP{i:04d}",
            "name": fake.name(),
            "email": fake.company_email(),
            "department": dept,
            "role": random.choice(ROLES[dept]),
            "location": random.choice(LOCATIONS),
            "hire_date": hire_date.strftime("%Y-%m-%d"),
            "manager_id": f"EMP{random.randint(1, max(1, i-1)):04d}" if i > 1 else None,
            "employment_status": random.choices(["Active", "Active", "Active", "On Leave", "Terminated"], k=1)[0],
            "grade_level": random.choice(["L1", "L2", "L3", "L4", "L5"]),
            "years_at_company": round((datetime.now() - hire_date).days / 365, 1),
        })
    return pd.DataFrame(rows)


def generate_lms_enrollments(employees_df):
    rows = []
    for _, emp in employees_df.iterrows():
        if emp["employment_status"] == "Terminated":
            continue
        for course in COURSES:
            # Required courses have higher enrollment rate
            enroll_prob = 0.95 if course["required"] else random.uniform(0.2, 0.7)
            if random.random() > enroll_prob:
                continue
            enrolled_date = _rand_date(start_days_ago=365)
            completed = random.random() < (0.85 if course["required"] else 0.6)
            completion_date = None
            score = None
            if completed:
                completion_date = enrolled_date + timedelta(days=random.randint(1, 60))
                score = random.randint(60, 100)
            rows.append({
                "enrollment_id": f"ENR{len(rows)+1:06d}",
                "employee_id": emp["employee_id"],
                "course_id": course["id"],
                "course_title": course["title"],
                "course_category": course["category"],
                "enrolled_date": enrolled_date.strftime("%Y-%m-%d"),
                "completion_date": completion_date.strftime("%Y-%m-%d") if completion_date else None,
                "status": "Completed" if completed else random.choice(["In Progress", "Not Started"]),
                "score": score,
                "duration_hours": course["duration_h"],
                "is_required": course["required"],
                "lms_source": random.choice(["Cornerstone", "SAP SF Learning"]),
            })
    return pd.DataFrame(rows)


def generate_skill_assessments(employees_df):
    rows = []
    for _, emp in employees_df.iterrows():
        if emp["employment_status"] == "Terminated":
            continue
        n_skills = random.randint(3, 8)
        for skill in random.sample(SKILLS, n_skills):
            rows.append({
                "assessment_id": f"ASS{len(rows)+1:06d}",
                "employee_id": emp["employee_id"],
                "skill": skill,
                "proficiency_level": random.choice(["Beginner", "Intermediate", "Advanced", "Expert"]),
                "self_rated": random.randint(1, 5),
                "manager_rated": random.randint(1, 5) if random.random() > 0.3 else None,
                "assessed_date": _rand_date(start_days_ago=180).strftime("%Y-%m-%d"),
            })
    return pd.DataFrame(rows)


def generate_training_budget(employees_df):
    rows = []
    for dept in DEPARTMENTS:
        dept_emps = employees_df[employees_df["department"] == dept]
        rows.append({
            "department": dept,
            "year": 2025,
            "budget_usd": random.randint(50_000, 200_000),
            "spent_usd": random.randint(20_000, 90_000),
            "headcount": len(dept_emps),
            "avg_training_hours_target": random.randint(20, 40),
        })
    return pd.DataFrame(rows)


def _inject_dirty(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Introduce realistic data quality issues to simulate real source systems."""
    df = df.copy()
    rng = random.Random(99)  # separate seed so main data stays reproducible

    if kind == "employees":
        # Inconsistent department spellings (~12% of rows)
        mask = df.index.map(lambda i: rng.random() < 0.12)
        df.loc[mask, "department"] = df.loc[mask, "department"].apply(
            lambda d: rng.choice(_DEPT_VARIANTS.get(d, [d]))
        )
        # Null emails (~6%)
        null_email = df.index.map(lambda i: rng.random() < 0.06)
        df.loc[null_email, "email"] = None
        # Null location (~5%)
        null_loc = df.index.map(lambda i: rng.random() < 0.05)
        df.loc[null_loc, "location"] = None
        # Mixed-case employment_status (~8%)
        mixed_status = df.index.map(lambda i: rng.random() < 0.08)
        df.loc[mixed_status, "employment_status"] = df.loc[mixed_status, "employment_status"].str.lower()
        # Duplicate ~2% of rows
        n_dupe = max(1, int(len(df) * 0.02))
        dupes = df.sample(n=n_dupe, random_state=7)
        df = pd.concat([df, dupes], ignore_index=True)

    elif kind == "enrollments":
        # Inconsistent status values (~10%)
        mask = df.index.map(lambda i: rng.random() < 0.10)
        df.loc[mask, "status"] = df.loc[mask, "status"].apply(
            lambda s: rng.choice(_STATUS_VARIANTS.get(s, [s]))
        )
        # Inconsistent course_category casing (~8%)
        cat_mask = df.index.map(lambda i: rng.random() < 0.08)
        df.loc[cat_mask, "course_category"] = df.loc[cat_mask, "course_category"].str.lower()
        # Null scores for some completed rows (~4%)
        completed = df["status"].str.lower().str.contains("complet", na=False)
        null_score = df.index.map(lambda i: rng.random() < 0.04)
        df.loc[completed & null_score, "score"] = None
        # Duplicate ~1.5% of rows
        n_dupe = max(1, int(len(df) * 0.015))
        dupes = df.sample(n=n_dupe, random_state=13)
        df = pd.concat([df, dupes], ignore_index=True)

    elif kind == "skills":
        # Inconsistent proficiency_level casing (~10%)
        mask = df.index.map(lambda i: rng.random() < 0.10)
        df.loc[mask, "proficiency_level"] = df.loc[mask, "proficiency_level"].apply(
            lambda p: rng.choice(_PROFICIENCY_VARIANTS.get(p, [p]))
        )
        # Duplicate ~1% of rows
        n_dupe = max(1, int(len(df) * 0.01))
        dupes = df.sample(n=n_dupe, random_state=17)
        df = pd.concat([df, dupes], ignore_index=True)

    elif kind == "budget":
        # Null spent_usd for 2 random departments
        null_idx = df.sample(n=min(2, len(df)), random_state=5).index
        df.loc[null_idx, "spent_usd"] = None

    return df


def main():
    print("Generating mock data (with real-world dirty data injected)...")

    employees = generate_employees(500)
    employees = _inject_dirty(employees, "employees")
    employees.to_csv(MOCK_DIR / "employees.csv", index=False)
    print(f"  employees.csv       — {len(employees)} rows (incl. duplicates/nulls/variant spellings)")

    enrollments = generate_lms_enrollments(employees[employees["employment_status"].str.lower() != "terminated"])
    enrollments = _inject_dirty(enrollments, "enrollments")
    enrollments.to_csv(MOCK_DIR / "lms_enrollments.csv", index=False)
    print(f"  lms_enrollments.csv — {len(enrollments)} rows (incl. duplicates/status variants)")

    skills = generate_skill_assessments(employees)
    skills = _inject_dirty(skills, "skills")
    skills.to_csv(MOCK_DIR / "skill_assessments.csv", index=False)
    print(f"  skill_assessments.csv — {len(skills)} rows (incl. proficiency variants)")

    budget = generate_training_budget(employees)
    budget = _inject_dirty(budget, "budget")
    budget.to_csv(MOCK_DIR / "training_budget.csv", index=False)
    print(f"  training_budget.csv — {len(budget)} rows (incl. null spend values)")

    courses_df = pd.DataFrame(COURSES)
    courses_df.to_csv(MOCK_DIR / "course_catalog.csv", index=False)
    print(f"  course_catalog.csv  — {len(courses_df)} rows")

    print(f"\nRaw (dirty) data saved to {MOCK_DIR}")
    print("Run setup_db.py to clean, standardise, and load into the analytics database.")


if __name__ == "__main__":
    main()
