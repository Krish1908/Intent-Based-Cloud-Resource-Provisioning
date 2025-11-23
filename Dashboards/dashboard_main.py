# crt fe 4 - export, otp and other functions are fine. small tabular column. line of code, 345.

import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

BASE_URL = "http://127.0.0.1:8001"

st.set_page_config(page_title="☁️ Cloud Resource Provisioning", layout="centered")

# --- Dynamic layout width depending on active page ---
# --- Adaptive width styling: compact home, wider dashboards ---
def apply_dynamic_width():
    """Applies CSS width dynamically based on active page."""
    page = st.session_state.get("page", "main")

    # Compact layout (login/register/etc)
    compact_pages = ["main", "register", "verify", "forgot", "reset"]

    if page in compact_pages:
        st.markdown("""
            <style>
            /* Compact centered layout (login/register/etc.) */
            .block-container {
                max-width: 70%;
                padding-left: 2rem;
                padding-right: 2rem;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # Wider layout for dashboards
        st.markdown("""
            <style>
            /* Slightly wider for dashboards */
            .block-container {
                max-width: 92%;
                padding-left: 3rem;
                padding-right: 3rem;
            }
            .stSelectbox, .stTextInput, .stButton, .stRadio {
                width: 100% !important;
            }
            </style>
        """, unsafe_allow_html=True)

# Apply layout style each rerun
apply_dynamic_width()

# # --- Slightly increase app width for better dropdown visibility ---
# st.markdown("""
#     <style>
#     /* widen the main content area just a bit */
#     .block-container {
#         max-width: 95%;
#         padding-left: 3rem;
#         padding-right: 3rem;
#     }
#     /* ensure selectboxes and tables align nicely */
#     .stSelectbox, .stTextInput, .stButton, .stRadio {
#         width: 100% !important;
#     }
#     </style>
# """, unsafe_allow_html=True)


# ---------------- Session State ----------------
if "page" not in st.session_state:
    st.session_state.page = "main"
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if "notif" not in st.session_state:
    st.session_state.notif = None
if "reg_email" not in st.session_state:
    st.session_state.reg_email = None

# ---------------- Validation ----------------
def validate_password(password: str) -> bool:
    return len(password) >= 8 and re.search(r"[A-Za-z]", password) and re.search(r"[0-9]", password)

def validate_email(email: str) -> bool:
    if not isinstance(email, str): return False
    if "@" not in email: return False
    local, _, domain = email.partition("@")
    return bool(local and "." in domain)

def validate_username(username: str) -> bool:
    return username and len(username) >= 3 and re.match(r"^[A-Za-z0-9_]+$", username)

# ---------------- Global Header ----------------
def show_header():
    st.title("☁️ Cloud Resource Provisioning Dashboard")
    if st.session_state.notif:
        st.success(st.session_state.notif)
        st.session_state.notif = None

# ---------------- Pages ----------------
def main_page():
    show_header()
    identifier_input = st.text_input("Username or Email")
    password_input = st.text_input("Password", type="password")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Login"):
            if not identifier_input or not password_input:
                st.error("Please enter username/email and password")
            else:
                res = requests.post(f"{BASE_URL}/login", json={
                    "identifier": identifier_input,
                    "password": password_input
                })

                if res.status_code == 200:
                    data = res.json()
                    st.session_state.username = data["username"]
                    st.session_state.role = data["role"]
                    st.session_state.page = "admin" if data["role"] == "admin" else "user"
                    st.rerun()

                else:
                    try:
                        st.error(res.json().get("detail", "Login failed"))
                    except Exception:
                        st.error("Login failed")

    with col2:
        if st.button("Register"):
            st.session_state.page = "register"
            st.rerun()

    with col3:
        if st.button("Forgot Password"):
            st.session_state.page = "forgot"
            st.rerun()

def register_page():
    show_header()
    st.subheader("Register New Account")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])

    if st.button("Signup"):
        if not validate_username(username):
            st.error("Invalid username (min 3 chars, letters/numbers/underscore only)")
            return
        if not validate_email(email):
            st.error("Invalid email")
            return
        if not validate_password(password):
            st.error("Password must be at least 8 characters with letters and numbers")
            return

        res = requests.post(f"{BASE_URL}/signup", json={
            "username": username,
            "email": email,
            "password": password,
            "role": role
        })

        if res.status_code == 200:
            data = res.json()
            st.session_state.page = "verify"
            st.session_state.reg_email = data["email"]
            st.session_state.notif = "OTP sent to registered email ID."
            st.rerun()
        else:
            st.error(res.json().get("detail", "Signup failed"))

def verify_page():
    show_header()
    st.subheader("Verify Email with OTP")
    email = st.session_state.reg_email or st.text_input("Email")
    otp = st.text_input("OTP")
    if st.button("Verify"):
        res = requests.post(f"{BASE_URL}/verify-otp", json={"email": email, "otp": otp})
        if res.status_code == 200:
            st.session_state.page = "main"
            st.session_state.notif = "Verification successful. Please login."
            st.rerun()
        else:
            st.error(res.json().get("detail", "Verification failed"))

def forgot_password_page():
    show_header()
    st.subheader("Forgot Password")
    email = st.text_input("Registered Email")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send OTP"):
            if not validate_email(email):
                st.error("Invalid email")
                return
            # Check email exists via new backend endpoint
            try:
                res_check = requests.post(f"{BASE_URL}/check-email", json={"email": email})
                if res_check.status_code == 200 and res_check.json().get("exists", False):
                    res = requests.post(f"{BASE_URL}/forgot-password", json={"email": email})
                    if res.status_code == 200:
                        st.session_state.page = "reset"
                        st.session_state.reg_email = email
                        st.session_state.notif = "OTP sent to registered email ID."
                        st.rerun()
                    else:
                        st.error(res.json().get("detail", "Failed to send OTP"))
                else:
                    st.error("Email not registered")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    with col2:
        if st.button("Cancel"):
            st.session_state.page = "main"
            st.rerun()

def reset_password_page():
    show_header()
    st.subheader("Reset Password")
    email = st.session_state.reg_email or st.text_input("Email")
    otp = st.text_input("OTP")
    new_password = st.text_input("New Password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset Password"):
            if not validate_password(new_password):
                st.error("Password must be at least 8 characters with letters and numbers")
                return
            res = requests.post(f"{BASE_URL}/reset-password", json={
                "email": email,
                "otp": otp,
                "new_password": new_password
            })
            if res.status_code == 200:
                st.session_state.page = "main"
                st.session_state.notif = "Password reset successful. Please login."
                st.rerun()
            else:
                st.error(res.json().get("detail", "Password reset failed"))
    with col2:
        if st.button("Cancel"):
            st.session_state.page = "main"
            st.rerun()


def user_dashboard():
    show_header()
    st.subheader(f"Welcome, {st.session_state.username} (User)")

    # 🔄 Auto-refresh every 5 seconds
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="user_refresh")

    text = st.text_area("Enter your provisioning request")
    if st.button("Submit Request"):
        if text.strip():
            res = requests.post(f"{BASE_URL}/parse", json={
                "username": st.session_state.username,
                "text": text.strip()
            })
            if res.status_code == 200:
                st.success("Request submitted successfully")
                st.rerun()
            else:
                st.error("Failed to submit request")

    st.subheader("Your Requests")
    res = requests.get(f"{BASE_URL}/user/requests", params={"username": st.session_state.username})
    if res.status_code == 200:
        data = res.json()
        if data:
            # Sort oldest first
            data = sorted(data, key=lambda x: x["created_at"])
            # --- Updated table with "Access Resource" column ---
            header_cols = st.columns([1, 4, 2, 2, 2])
            header_cols[0].markdown("**SNO**")
            header_cols[1].markdown("**Request**")
            header_cols[2].markdown("**Status**")
            header_cols[3].markdown("**Timestamp**")
            header_cols[4].markdown("**Access**")

            for idx, r in enumerate(data, start=1):
                cols = st.columns([1, 4, 2, 2, 2])
                cols[0].write(idx)
                cols[1].write(r["text"])
                cols[2].write(r["status"])

                ts = datetime.fromisoformat(r["created_at"]).strftime("%d-%m-%Y_%H-%M-%S")
                ts = ts[:-1]
                cols[3].write(ts)

                # ✅ Show "Access Resource" button only when approved
                if r["status"].lower() == "approve":
                    with cols[4]:
                        if "ec2" in r["text"].lower():
                            st.link_button("Access EC2", "http://localhost:8502", use_container_width=True)
                        elif "s3" in r["text"].lower():
                            st.link_button("Access S3", "http://localhost:8503", use_container_width=True)
                        else:
                            st.write("-")
                else:
                    cols[4].write("⏳ Pending Approval")

            # Download
            format_choice = st.radio("Download as:", ["CSV","Excel"], horizontal=True)
            if st.button("Download"):
                if format_choice=="CSV":
                    df = pd.DataFrame(data)
                    df["SNO"] = range(1,len(df)+1)
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d-%m-%Y_%H-%M-%S").str[:-1]
                    csv_bytes = df[["SNO","text","status","created_at"]].to_csv(index=False).encode()
                    st.download_button(label="Download CSV", data=csv_bytes, file_name=f"user_requests_{st.session_state.username}.csv")
                else:
                    df = pd.DataFrame(data)
                    df["SNO"] = range(1,len(df)+1)
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d-%m-%Y_%H-%M-%S").str[:-1]
                    excel_file = pd.ExcelWriter("temp.xlsx", engine="xlsxwriter")
                    df[["SNO","text","status","created_at"]].to_excel(excel_file, index=False)
                    excel_file.close()
                    with open("temp.xlsx","rb") as f:
                        st.download_button(label="Download Excel", data=f, file_name=f"user_requests_{st.session_state.username}.xlsx")

        else:
            st.info("No requests yet.")
    else:
        st.error("Failed to fetch requests")

    if st.button("Logout"):
        st.session_state.page = "main"
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()


def admin_dashboard():
    show_header()
    st.subheader(f"Welcome, {st.session_state.username} (Admin)")

    # 🔄 Auto-refresh every 5 seconds
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="admin_refresh")

    status_filter = st.selectbox("Filter by status:", ["All","Pending","Approve","Reject"])
    res = requests.get(f"{BASE_URL}/admin/requests")
    if res.status_code == 200:
        data = res.json()
        if status_filter!="All":
            data = [d for d in data if d["status"].lower()==status_filter.lower()]
        if data:
            # Sort oldest first
            data = sorted(data, key=lambda x: x["created_at"])
            header_cols = st.columns([1,2,4,2,3,2])
            header_cols[0].markdown("**SNO**")
            header_cols[1].markdown("**Username**")
            header_cols[2].markdown("**Request**")
            header_cols[3].markdown("**Status**")
            header_cols[4].markdown("**Timestamp**")
            header_cols[5].markdown("**Action**")
            for idx, r in enumerate(data, start=1):
                cols = st.columns([1,2,4,2,3,2])
                cols[0].write(idx)
                cols[1].write(r["username"])
                cols[2].write(r["text"])
                cols[3].write(r["status"])
                ts = datetime.fromisoformat(r["created_at"]).strftime("%d-%m-%Y_%H-%M-%S")
                ts = ts[:-1]  # show only first 2 digits of seconds
                cols[4].write(ts)
                with cols[5]:
                    new_status = st.selectbox(
                        "Change Status",
                        ["approve","reject","pending"],
                        index=["approve","reject","pending"].index(r["status"]) if r["status"] in ["approve","reject","pending"] else 2,
                        key=f"status_{r['id']}"
                    )
                    if new_status!=r["status"]:
                        requests.post(f"{BASE_URL}/admin/update/{r['id']}", params={"status":new_status})
                        st.rerun()
            # Download
            format_choice = st.radio("Download as:", ["CSV","Excel"], horizontal=True)
            if st.button("Download"):
                if format_choice=="CSV":
                    df = pd.DataFrame(data)
                    df["SNO"] = range(1,len(df)+1)
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d-%m-%Y_%H-%M-%S").str[:-1]
                    csv_bytes = df[["SNO","username","text","status","created_at"]].to_csv(index=False).encode()
                    st.download_button(label="Download CSV", data=csv_bytes, file_name=f"admin_requests_{st.session_state.username}.csv")
                else:
                    df = pd.DataFrame(data)
                    df["SNO"] = range(1,len(df)+1)
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d-%m-%Y_%H-%M-%S").str[:-1]
                    excel_file = pd.ExcelWriter("temp.xlsx", engine="xlsxwriter")
                    df[["SNO","username","text","status","created_at"]].to_excel(excel_file, index=False)
                    excel_file.close()
                    with open("temp.xlsx","rb") as f:
                        st.download_button(label="Download Excel", data=f, file_name=f"admin_requests_{st.session_state.username}.xlsx")
        else:
            st.info("No requests found.")
    else:
        st.error("Failed to fetch requests")

    if st.button("Logout"):
        st.session_state.page = "main"
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()


# ---------------- Router ----------------
if st.session_state.page=="main":
    main_page()
elif st.session_state.page=="register":
    register_page()
elif st.session_state.page=="verify":
    verify_page()
elif st.session_state.page=="forgot":
    forgot_password_page()
elif st.session_state.page=="reset":
    reset_password_page()
elif st.session_state.page=="user":
    user_dashboard()
elif st.session_state.page=="admin":
    admin_dashboard()
