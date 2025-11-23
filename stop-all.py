import os
import subprocess
import time
import psutil  # pip install psutil

# ===============================
# CONFIGURATION
# ===============================
PORTS = [8001, 8002, 8003, 8501, 8502, 8503]
TERMINAL_KEYWORDS = [
    "Main Backend",
    "EC2 Backend",
    "S3 Backend",
    "EC2 Dashboard",
    "S3 Dashboard",
    "Main Dashboard"
]


# ===============================
# KILL PROCESSES BY PORT
# ===============================
def kill_process_on_port(port):
    """Kill process running on a given port (Windows & Unix)."""
    try:
        if os.name == "nt":
            cmd_find = f'netstat -ano | findstr :{port}'
            result = subprocess.check_output(cmd_find, shell=True).decode(errors="ignore")
            for line in result.splitlines():
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit():
                    print(f"🛑 Terminating PID {pid} on port {port}...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            cmd_find = f"lsof -ti:{port}"
            pids = subprocess.check_output(cmd_find, shell=True).decode().strip().split()
            for pid in pids:
                print(f"🛑 Killing PID {pid} on port {port}...")
                os.system(f"kill -9 {pid}")
    except subprocess.CalledProcessError:
        print(f"✅ No process found on port {port}.")
    except Exception as e:
        print(f"⚠️ Error killing port {port}: {e}")


# ===============================
# CLOSE BACKEND TERMINALS
# ===============================
def close_backend_cmds():
    """Force close any cmd.exe running uvicorn backends."""
    print("\n🧩 Closing Uvicorn backend terminals...")
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline", "ppid"]):
        try:
            cmdline = proc.info.get("cmdline", [])
            if not isinstance(cmdline, (list, tuple)):
                continue

            cmdline_str = " ".join(cmdline).lower()
            if "uvicorn" in cmdline_str:
                parent_pid = proc.info.get("ppid")
                if parent_pid:
                    try:
                        parent = psutil.Process(parent_pid)
                        if parent.name().lower() == "cmd.exe":
                            print(f"🪟 Closing CMD hosting backend (PID {parent.pid}) for Uvicorn process {proc.pid}...")
                            parent.terminate()
                            proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


# ===============================
# CLOSE ANY REMAINING TERMINALS
# ===============================
def close_remaining_cmds():
    """Close all leftover cmd.exe windows matching known titles."""
    print("\n🪟 Closing any remaining OneYes terminals...")
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            if proc.info["name"].lower() == "cmd.exe":
                cmdline = proc.info.get("cmdline", [])
                if not isinstance(cmdline, (list, tuple)):
                    continue

                cmdline_str = " ".join(cmdline).lower()
                if any(keyword.lower() in cmdline_str for keyword in TERMINAL_KEYWORDS):
                    print(f"🪟 Forcing close on: {cmdline_str[:100]}...")
                    proc.terminate()
                    time.sleep(0.2)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


# ===============================
# MAIN FUNCTION
# ===============================
def main():
    print("\n🧹 Stopping all OneYes services (backends & dashboards)...\n")
    
    # 1️⃣ Kill processes by port
    for port in PORTS:
        kill_process_on_port(port)
        time.sleep(0.3)

    # 2️⃣ Close backend CMDs (Uvicorn)
    close_backend_cmds()
    time.sleep(0.5)

    # 3️⃣ Close all remaining CMDs (Streamlit & others)
    close_remaining_cmds()
    time.sleep(0.5)

    print("\n✅ All processes and terminal windows closed successfully!\n")


if __name__ == "__main__":
    main()
