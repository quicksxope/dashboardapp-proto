# shared.py (FINAL & STABLE VERSION)
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

# =======================================================
# Cache GitHub file → raw bytes ONLY
# =======================================================
@st.cache_data(ttl=3600)
def fetch_github_file(repo, file_path, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"

    res = requests.get(url, headers=GITHUB_HEADERS)
    if res.status_code != 200:
        return None, None, None

    info = res.json()
    raw_bytes = base64.b64decode(info["content"])
    md5_hash = hashlib.md5(raw_bytes).hexdigest()
    sha = info["sha"]

    return raw_bytes, md5_hash, sha


def new_bytesio(raw):
    """Always return a fresh BytesIO for pandas."""
    if raw is None:
        return None
    buf = BytesIO(raw)
    buf.seek(0)
    return buf


# =======================================================
# Upload file to GitHub
# =======================================================
def upload_to_github(repo, file_path, raw_bytes, sha, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    payload = {
        "message": f"Update {file_path}",
        "content": base64.b64encode(raw_bytes).decode(),
        "sha": sha,
        "branch": branch,
    }

    res = requests.put(url, headers=GITHUB_HEADERS, json=payload)
    return res.status_code in (200, 201)


# =======================================================
# MAIN get_file(): identical behavior for ALL files
# =======================================================
def get_file(repo_path, label, key, branch="main"):
    if "/contents/" not in repo_path:
        st.error("❌ Path harus format '<repo>/contents/<file>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # Fetch GitHub version (cached)
    raw_github, github_hash, github_sha = fetch_github_file(repo, file_path, branch)

    github_file = new_bytesio(raw_github)

    # User upload
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_upload")

    if uploaded:
        raw_uploaded = uploaded.getvalue()
        uploaded_hash = hashlib.md5(raw_uploaded).hexdigest()

        if uploaded_hash == github_hash:
            st.sidebar.success("✔ File sama dengan database. Menggunakan file default.")
            return new_bytesio(raw_github)

        with st.sidebar.expander("Konfirmasi Update File"):
            confirm = st.radio("Update file ke GitHub?", ["Tidak", "Ya"], key=f"{key}_confirm")

        if confirm == "Ya":
            ok = upload_to_github(repo, file_path, raw_uploaded, github_sha, branch)
            if ok:
                st.cache_data.clear()
                st.sidebar.success("✔ File berhasil diupdate.")
                return new_bytesio(raw_uploaded)
            else:
                st.sidebar.error("❌ Upload gagal. Menggunakan file lama.")
                return github_file

        return github_file

    # No upload → return default GitHub version
    return github_file
