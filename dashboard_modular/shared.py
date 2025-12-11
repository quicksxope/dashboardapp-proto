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
# FETCH FILE USING RAW.GITHUBUSERCONTENT.COM
# NEVER RETURNS 0 BYTES
# ============================================================
@st.cache_data(ttl=3600)
def fetch_github_bytes(repo_path, branch="main"):
    """
    ALWAYS fetch raw file bytes.
    repo_path format: owner/repo/contents/path/to/file.xlsx
    """
    try:
        repo, file_path = repo_path.split("/contents/", 1)
    except:
        return None, None, 400

    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"

    res = requests.get(raw_url)

    if res.status_code != 200:
        return None, None, res.status_code

    content = res.content  # raw bytes (never empty unless file truly empty)
    file_hash = hashlib.md5(content).hexdigest()

    return content, file_hash, res.status_code


# ============================================================
# ALWAYS return a fresh BytesIO object
# ============================================================
def to_fresh_bytesio(content_bytes):
    if content_bytes is None:
        return None

    bio = BytesIO(content_bytes)
    bio.seek(0)
    return bio


# ============================================================
# UPDATE FILE TO GITHUB (Contents API)
# ============================================================
def update_file(repo, file_path, content_bytes, branch="main"):
    # Step 1 — get SHA (required by GitHub API)
    meta_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    meta_res = requests.get(meta_url, headers=GITHUB_HEADERS)

    if meta_res.status_code != 200:
        st.sidebar.error("❌ Gagal mengambil SHA dari GitHub.")
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
# MAIN FUNCTION — get_file()
# ALWAYS returns: fresh BytesIO or None
# ============================================================
def get_file(repo_path: str, label: str, key: str, branch="main"):
    """
    Safest version:
    ✔ Raw fetch (never zero bytes)
    ✔ Fresh BytesIO every call
    ✔ Streamlit reload safe
    ✔ GitHub upload supported
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus format '<repo>/contents/<file>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # -------------------------
    # 1) GET FILE FROM GITHUB (RAW)
    # -------------------------
    github_bytes, github_hash, status = fetch_github_bytes(
        f"{repo}/contents/{file_path}", branch
    )

    github_file = to_fresh_bytesio(github_bytes)

    # Debug info
    with st.sidebar.expander(f"DEBUG: {key}", expanded=False):
        st.write("GitHub HTTP Status:", status)
        st.write("GitHub Bytes:", None if github_bytes is None else len(github_bytes))
        st.write("GitHub Hash:", github_hash)

    # If GitHub truly failed
    if github_bytes is None:
        st.sidebar.error("❌ Tidak bisa mengambil file dari GitHub.")
        github_file = None

    # -------------------------
    # 2) USER UPLOAD
    # -------------------------
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_uploader")

    if uploaded:
        uploaded_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(uploaded_bytes).hexdigest()

        with st.sidebar.expander("Upload Debug"):
            st.write("Uploaded bytes:", len(uploaded_bytes))
            st.write("Uploaded hash:", uploaded_hash)

        # If same as GitHub DB
        if github_hash and uploaded_hash == github_hash:
            st.sidebar.info("✔ File sama dengan database. Menggunakan versi GitHub.")
            return to_fresh_bytesio(github_bytes)

        # Ask user to confirm update
        with st.sidebar.expander("Konfirmasi Update File"):
            confirm = st.radio(
                "Update file ke GitHub?",
                ["Tidak", "Ya"],
                key=f"{key}_confirm"
            )

        if confirm == "Ya":
            ok = update_file(repo, file_path, uploaded_bytes, branch)
            if ok:
                st.sidebar.success("✔ File berhasil diupload ke GitHub.")
                st.cache_data.clear()
                return to_fresh_bytesio(uploaded_bytes)
            else:
                st.sidebar.error("❌ Gagal upload. Menggunakan versi GitHub.")
                return github_file

        # User did not update → use uploaded only locally
        st.sidebar.info("📄 Menggunakan file hasil upload (lokal).")
        return to_fresh_bytesio(uploaded_bytes)

    # -------------------------
    # 3) NO UPLOAD → use GitHub version
    # -------------------------
    if github_bytes is None or len(github_bytes) == 0:
        st.sidebar.error("❌ GitHub file kosong atau tidak ditemukan.")
        return None

    return github_file
