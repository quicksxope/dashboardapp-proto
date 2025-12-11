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


# ==========================================================
# Fetch Excel bytes from GitHub — ALWAYS returns raw bytes
# ==========================================================
@st.cache_data(ttl=300)
def fetch_github_bytes(repo, file_path, branch="main"):
    """
    Mengambil file dari GitHub dan SELALU return raw bytes.
    Anti-error, auto gunakan download_url jika file besar.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code != 200:
        st.error(f"❌ Gagal fetch file dari GitHub: {file_path}")
        return None

    meta = res.json()

    # Jika file besar → GitHub kasih download_url
    if "download_url" in meta and meta["download_url"]:
        raw = requests.get(meta["download_url"]).content
    else:
        raw = base64.b64decode(meta["content"])

    return raw


# ==========================================================
# Convert raw bytes → BytesIO dengan .seek(0) SELALU
# ==========================================================
def make_bytesio(raw):
    if raw is None:
        return None
    bio = BytesIO(raw)
    bio.seek(0)
    return bio


# ==========================================================
# Main function: get_file
# Simple, clean, 100% stable
# ==========================================================
def get_file(repo_path: str, label: str, key: str, branch="main"):
    """
    Mekanisme final:
    1. Ambil file GitHub → BytesIO
    2. Jika user upload:
        - Gunakan file upload
        - (Opsional) update GitHub jika ingin
    3. Return BytesIO fresh setiap kali
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus format '<repo>/contents/<file_path>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # ---- STEP 1: ALWAYS fetch GitHub bytes ----
    raw_github = fetch_github_bytes(repo, file_path, branch)
    github_file = make_bytesio(raw_github)

    # ---- STEP 2: User Upload ----
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)

    if uploaded:
        raw_upload = uploaded.getvalue()
        upload_bio = make_bytesio(raw_upload)

        # Check if same file
        same = (
            hashlib.md5(raw_upload).hexdigest() ==
            hashlib.md5(raw_github).hexdigest()
        )

        if same:
            st.sidebar.info("✔ File sama dengan file database GitHub. Menggunakan versi GitHub.")
            return github_file

        # Ask confirmation
        with st.sidebar.expander("Konfirmasi Update File → GitHub"):
            confirm = st.radio("Upload file baru ke GitHub?", ["Tidak", "Ya"], key=f"{key}_confirm")

        if confirm == "Ya":
            if update_file(repo, file_path, raw_upload, branch):
                st.sidebar.success("✅ File berhasil diupdate ke GitHub.")
                st.cache_data.clear()
            else:
                st.sidebar.error("❌ Gagal update GitHub. Menggunakan file upload lokal.")

        return upload_bio

    # ---- STEP 3: No upload → return GitHub ----
    return github_file


# ==========================================================
# Update file to GitHub (PUT)
# ==========================================================
def update_file(repo, file_path, raw_bytes, branch="main"):
    meta_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    meta = requests.get(meta_url, headers=GITHUB_HEADERS).json()
    sha = meta.get("sha")

    payload = {
        "message": f"Update {file_path} via dashboard",
        "content": base64.b64encode(raw_bytes).decode(),
        "sha": sha,
        "branch": branch
    }

    put_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    res = requests.put(put_url, headers=GITHUB_HEADERS, json=payload)

    return res.status_code in (200, 201)
