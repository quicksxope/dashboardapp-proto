# shared.py (SUPER FAST VERSION)
import hashlib
import requests
import streamlit as st
import base64
from io import BytesIO
from datetime import datetime

# GitHub Auth
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}

# ================================================================
# FAST CACHE: Store GitHub raw bytes only, no BytesIO.
# ================================================================
@st.cache_data(ttl=3600)
def fetch_github_raw(repo, file_path, branch="main"):
    """
    Fetch file content from GitHub. Returns raw bytes + hash.
    This function is cached → only called once per hour.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code != 200:
        return None, None

    data = res.json()
    raw_bytes = base64.b64decode(data["content"])
    md5_hash = hashlib.md5(raw_bytes).hexdigest()
    return raw_bytes, md5_hash


def fresh_bytesio(raw_bytes):
    """Create a fresh BytesIO object every time."""
    if raw_bytes is None:
        return None
    bio = BytesIO(raw_bytes)
    bio.seek(0)
    return bio


# ================================================================
# Update GitHub File
# ================================================================
def update_file(repo, file_path, content_bytes, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    meta = requests.get(url, headers=GITHUB_HEADERS).json()
    sha = meta.get("sha", None)

    payload = {
        "message": f"Update {file_path}",
        "content": base64.b64encode(content_bytes).decode(),
        "sha": sha,
        "branch": branch,
    }

    res = requests.put(url, headers=GITHUB_HEADERS, json=payload)
    return res.status_code in (200, 201)


# ================================================================
# Main get_file() function
# ================================================================
def get_file(repo_path: str, label: str, key: str, branch="main"):
    """
    Returns BytesIO for Excel files:
    - Always uses cached raw bytes
    - Only downloads from GitHub once per TTL
    - Ensures fresh BytesIO for pandas
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus format '<repo>/contents/<file_path>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # Fetch stored raw bytes from GitHub (cached)
    github_bytes, github_hash = fetch_github_raw(repo, file_path, branch)

    # Fresh BytesIO from cached bytes
    github_file = fresh_bytesio(github_bytes)

    # Allow upload override
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_upload")

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(file_bytes).hexdigest()

        # If identical to GitHub → no need to upload
        if uploaded_hash == github_hash:
            st.sidebar.success("✔ File sama dengan database. Menggunakan file default.")
            return fresh_bytesio(github_bytes)

        # Ask confirmation
        with st.sidebar.expander("Konfirmasi Update File"):
            confirm = st.radio("Update file ke database GitHub?", ["Tidak", "Ya"], key=f"{key}_confirm")

        if confirm == "Ya":
            ok = update_file(repo, file_path, file_bytes, branch)
            if ok:
                st.cache_data.clear()
                st.sidebar.success("✔ File berhasil diupdate.")
                return fresh_bytesio(file_bytes)
            else:
                st.sidebar.error("❌ Gagal upload ke GitHub. Menggunakan file lama.")

        return fresh_bytesio(github_bytes)

    # No upload → return GitHub version
    return github_file
