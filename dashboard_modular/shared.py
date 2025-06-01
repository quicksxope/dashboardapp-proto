# shared.py
import hashlib
import requests
from io import BytesIO
import streamlit as st
import base64
from datetime import datetime

# --- Token GitHub dari secrets ---
GITHUB_HEADERS = {
    "Authorization": f"token {st.secrets['github_token']}",
    "Accept": "application/vnd.github.v3+json"
}

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

@st.cache_data(ttl=3600)
def get_github_file_and_hash(repo_path, branch="main"):
    """
    Ambil file dari GitHub dan return (BytesIO, hash, sha)
    """
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code == 200:
        try:
            json_data = res.json()
            content_b64 = json_data["content"]
            content = base64.b64decode(content_b64)
            return BytesIO(content), hashlib.md5(content).hexdigest(), json_data["sha"]
        except Exception as e:
            st.error(f"⚠️ Gagal parsing file dari GitHub: {e}")
    else:
        st.error(f"⚠️ Gagal ambil file dari GitHub ({repo_path}): {res.status_code}")
    
    return None, None, None

def update_file_to_github(repo_path, file_bytes, commit_msg="Update via dashboard", branch="main", sha=None):
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
    Ambil file dari uploader atau GitHub:
    - Kalau user upload → simpan & update ke GitHub jika beda
    - Kalau sama → pakai file GitHub
    - Kalau tidak upload → fallback GitHub
    Return: BytesIO file
    """
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)
    github_file, github_hash, github_sha = get_github_file_and_hash(repo_path, branch=branch)

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = get_file_hash(file_bytes)

        if uploaded_hash == github_hash:
            st.sidebar.info("✅ Uploaded file sama persis dengan GitHub. Pakai default.")
            return github_file
        else:
            st.sidebar.warning("🆕 File berbeda. Mengunggah ke GitHub...")
            success = update_file_to_github(
                repo_path,
                file_bytes,
                f"Auto-update {key} from dashboard",
                branch=branch,
                sha=github_sha
            )
            if success:
                timestamp = datetime.now()
                st.session_state[f"{key}_uploaded_at"] = timestamp
                st.sidebar.success("📤 File berhasil diunggah ke GitHub.")
                st.sidebar.markdown(f"🕒 Uploaded at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                return BytesIO(file_bytes)
            else:
                st.sidebar.error("❌ Gagal upload ke GitHub. Pakai default.")
                return github_file
    else:
        st.sidebar.info("📥 Menggunakan file default dari GitHub.")
        return github_file
