import asyncio
import asyncssh
import subprocess
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:8502", "http://127.0.0.1:8502",
    "https://localhost:8502", "https://127.0.0.1:8502",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== CONFIG ==========
TERRAFORM_DIR = r"\EC2"
PEM_KEY_PATH = r"path-to-pem-file"
SSH_USER = "ubuntu"


# ========== EC2 MANAGEMENT ==========

@app.post("/launch_ec2/")
async def launch_ec2():
    """Launch EC2 instance using Terraform."""
    try:
        subprocess.run(["terraform", "init"], cwd=TERRAFORM_DIR, check=True)
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=TERRAFORM_DIR, check=True)

        time.sleep(10)
        ip_out = subprocess.check_output(["terraform", "output", "-raw", "public_ip"], cwd=TERRAFORM_DIR)
        instance_ip = ip_out.decode().strip()
        return {"status": "Launched", "public_ip": instance_ip}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}

@app.get("/get_ip/")
async def get_ip():
    """Fetch current Terraform public IP."""
    try:
        ip_out = subprocess.check_output(["terraform", "output", "-raw", "public_ip"], cwd=TERRAFORM_DIR)
        instance_ip = ip_out.decode().strip()
        return {"public_ip": instance_ip}
    except Exception:
        return {"public_ip": None}

@app.post("/destroy_ec2/")
async def destroy_ec2():
    """Destroy only EC2 instance, preserving other resources."""
    try:
        result = subprocess.run(
            [
                "terraform", "destroy",
                "-target=aws_instance.krish-crp",   # ✅ EC2-specific target
                "-auto-approve",
            ],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            check=True,
        )

        return {
            "status": "EC2 instance destroyed successfully",
            "details": result.stdout,
        }

    except subprocess.CalledProcessError as e:
        return {
            "error": e.stderr or str(e),
            "message": "Terraform EC2 destroy failed"
        }

# ========== SSH TERMINAL ==========

@app.websocket("/ws/ssh")
async def websocket_ssh(websocket: WebSocket, ip: str):
    """Fully interactive SSH terminal."""
    await websocket.accept()
    print(f"[INFO] WebSocket connected for EC2: {ip}")

    try:
        async with asyncssh.connect(
            ip,
            username=SSH_USER,
            client_keys=[PEM_KEY_PATH],
            known_hosts=None,
        ) as conn:
            proc = await conn.create_process(
                "bash --login",
                term_type="xterm-256color",
                term_size=(120, 40),
            )
            await websocket.send_text(f"Connected to {ip}\r\n")

            async def reader():
                try:
                    while True:
                        data = await proc.stdout.read(4096)
                        if not data:
                            await asyncio.sleep(0.05)
                            continue
                        await websocket.send_text(data)
                except Exception as e:
                    print(f"[Reader stopped] {e}")

            reader_task = asyncio.create_task(reader())

            while True:
                try:
                    data = await websocket.receive_text()
                    if data.lower().strip() in ["exit", "logout"]:
                        proc.stdin.write("exit\n")
                        await websocket.send_text("\r\n[INFO] Session closed by user.\r\n")
                        break
                    proc.stdin.write(data)
                except WebSocketDisconnect:
                    print("[INFO] WebSocket disconnected.")
                    break
                except Exception as e:
                    print("[ERROR write]", e)
                    break

            reader_task.cancel()

    except Exception as e:
        print("[ERROR]", e)
        try:
            await websocket.send_text(f"[ERROR] {str(e)}\r\n")
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        print("[INFO] WebSocket closed cleanly.")
