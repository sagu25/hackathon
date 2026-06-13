"""One-command startup: generates data (first run only), sets up DB, launches Streamlit.

Usage:
    python start.py           # normal start — skips data gen if DB already exists
    python start.py --reset   # force-regenerate data and rebuild DB from scratch
"""
import sys
import subprocess
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BASE    = Path(__file__).parent
SCRIPTS = BASE / "scripts"
DB_PATH = BASE / "data" / "learning_agent.db"


def run(cmd, label):
    print(f"\n{'='*50}\n{label}\n{'='*50}")
    result = subprocess.run([sys.executable, str(cmd)], cwd=str(BASE))
    if result.returncode != 0:
        print(f"ERROR: {label} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"OK {label} complete")


def main():
    reset = "--reset" in sys.argv

    print("Learning Report Agent — Startup")
    print("=" * 50)

    if reset or not DB_PATH.exists():
        if reset:
            print("--reset flag detected: rebuilding data and database from scratch.")
        else:
            print("First run detected: generating data and setting up database.")

        run(SCRIPTS / "generate_mock_data.py", "Step 1/2: Generating mock data")
        run(SCRIPTS / "setup_db.py",           "Step 2/2: Setting up database")
    else:
        print(f"Database already exists ({DB_PATH.name}) — skipping data generation.")
        print("Run with --reset to force a full rebuild:  python start.py --reset")

    # Start background scheduler before Streamlit
    print("\n" + "=" * 50)
    print("Starting background report scheduler...")
    sys.path.insert(0, str(BASE))
    from output.scheduler import start_scheduler
    start_scheduler()
    print("Scheduler running — auto-delivers reports per schedule_config table.")

    print("\n" + "=" * 50)
    print("Launching Streamlit UI...")
    print("Open: http://localhost:8501")
    print("=" * 50)

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(BASE / "ui" / "app.py"),
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
    ], cwd=str(BASE))


if __name__ == "__main__":
    main()
