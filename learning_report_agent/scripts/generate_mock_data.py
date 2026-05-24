"""Generate realistic mock data for LMS, HR, and training systems."""
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


def main():
    print("Generating mock data...")

    employees = generate_employees(500)
    employees.to_csv(MOCK_DIR / "employees.csv", index=False)
    print(f"  employees.csv — {len(employees)} rows")

    enrollments = generate_lms_enrollments(employees)
    enrollments.to_csv(MOCK_DIR / "lms_enrollments.csv", index=False)
    print(f"  lms_enrollments.csv — {len(enrollments)} rows")

    skills = generate_skill_assessments(employees)
    skills.to_csv(MOCK_DIR / "skill_assessments.csv", index=False)
    print(f"  skill_assessments.csv — {len(skills)} rows")

    budget = generate_training_budget(employees)
    budget.to_csv(MOCK_DIR / "training_budget.csv", index=False)
    print(f"  training_budget.csv — {len(budget)} rows")

    courses_df = pd.DataFrame(COURSES)
    courses_df.to_csv(MOCK_DIR / "course_catalog.csv", index=False)
    print(f"  course_catalog.csv — {len(courses_df)} rows")

    print(f"\nAll mock data saved to {MOCK_DIR}")


if __name__ == "__main__":
    main()
