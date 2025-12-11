# shared.py (SIMPLE, CLEAN, FINAL)

import streamlit as st
import base64
import hashlib
import requests
from io import BytesIO

GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}

@st.cache_data(ttl=3600)
def fetch_from_github(repo, file_path, branch="main"):
    """
    Fetch raw bytes from GitHub and cache it for 1 hour.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)
    data = res.json()

    raw = base64.b64decode(data["content"])
    hashval = hashlib.md5(raw).hexdigest()
    sha = data["sha"]

    return raw, hashval, sha


def fresh_bytesio(raw):
    """Always return fresh BytesIO for pandas."""
    buf = BytesIO(raw)
    buf.seek(0)
    return buf


def update_github(repo, file_path, raw, sha, branch="main"):
    """
    Upload new Excel file to GitHub.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    payload = {
        "message": "Update via dashboard",
        "content": base64.b64encode(raw).decode(),
        "sha": sha,
        "branch": branch
    }

    res = requests.put(url, headers=GITHUB_HEADERS, json=payload)
    return res.status_code in (200, 201)


def get_file(repo_path, label, key, branch="main"):

    repo, file_path = repo_path.split("/contents/")

    # load from GitHub (cached raw bytes)
    raw_github, github_hash, github_sha = fetch_from_github(repo, file_path, branch)

    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)

    if uploaded:
        raw_uploaded = uploaded.getvalue()
        uploaded_hash = hashlib.md5(raw_uploaded).hexdigest()

        # file sama → gunakan GitHub version
        if uploaded_hash == github_hash:
            st.sidebar.info("✔ Sama dengan database. Menggunakan file GitHub.")
            return fresh_bytesio(raw_github)

        # file berbeda → konfirmasi update
        with st.sidebar.expander("Konfirmasi update file"):
            confirm = st.radio("Update ke GitHub?", ["Tidak", "Ya"], key=f"{key}_c")

        if confirm == "Ya":
            if update_github(repo, file_path, raw_uploaded, github_sha, branch):
                st.cache_data.clear()
                st.sidebar.success("✔ File berhasil diupdate.")
                return fresh_bytesio(raw_uploaded)
            else:
                st.sidebar.error("❌ Upload gagal.")
                return fresh_bytesio(raw_github)

        return fresh_bytesio(raw_github)

    # default: return GitHub version
    return fresh_bytesio(raw_github)
