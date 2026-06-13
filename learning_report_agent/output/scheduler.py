"""Background scheduler — checks schedule_config every minute and auto-delivers reports."""
import threading
import sqlite3
import time
from datetime import datetime, timedelta

from config import DB_PATH


def _should_fire(frequency: str, last_run: str | None) -> bool:
    now = datetime.now()
    if not last_run:
        return True  # never run — fire immediately

    try:
        last = datetime.fromisoformat(last_run)
    except ValueError:
        return True

    if "Daily" in frequency:
        return last.date() < now.date()

    elif "Weekly" in frequency:
        if now.weekday() != 0:  # only fires on Monday
            return False
        this_monday = (now - timedelta(days=now.weekday())).date()
        return last.date() < this_monday

    elif "Monthly" in frequency:
        if now.day != 1:  # only fires on 1st of month
            return False
        return (last.year, last.month) < (now.year, now.month)

    return False


def _run_schedule(row: dict):
    """Generate report + PDF + send email for one schedule row."""
    from output.report_generator import (
        generate_compliance_report,
        generate_learning_kpi_report,
        generate_skill_gap_report,
    )
    from output.pdf_generator import generate_pdf
    from output.email_sender import send_report_email

    rtype      = row["report_type"]
    dept       = row.get("department")
    recipients = [e.strip() for e in row["recipients"].split(",") if e.strip()]

    if rtype == "compliance":
        report = generate_compliance_report(dept)
    elif rtype == "learning_kpis":
        report = generate_learning_kpi_report(dept)
    else:
        report = generate_skill_gap_report(dept)

    pdf    = generate_pdf(report)
    result = send_report_email(recipients, report, pdf)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE schedule_config SET last_run=? WHERE id=?",
        (datetime.now().isoformat(), row["id"]),
    )
    conn.commit()
    conn.close()

    print(f"[SCHEDULER] Schedule {row['id']} ({rtype}) fired -> {result['status']}: {result['detail'][:80]}")


def _tick():
    """One scheduler tick — check all enabled schedules."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM schedule_config WHERE enabled=1").fetchall()
        conn.close()
    except Exception:
        return  # DB not ready yet

    for raw in rows:
        row = dict(raw)
        if _should_fire(row["frequency"], row.get("last_run")):
            try:
                _run_schedule(row)
            except Exception as exc:
                print(f"[SCHEDULER ERROR] Schedule {row['id']}: {exc}")


def start_scheduler() -> threading.Thread:
    """
    Launch the background scheduler daemon thread.
    Call once at app startup — safe to call multiple times (no-op after first).
    """
    for t in threading.enumerate():
        if t.name == "report-scheduler":
            return t  # already running

    def _loop():
        print("[SCHEDULER] Started — checking schedules every 60 s")
        while True:
            _tick()
            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True, name="report-scheduler")
    t.start()
    return t
