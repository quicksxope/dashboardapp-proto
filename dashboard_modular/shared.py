# shared.py
import hashlib
import requests
from io import BytesIO
import streamlit as st
import base64

# --- Global GitHub Token Header ---
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}

def get_file_hash(file_bytes):
    """Return MD5 hash of given file content."""
    return hashlib.md5(file_bytes).hexdigest()

@st.cache_data(ttl=3600)
def get_github_file_and_hash(repo_path, branch="main"):
    """Download file from GitHub and return its content, hash, and SHA."""
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code == 200:
        try:
            json_data = res.json()
            content_b64 = json_data["content"]
            content = base64.b64decode(content_b64)
            return BytesIO(content), hashlib.md5(content).hexdigest(), json_data["sha"]
        except Exception as e:
            st.error(f"⚠️ Failed to parse GitHub content: {e}")
            return None, None, None
    else:
        st.error(f"⚠️ Failed to fetch file from GitHub: {res.status_code}")
        return None, None, None

def update_file_to_github(repo_path, file_bytes, commit_msg="Update via dashboard", branch="main", sha=None):
    """Upload or replace file on GitHub repo."""
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

def get_file(repo_path: str, label: str, key: str, branch="main"):
    """
    Handle file upload + GitHub fallback + auto-replace if changed.
    - `repo_path`: "username/repo/contents/path/to/file.xlsx"
    - `label`: file uploader label
    - `key`: session key for uploader
    """
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)
    github_file, github_hash, github_sha = get_github_file_and_hash(repo_path, branch=branch)

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = get_file_hash(file_bytes)

        if uploaded_hash == github_hash:
            st.sidebar.info(f"✅ Uploaded file same as GitHub. Using default.")
            return github_file
        else:
            st.sidebar.warning("🆕 Uploaded file is different. Updating GitHub…")
            success = update_file_to_github(
                repo_path,
                file_bytes,
                f"Update {key} from dashboard upload",
                branch=branch,
                sha=github_sha
            )
            if success:
                st.sidebar.success("📤 File updated to GitHub.")
                return BytesIO(file_bytes)
            else:
                st.sidebar.error("❌ Failed to update file. Using GitHub version instead.")
                return github_file
    else:
        return github_file
