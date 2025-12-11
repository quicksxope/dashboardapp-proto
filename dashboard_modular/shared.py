import streamlit as st
import requests
import base64
import hashlib
from io import BytesIO
from datetime import datetime

# ================================
# GitHub API Headers
# ================================
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}


# ================================
# Fetch raw bytes from GitHub
# ================================
def fetch_github_file(repo_path, branch="main"):
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code != 200:
        st.error(f"❌ Failed to fetch GitHub file: {res.status_code}")
        return None, None, None

    data = res.json()
    content = base64.b64decode(data["content"])
    file_hash = hashlib.md5(content).hexdigest()
    sha = data.get("sha")

    return content, file_hash, sha


# ================================
# Upload to GitHub (PUT)
# ================================
def upload_to_github(repo, file_path, content_bytes, sha, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    payload = {
        "message": f"Update {file_path}",
        "content": base64.b64encode(content_bytes).decode(),
        "sha": sha,
        "branch": branch
    }

    res = requests.put(url, headers=GITHUB_HEADERS, json=payload)

    return res.status_code in (200, 201)


# ================================
# Main get_file() Function
# ================================
def get_file(repo_path, label, key, branch="main"):
    """
    ALWAYS return a fresh BytesIO.
    Upload new file to GitHub if confirmed.
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path must be '<repo>/contents/<filepath>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # ---- 1. Load GitHub file
    github_bytes, github_hash, github_sha = fetch_github_file(
        f"{repo}/contents/{file_path}", branch
    )

    github_bio = BytesIO(github_bytes) if github_bytes else None
    if github_bio:
        github_bio.seek(0)

    # ---- 2. User Upload
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=f"{key}_uploader")

    if uploaded:
        uploaded_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(uploaded_bytes).hexdigest()

        # If same file → use GitHub version
        if uploaded_hash == github_hash:
            st.sidebar.info("✔ File sama seperti di database. Menggunakan versi GitHub.")
            return BytesIO(github_bytes)

        # Ask confirmation
        with st.sidebar.expander("Konfirmasi Penggantian File"):
            confirm = st.radio(
                "Replace file in GitHub?",
                ["Tidak", "Ya"],
                key=f"{key}_confirm"
            )

        if confirm == "Ya":
            success = upload_to_github(repo, file_path, uploaded_bytes, github_sha, branch)
            if success:
                st.sidebar.success("✅ File berhasil diupload ke GitHub!")
                st.cache_data.clear()
                bio = BytesIO(uploaded_bytes)
                bio.seek(0)
                return bio
            else:
                st.sidebar.error("❌ Upload gagal! Menggunakan file lama.")
                return github_bio

        # If user says No → use GitHub file
        return github_bio

    # ---- 3. No upload → return GitHub version
    return github_bio
