"""One-command startup: generates data, sets up DB, launches Streamlit."""
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
SCRIPTS = BASE / "scripts"


def run(cmd, label):
    print(f"\n{'='*50}\n{label}\n{'='*50}")
    result = subprocess.run([sys.executable, str(cmd)], cwd=str(BASE))
    if result.returncode != 0:
        print(f"ERROR: {label} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"✓ {label} complete")


def main():
    print("Learning Report Agent — Startup")
    print("=" * 50)

    run(SCRIPTS / "generate_mock_data.py", "Step 1/2: Generating mock data")
    run(SCRIPTS / "setup_db.py", "Step 2/2: Setting up database")

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
