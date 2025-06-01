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

def update_file_to_github(repo_path, file_bytes, commit_msg="Update via dashboard", branch="main"):
    """Update file di GitHub dengan SHA yang selalu fresh."""
    # Pisah repo & file path
    repo, file_path = repo_path.split("/contents/", 1)

    # 🔁 Step 1: GET SHA terbaru langsung dari GitHub
    get_url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res_get = requests.get(get_url, headers=GITHUB_HEADERS)

    if res_get.status_code != 200:
        st.error(f"❌ Gagal ambil SHA untuk {file_path}")
        st.code(res_get.text)
        return False

    sha = res_get.json().get("sha")

    # 🔁 Step 2: Prepare PUT payload
    content_b64 = base64.b64encode(file_bytes).decode()
    put_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    payload = {
        "message": commit_msg,
        "content": content_b64,
        "branch": branch,
        "sha": sha
    }

    res_put = requests.put(put_url, headers=GITHUB_HEADERS, json=payload)

    if res_put.status_code not in (200, 201):
        st.error(f"❌ GitHub PUT error {res_put.status_code}")
        st.code(res_put.text)

    return res_put.status_code in (200, 201)



def get_file(repo_path: str, label: str, key: str, branch="main"):
    # Pisahkan ke REPO dan FILE_PATH
    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus dalam format '<repo>/contents/<path>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)
    github_file, github_hash, github_sha = get_github_file_and_hash(f"{repo}/contents/{file_path}", branch=branch)

    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = get_file_hash(file_bytes)

        if uploaded_hash == github_hash:
            st.sidebar.info("✅ Uploaded file sama dengan GitHub. Pakai default.")
            return github_file
        else:
            with st.sidebar.expander("⚠️ Konfirmasi Penggantian File"):
                st.warning("File yang diupload berbeda dari GitHub.")
                confirm = st.radio(
                    "Yakin ingin mengganti file default dengan yang ini?",
                    ["Tidak", "Ya"],
                    key=f"{key}_confirm"
                )

            if confirm == "Ya":
                st.sidebar.warning("📤 Mengunggah ke GitHub...")
                success = update_file_to_github(
                f"{repo}/contents/{file_path}",
                file_bytes,
                f"Update {key} from dashboard",
                branch=branch
                )

                
                if success:
                    timestamp = datetime.now()
                    st.session_state[f"{key}_uploaded_at"] = timestamp
                    st.sidebar.success("✅ File berhasil diunggah ke GitHub.")
                    st.sidebar.markdown(f"🕒 Uploaded at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    return BytesIO(file_bytes)
                else:
                    st.sidebar.error("❌ Gagal upload ke GitHub. Gunakan file default.")
                    return github_file
            else:
                st.sidebar.info("📥 Upload dibatalkan. Menggunakan file GitHub.")
                return github_file
    else:
        st.sidebar.info("📥 Tidak ada file diupload. Menggunakan file GitHub.")
        return github_file

