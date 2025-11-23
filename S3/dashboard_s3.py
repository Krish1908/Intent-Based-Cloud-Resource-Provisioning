
import streamlit as st
import requests
from io import BytesIO
from urllib.parse import quote 

# FastAPI backend URL
BASE_URL = "http://127.0.0.1:8003/bucket"

st.set_page_config(page_title="🪣 S3 Bucket Management Panel")

st.title("🪣 S3 Bucket Management Panel")

# =========================================================
# CREATE BUCKET
# =========================================================
st.header("Create a New Bucket")
bucket_name = st.text_input("Enter new bucket name")

if st.button("Create Bucket"):
    if bucket_name:
        try:
            response = requests.post(
                f"{BASE_URL}/create",
                data={"bucket_name": bucket_name}
            )
            if response.status_code == 200:
                st.success(f"✅ Bucket created successfully.")
            else:
                st.error(f"❌ Backend rejected request ({response.status_code}).\n\n{response.text}")
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
    else:
        st.warning("Please enter a bucket name.")

st.divider()

# =========================================================
# UPLOAD FILE
# =========================================================
st.header("Upload a File to S3 Bucket")
upload_bucket = st.text_input("Enter target bucket name")
upload_file = st.file_uploader("Choose a file")

if st.button("Upload File"):
    if upload_bucket and upload_file:
        try:
            files = {"file": (upload_file.name, upload_file.getvalue())}
            data = {"bucket_name": upload_bucket}

            response = requests.post(
                f"{BASE_URL}/upload",
                data=data,
                files=files
            )
            if response.status_code == 200:
                st.success(f"✅ File uploaded successfully.")
            else:
                st.error(f"❌ Upload failed ({response.status_code}).\n\n{response.text}")
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
    else:
        st.warning("Please provide both a bucket name and a file.")

st.divider()

# =========================================================
# LIST FILES
# =========================================================
st.header("List Files in a Bucket")
list_bucket = st.text_input("Enter bucket name to list files")

if st.button("List Files"):
    if list_bucket:
        try:
            response = requests.get(f"{BASE_URL}/{list_bucket}/list")

            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                if files:
                    st.success(f"✅ Found {len(files)} files in '{list_bucket}'")
                    for f in files:
                        st.write(f"- {f['Key']}")
                else:
                    st.info("📭 No files found in this bucket.")
            else:
                st.error(f"❌ Failed to list files ({response.status_code}).\n\n{response.text}")
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
    else:
        st.warning("Please enter a bucket name.")

st.divider()

# =========================================================
# FILE OPERATIONS (Download / View URL / Delete)
# =========================================================
st.header("File Operations")
op_bucket = st.text_input("Enter bucket name")
op_file = st.text_input("Enter file name")

col1, col2, col3 = st.columns(3)

# --- Download File ---
with col1:
    if st.button("📥 Fetch File for Download"):
        if op_bucket and op_file:
            try:
                # Get public S3 URL from backend
                response = requests.get(f"{BASE_URL}/{op_bucket}/url", params={"key": op_file})

                if response.status_code == 200:
                    url = response.json().get("url")
                    file_response = requests.get(url)

                    if file_response.status_code == 200:
                        st.download_button(
                            label="⬇️ Click to Download File",
                            data=BytesIO(file_response.content),
                            file_name=op_file,
                            mime=file_response.headers.get("Content-Type", "application/octet-stream")
                        )
                        st.success(f"✅ Ready to download: {op_file}")
                    else:
                        st.error("❌ File not accessible from S3 public URL.")
                else:
                    st.error(f"⚠️ Failed to get URL: {response.text}")

            except Exception as e:
                st.error(f"⚠️ Error: {e}")

        else:
            st.warning("Please enter both bucket name and file name.")


# --- View Public URL ---
with col2:
    if st.button("🌐 View Public URL"):
        if op_bucket and op_file:
            try:
                response = requests.get(
                    f"{BASE_URL}/{op_bucket}/url",
                    params={"key": op_file}
                )
                if response.status_code == 200:
                    url = response.json().get("url")
                    encoded_url = quote(url, safe=':/')
                    st.success(f"🌍 Public URL:")
                    st.write(f"[Open File]({encoded_url})")
                else:
                    st.error(f"❌ Failed to get URL ({response.status_code}).\n\n{response.text}")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")
        else:
            st.warning("Please provide both bucket name and file name.")

# --- Delete File ---
with col3:
    if st.button("🗑️ Delete File"):
        if op_bucket and op_file:
            try:
                response = requests.delete(
                    f"{BASE_URL}/{op_bucket}/delete",
                    params={"keys": op_file}
                )
                if response.status_code == 200:
                    st.success(f"✅ File deleted successfully.")
                else:
                    st.error(f"❌ Deletion failed ({response.status_code}).\n\n{response.text}")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")
        else:
            st.warning("Please provide both bucket name and file name.")

st.divider()

# =========================================================
# DELETE BUCKET
# =========================================================
st.header("Delete a Bucket")
delete_bucket = st.text_input("Enter bucket name to delete")

if st.button("Delete Bucket"):
    if delete_bucket:
        try:
            response = requests.delete(f"{BASE_URL}/{delete_bucket}")
            if response.status_code == 200:
                st.success(f"✅ Bucket deleted successfully.")
            else:
                st.error(f"❌ Backend rejected request ({response.status_code}).\n\n{response.text}")
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
    else:
        st.warning("Please enter a bucket name.")

st.divider()
