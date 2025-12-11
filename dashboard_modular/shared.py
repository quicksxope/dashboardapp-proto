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


# ============================================================================================
# 📌 FIX #1 — GitHub fetch tetap pakai cache, tapi BytesIO selalu dibuat ulang setiap return
# ============================================================================================
@st.cache_data(ttl=3600)
def get_github_file_and_hash(repo_path, branch="main"):
    """
    Ambil file dari GitHub dan return (content_bytes, hash, sha)
    - NOTICE: return content_bytes (bukan BytesIO) supaya pointer tidak tersimpan dalam cache
    """
    url = f"https://api.github.com/repos/{repo_path}?ref={branch}"
    res = requests.get(url, headers=GITHUB_HEADERS)

    if res.status_code == 200:
        try:
            json_data = res.json()
            content_b64 = json_data["content"]
            content = base64.b64decode(content_b64)
            return content, hashlib.md5(content).hexdigest(), json_data["sha"]

        except Exception as e:
            st.error(f"⚠️ Gagal parsing file dari GitHub: {e}")
    else:
        st.error(f"⚠️ Gagal ambil file dari GitHub ({repo_path}): {res.status_code}")

    return None, None, None



# ============================================================================================
# 📌 FIX #2 — Selalu buat BytesIO BARU + reset pointer sebelum return
# ============================================================================================
def to_bytesio(content_bytes):
    """
    Selalu buat BytesIO baru, pointer otomatis di posisi 0.
    """
    if content_bytes is None:
        return None
    return BytesIO(content_bytes)



def update_file_to_github(repo_path, file_bytes, commit_msg="Update via dashboard", branch="main"):
    """Update file di GitHub dengan SHA terbaru."""
    
    repo, file_path = repo_path.split("/contents/", 1)

    # Step 1: GET SHA terbaru
    get_url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    res_get = requests.get(get_url, headers=GITHUB_HEADERS)

    if res_get.status_code != 200:
        st.error(f"❌ Gagal ambil SHA untuk {file_path}")
        st.code(res_get.text)
        return False

    sha = res_get.json().get("sha")

    # Step 2: Upload file baru
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



# ============================================================================================
# 📌 FIX #3 — get_file() sekarang selalu return BytesIO baru, aman untuk pandas
# ============================================================================================
def get_file(repo_path: str, label: str, key: str, branch="main"):
    # Validasi path format
    if "/contents/" not in repo_path:
        st.error("❌ repo_path harus dalam format '<repo>/contents/<path>'")
        return None

    repo, file_path = repo_path.split("/contents/", 1)

    # Upload dari user
    uploaded = st.sidebar.file_uploader(label, type="xlsx", key=key)

    # Ambil file dari GitHub (CACHED sebagai raw bytes, bukan BytesIO!)
    github_bytes, github_hash, github_sha = get_github_file_and_hash(
        f"{repo}/contents/{file_path}", branch=branch
    )

    # Safety: buat BytesIO baru setiap kali
    github_file = to_bytesio(github_bytes)

    # ============================================================
    # CASE 1 — User upload file
    # ============================================================
    if uploaded:
        file_bytes = uploaded.getvalue()
        uploaded_hash = get_file_hash(file_bytes)

        # File sama → pakai default GitHub
        if uploaded_hash == github_hash:
            st.sidebar.info("✅ Uploaded file sama dengan Database. Menggunakan file default.")
            return to_bytesio(github_bytes)

        # File berbeda → minta konfirmasi update GitHub
        with st.sidebar.expander("⚠️ Konfirmasi Penggantian File"):
            st.warning("File yang diupload berbeda dari Database.")
            confirm = st.radio(
                "Yakin ingin mengganti file default dengan yang ini?",
                ["Tidak", "Ya"],
                key=f"{key}_confirm"
            )

        if confirm == "Ya":
            st.sidebar.warning("📤 Mengunggah ke Database...")
            success = update_file_to_github(
                f"{repo}/contents/{file_path}",
                file_bytes,
                f"Update {key} from dashboard",
                branch=branch
            )

            if success:
                # Refresh cache agar file terbaru diambil
                st.cache_data.clear()
                timestamp = datetime.now()
                st.session_state[f"{key}_uploaded_at"] = timestamp
                st.sidebar.success("✅ File Baru berhasil diunggah ke Database.")
                st.sidebar.markdown(f"🕒 Uploaded at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

                return to_bytesio(file_bytes)

            else:
                st.sidebar.error("❌ Gagal upload ke Database. Menggunakan file default.")
                return to_bytesio(github_bytes)

        else:
            st.sidebar.info("📥 Upload dibatalkan. Menggunakan file default.")
            return to_bytesio(github_bytes)

    # ============================================================
    # CASE 2 — Tidak ada upload → return file default GitHub
    # ============================================================
    st.sidebar.info("📥 Tidak ada file diupload. Menggunakan file Database.")
    return github_file
