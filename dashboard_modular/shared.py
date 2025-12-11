# shared.py
import hashlib
import requests
import streamlit as st
import base64
from io import BytesIO
from datetime import datetime


# ============================================================
# GitHub auth headers
# ============================================================
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}


# ============================================================
# Fetch GitHub file (ONLY RETURNS BYTES, NEVER BytesIO)
# Cached for stability (avoids multiple fetches)
# ============================================================
@st.cache_data(ttl=3600)
def fetch_github_bytes(repo_path, branch="main"):
    """
    Returns:
        (bytes_or_None, hash_or_None, status_code)
    """
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)
    status = res.status_code

    if status != 200:
        return None, None, status

    try:
        data = res.json()
        content_b64 = data.get("content", None)
        if content_b64 is None:
            return None, None, status

        content = base64.b64decode(content_b64)
        file_hash = hashlib.md5(content).hexdigest()
        return content, file_hash, status

    except Exception:
        return None, None, status


# ============================================================
# Helper: always return fresh BytesIO so pandas NEVER sees EOF
# ============================================================
def to_fresh_bytesio(content_bytes):
    if content_bytes is None:
        return None

    bio = BytesIO(content_bytes)
    bio.seek(0)
    return bio


# ============================================================
# GitHub update helper
# ============================================================
def update_file(repo, file_path, content_bytes, branch="main"):
    # Step 1 — get SHA
    meta_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    meta_res = requests.get(meta_url, headers=GITHUB_HEADERS)

    if meta_res.status_code != 200:
        st.sidebar.error("❌ Gagal ambil SHA file GitHub.")
        return False

    sha = meta_res.json().get("sha")

    payload = {
        "message": f"Update {file_path}",
        "content": base64.b64encode(content_bytes).decode(),
        "sha": sha,
        "branch": branch
    }

    put_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    put_res = requests.put(put_url, headers=GITHUB_HEADERS, json=payload)

    return put_res.status_code in (200, 201)


# ============================================================
# MASTER FUNCTION – get_file()
# ============================================================
def get_file(repo_path: str, label: str, key: str, branch="main"):
    """
    Returns ALWAYS a fresh BytesIO or None.
    NEVER returns stale buffer.
    Ensures reload-safe Excel file handling.
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus format '<repo>/contents/<file>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # -------- 1) Fetch GitHub file ----------
    github_bytes, github_hash, status = fetch_github_bytes(
        f"{repo}/contents/{file_path}", branch
    )

    # Fresh BytesIO every time
    github_file = to_fresh_bytesio(github_bytes)

    # Sidebar diagnostics
    with st.sidebar.expander(f"DEBUG: {key}", expanded=False):
        st.write("GitHub HTTP Status:", status)
        st.write("GitHub Bytes:", None if github_bytes is None else len(github_bytes))
        st.write("GitHub Hash:", github_hash)

    # -------- 2) User upload ----------
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_uploader")

    if uploaded:
        uploaded_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(uploaded_bytes).hexdigest()

        with st.sidebar.expander("Upload Debug"):
            st.write("Uploaded bytes:", len(uploaded_bytes))
            st.write("Uploaded hash:", uploaded_hash)

        # If uploaded equals DB file
        if github_hash and uploaded_hash == github_hash:
            st.sidebar.info("✔ File sama dengan database. Menggunakan default GitHub.")
            return to_fresh_bytesio(github_bytes)

        # Ask user confirmation to update
        with st.sidebar.expander("Konfirmasi Update File"):
            confirm = st.radio(
                "Update file ke GitHub?",
                ["Tidak", "Ya"],
                key=f"{key}_confirm"
            )

        if confirm == "Ya":
            ok = update_file(repo, file_path, uploaded_bytes, branch)
            if ok:
                st.sidebar.success("✔ Berhasil upload ke GitHub.")
                st.cache_data.clear()
                return to_fresh_bytesio(uploaded_bytes)
            else:
                st.sidebar.error("❌ Gagal upload. Menggunakan GitHub version.")
                return github_file

        # If user cancels update → use local upload
        st.sidebar.info("📄 Menggunakan file hasil upload (lokal).")
        return to_fresh_bytesio(uploaded_bytes)

    # -------- 3) No upload ----------
    if github_bytes is None or len(github_bytes) == 0:
        st.sidebar.error("❌ GitHub file kosong atau tidak ditemukan.")
        return None

    return github_file
