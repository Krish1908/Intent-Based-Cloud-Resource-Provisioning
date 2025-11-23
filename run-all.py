import os
import subprocess
import time

# =========================
# CONFIGURATION
# =========================
SERVICES = [
    # === MAIN DASHBOARD ===
    {
        "name": "Main Backend",
        "dir": r"\Dashboards",
        "cmd": "uvicorn backend_main:app --host 127.0.0.1 --port 8001 --reload",
    },
    {
        "name": "Main Dashboard",
        "dir": r"\Dashboards",
        "cmd": "streamlit run dashboard_main.py --server.port 8501",  # ✅ only this opens tab
    },

    # === EC2 MODULE ===
    {
        "name": "EC2 Backend",
        "dir": r"\EC2",
        "cmd": "uvicorn backend_ec2:app --host 127.0.0.1 --port 8002 --reload",
    },
    {
        "name": "EC2 Dashboard (Silent)",
        "dir": r"\EC2",
        # ✅ This version prevents Streamlit from opening a new tab
        "cmd": "streamlit run dashboard_ec2.py --server.port 8502 --server.headless true --logger.level error",
    },

    # === S3 MODULE ===
    {
        "name": "S3 Backend",
        "dir": r"\S3",
        "cmd": "uvicorn backend_s3:app --host 127.0.0.1 --port 8003 --reload",
    },
    {
        "name": "S3 Dashboard (Silent)",
        "dir": r"\S3",
        # ✅ Silent startup
        "cmd": "streamlit run dashboard_s3.py --server.port 8503 --server.headless true --logger.level error",
    },
]


# =========================
# FUNCTION: OPEN TERMINAL
# =========================
def open_terminal(title, directory, command):
    print(f"🟢 Launching {title}...")
    os.chdir(directory)

    if os.name == "nt":  # Windows
        subprocess.Popen(f'start cmd /k "title {title} && {command}"', shell=True)
    else:  # macOS / Linux
        subprocess.Popen(
            ['gnome-terminal', '--', 'bash', '-c', f'cd "{directory}" && {command}; exec bash']
        )

    time.sleep(1)


# =========================
# MAIN LOGIC
# =========================
if __name__ == "__main__":
    print("🚀 Launching OneYes Infrastructure Suite...\n")

    for svc in SERVICES:
        open_terminal(svc["name"], svc["dir"], svc["cmd"])

    print("\n✅ All services launched successfully!\n")
    print("📡 Ports overview:")
    print(" Main Backend:  8001 | Dashboard: 8501 (opens automatically)")
    print(" EC2 Backend:   8002 | Dashboard: 8502 (headless)")
    print(" S3 Backend:    8003 | Dashboard: 8503 (headless)")
    print("\n💡 EC2 & S3 dashboards will open only when you click 'Access Resource' in the main dashboard.\n")

