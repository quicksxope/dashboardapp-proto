import streamlit as st
import requests
import base64
import hashlib
from io import BytesIO

# ==========================================
# GitHub API Headers
# ==========================================
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}

# ==========================================
# Fetch file bytes + SHA from GitHub
# ==========================================
def fetch_github_file(repo, file_path, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code != 200:
        return None, None, None

    data = res.json()
    content = base64.b64decode(data["content"])
    file_hash = hashlib.md5(content).hexdigest()
    sha = data.get("sha")

    return content, file_hash, sha


# ==========================================
# Upload file to GitHub
# ==========================================
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


# ==========================================
# Main get_file() Function
# ==========================================
def get_file(repo_path, label, key, branch="main"):
    """
    Stable file loader with:
    - GitHub fallback
    - User upload with confirmation
    - Latest file stored in session_state
    """

    if "/contents/" not in repo_path:
        st.error("❌ repo_path must be '<repo>/contents/<file>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # ---------------------------------------
    # 1. If previously uploaded this session
    # ---------------------------------------
    if f"{key}_bytes" in st.session_state:
        bio = BytesIO(st.session_state[f"{key}_bytes"])
        bio.seek(0)
        return bio

    # ---------------------------------------
    # 2. Load from GitHub
    # ---------------------------------------
    github_bytes, github_hash, github_sha = fetch_github_file(repo, file_path, branch)

    if github_bytes is None:
        st.error("❌ Cannot load file from GitHub")
        return None

    github_bio = BytesIO(github_bytes)
    github_bio.seek(0)

    # ---------------------------------------
    # 3. User upload UI
    # ---------------------------------------
    uploaded = st.sidebar.file_uploader(label, type=["xlsx"], key=f"{key}_uploader")

    if uploaded:
        uploaded_bytes = uploaded.getvalue()
        uploaded_hash = hashlib.md5(uploaded_bytes).hexdigest()

        # If same file → ignore
        if uploaded_hash == github_hash:
            st.sidebar.info("✔ File sama seperti versi GitHub — tidak diganti.")
            st.session_state[f"{key}_bytes"] = github_bytes
            return BytesIO(github_bytes)

        # Ask confirmation
        confirm = st.sidebar.radio(
            "Replace GitHub file?",
            ["Tidak", "Ya"],
            horizontal=True,
            key=f"{key}_confirm"
        )

        if confirm == "Ya":
            ok = upload_to_github(repo, file_path, uploaded_bytes, github_sha, branch)
            if ok:
                st.sidebar.success("✅ File berhasil diupload ke GitHub!")
                st.session_state[f"{key}_bytes"] = uploaded_bytes
                return BytesIO(uploaded_bytes)
            else:
                st.sidebar.error("❌ Upload gagal, memakai file GitHub.")
                return github_bio

        # If user chooses NOT to replace GitHub
        return github_bio

    # ---------------------------------------
    # No upload → return GitHub version
    # ---------------------------------------
    st.session_state[f"{key}_bytes"] = github_bytes
    return github_bio
