import streamlit as st
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="💻 EC2 Live SSH Terminal", layout="wide")

st.title("💻 EC2 Live SSH Terminal")
BASE_URL = "http://127.0.0.1:8002"

# ====== Control Buttons ======
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Create Instance"):
        st.info("Launching EC2 instance... Please wait ⏳")
        res = requests.post(f"{BASE_URL}/launch_ec2/")
        if res.status_code == 200:
            data = res.json()
            st.success(f"✅ Instance launched! Public IP: {data.get('public_ip', 'N/A')}")
            st.session_state["ip"] = data.get("public_ip", "")
        else:
            st.error("Failed to launch EC2 instance")

with col2:
    if st.button("🌐 View Public IP"):
        res = requests.get(f"{BASE_URL}/get_ip/")
        if res.status_code == 200:
            ip = res.json().get("public_ip")
            if ip:
                st.session_state["ip"] = ip
                st.success(f"Public IP: {ip}")
            else:
                st.warning("No instance found.")
        else:
            st.error("Failed to retrieve IP")

with col3:
    if st.button("🗑 Destroy Instance"):
        res = requests.post(f"{BASE_URL}/destroy_ec2/")
        if res.status_code == 200:
            st.warning("Instance destroyed successfully 🧹")
            st.session_state["ip"] = ""
        else:
            st.error("Failed to destroy instance")

st.divider()

# ====== Terminal Section ======
ip = st.session_state.get("ip", "")
ip = st.text_input("Enter EC2 Public IP", value=ip, placeholder="e.g., 13.223.228.52")


if ip.strip():
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm/css/xterm.css" />
      <script src="https://cdn.jsdelivr.net/npm/xterm/lib/xterm.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit/lib/xterm-addon-fit.js"></script>
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          height: 100%;
          background-color: black;
          overflow: hidden;
        }}
        #terminal {{
          width: 100%;
          height: 95vh;
          border: 3px solid #00ff00;
          border-radius: 10px;
          padding: 5px;
          box-sizing: border-box;
          background-color: black;
        }}
      </style>
    </head>
    <body>
      <div id="terminal" tabindex="0"></div>
      <script>
        const term = new window.Terminal({{
          cursorBlink: true,
          fontFamily: "monospace",
          fontSize: 15,
          convertEol: true,
          scrollback: 2000,
          theme: {{
            background: '#000000',
            foreground: '#FFFFFF',
            cursor: '#00FF00'
          }}
        }});
        const fitAddon = new window.FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal'));
        fitAddon.fit();
        window.addEventListener('resize', () => fitAddon.fit());
        const termDiv = document.getElementById('terminal');
        term.focus();
        termDiv.addEventListener('click', () => term.focus());
        term.write('Connecting to {ip}...\\r\\n');
        const socket = new WebSocket('ws://127.0.0.1:8002/ws/ssh?ip={ip}');
        socket.onopen = () => {{
          term.write('[Connected to EC2: {ip}]\\r\\n');
          term.focus();
        }};
        socket.onmessage = (event) => {{
          term.write(event.data);
        }};
        socket.onclose = () => {{
          term.write('\\r\\n[Connection closed]\\r\\n');
        }};
        socket.onerror = (err) => {{
          term.writeln('[ERROR] Connection failed');
        }};
        term.onData((data) => {{
          if (socket.readyState === WebSocket.OPEN) {{
            socket.send(data);
          }}
        }});
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=700)
else:
    st.info("Enter an EC2 public IP to start the live terminal.")
