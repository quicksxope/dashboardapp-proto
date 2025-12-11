# shared.py
import hashlib
import requests
import streamlit as st
import base64
from io import BytesIO
from datetime import datetime

GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}


# ===================================================================
# ALWAYS return content bytes, NEVER return BytesIO from cache
# ===================================================================
@st.cache_data(ttl=3600)
def fetch_github_bytes(repo_path, branch="main"):
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code != 200:
        return None, None

    data = res.json()
    content = base64.b64decode(data["content"])
    file_hash = hashlib.md5(content).hexdigest()
    return content, file_hash


def to_fresh_bytesio(content_bytes):
    """ ALWAYS build a fresh BytesIO so pandas never reads EOF. """
    if content_bytes is None:
        return None

    bio = BytesIO(content_bytes)
    bio.seek(0)
    return bio


def get_file(repo_path: str, label: str, key: str, branch="main"):
    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus format '<repo>/contents/<file>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # ============ 1. Fetch GitHub file bytes (CACHED but raw bytes only) ============
    github_bytes, github_hash = fetch_github_bytes(f"{repo}/contents/{file_path}", branch=branch)

    # Convert to BytesIO fresh every time
    github_file = to_fresh_bytesio(github_bytes)

    # ============ 2. User upload ============
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_uploader")

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(file_bytes).hexdigest()

        if uploaded_hash == github_hash:
            st.sidebar.info("✔ File sama dengan database. Menggunakan default.")
            return to_fresh_bytesio(github_bytes)

        # Ask confirmation
        with st.sidebar.expander("Konfirmasi Update File"):
            confirm = st.radio("Update file ke GitHub?", ["Tidak", "Ya"], key=f"{key}_confirm")

        if confirm == "Ya":
            # Upload to GitHub
            res = update_file(repo, file_path, file_bytes, branch)
            if res:
                st.cache_data.clear()
                return to_fresh_bytesio(file_bytes)
            else:
                return github_file

        return github_file

    # ============ 3. No upload → return GitHub version ============
    return github_file



# ===================================================================
# GitHub Update Helper
# ===================================================================
def update_file(repo, file_path, content_bytes, branch="main"):
    get_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    meta = requests.get(get_url, headers=GITHUB_HEADERS).json()
    sha = meta.get("sha")

    payload = {
        "message": f"Update {file_path}",
        "content": base64.b64encode(content_bytes).decode(),
        "sha": sha,
        "branch": branch
    }

    put_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    res = requests.put(put_url, headers=GITHUB_HEADERS, json=payload)
    return res.status_code in (200, 201)
