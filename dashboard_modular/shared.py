# shared.py
import hashlib
import requests
from io import BytesIO
import streamlit as st
import base64

GITHUB_HEADERS = {"Authorization": f"token {st.secrets['github_token']}"}

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

@st.cache_data(ttl=3600)
def get_github_file_and_hash(repo_path, branch="main"):
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    r = requests.get(url, headers=GITHUB_HEADERS)
    if r.status_code == 200:
        content_b64 = r.json()["content"]
        content = base64.b64decode(content_b64)
        file = BytesIO(content)
        hash_val = hashlib.md5(content).hexdigest()
        sha = r.json()["sha"]
        return file, hash_val, sha
    return None, None, None

def update_file_to_github(repo_path, file_bytes, commit_msg="Update via dashboard", branch="main", sha=None):
    url = f"https://api.github.com/repos/{repo_path}"
    content_b64 = base64.b64encode(file_bytes).decode()
    payload = {
        "message": commit_msg,
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=GITHUB_HEADERS, json=payload)
    return res.status_code in (200, 201)

def get_file(repo_path: str, label: str, key: str):
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)
    github_file, github_hash, github_sha = get_github_file_and_hash(repo_path)

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = get_file_hash(file_bytes)

        if uploaded_hash == github_hash:
            st.sidebar.info(f"✅ Uploaded file same as GitHub. Using default.")
            return github_file
        else:
            st.sidebar.success("🆕 Uploaded file is different. Updating GitHub…")
            success = update_file_to_github(
                repo_path,
                file_bytes,
                f"Update {key} from dashboard upload",
                sha=github_sha
            )
            if success:
                st.sidebar.success("📤 File updated to GitHub.")
                return BytesIO(file_bytes)
            else:
                st.sidebar.error("❌ Failed to update file to GitHub.")
                return github_file
    else:
        return github_file
