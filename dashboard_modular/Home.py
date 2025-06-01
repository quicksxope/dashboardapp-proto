import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth import require_login
from io import BytesIO
import hashlib
from datetime import datetime
import requests


st.set_page_config(page_title="Dashboard Home", layout="wide")
require_login()

# URL raw file dari GitHub (ganti sesuai repo lo)
GITHUB_PROJECT_FILE_URL = "https://raw.githubusercontent.com/quicksxope/Dashboard-New/main/data/Data_project_monitoring.xlsx"
GITHUB_CONTRACT_FILE_URL = "https://raw.githubusercontent.com/quicksxope/Dashboard-New/main/data/data_kontrak_new.xlsx"

def get_file_hash(file):
    return hashlib.md5(file.getvalue()).hexdigest()

@st.cache_data(ttl=3600)
def load_excel_from_github(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        return None

# --- File uploader logic ---
uploaded_project_file = st.sidebar.file_uploader("📊 Upload Project Data", type="xlsx", key="project_file")
uploaded_contract_file = st.sidebar.file_uploader("📁 Upload Contract Data", type="xlsx", key="contract_file")

# --- Project file ---
if uploaded_project_file:
    file_hash = get_file_hash(uploaded_project_file)
    if st.session_state.get("project_file_hash") != file_hash:
        st.session_state.project_file_hash = file_hash
        st.session_state.project_upload_time = datetime.now()
    project_file = BytesIO(uploaded_project_file.getvalue())
    st.sidebar.markdown(f"🕒 Last Project Upload: {st.session_state.project_upload_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    project_file = load_excel_from_github(GITHUB_PROJECT_FILE_URL)
    st.sidebar.info("📥 Using default project file from GitHub")

# --- Contract file ---
if uploaded_contract_file:
    file_hash = get_file_hash(uploaded_contract_file)
    if st.session_state.get("contract_file_hash") != file_hash:
        st.session_state.contract_file_hash = file_hash
        st.session_state.contract_upload_time = datetime.now()
    contract_file = BytesIO(uploaded_contract_file.getvalue())
    st.sidebar.markdown(f"🕒 Last Contract Upload: {st.session_state.contract_upload_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    contract_file = load_excel_from_github(GITHUB_CONTRACT_FILE_URL)
    st.sidebar.info("📥 Using default contract file from GitHub")















st.markdown("""
<div style="
    background: linear-gradient(to right, #3498db, #2ecc71);
    padding: 1.2rem 2rem;
    font-size: 2rem;
    font-weight: 800;
    color: white;
    border-radius: 12px;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    margin-bottom: 1.5rem;
">
    Dashboard Summary
</div>
""", unsafe_allow_html=True)

# Custom card renderer
def render_card(title, value, subtext="", color="#fef9c3", icon="📦"):
    st.markdown(f'''
        <div style="
            background-color:{color};
            padding:1.4rem 1.6rem;
            border-radius:16px;
            box-shadow:0 1px 4px rgba(0,0,0,0.05);
            font-family: 'Inter', sans-serif;
            margin-bottom: 20px;
        ">
            <div style="font-size:0.9rem; color:#4b5563;">{icon} {title}</div>
            <div style="font-size:2rem; font-weight:700; color:#111827;">{value}</div>
            <div style="font-size:0.9rem; color:#6b7280;">{subtext}</div>
        </div>
    ''', unsafe_allow_html=True)


def render_progress_card(title, percent, color="#3b82f6", icon="📊"):
    percent = max(0, min(percent, 100))
    st.markdown(f"""
        <div style="
            background-color: #1f2937;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            font-family: 'Inter', sans-serif;
            color: #f9fafb;
        ">
            <div style="font-weight:600; font-size:1.05rem; margin-bottom:0.5rem;">
                {icon} {title}
            </div>
            <div style="background-color: #374151; height: 10px; border-radius: 9999px; overflow: hidden; margin: 0.4rem 0;">
                <div style="width: {percent:.2f}%; background-color: {color}; height: 100%;"></div>
            </div>
            <div style="font-size: 0.85rem;">
                Progress: {percent:.2f}%
            </div>
        </div>
    """, unsafe_allow_html=True)



def render_card_with_donut(title, value, subtext, labels, values, colors, icon="🥯", total_value=None, remaining=None):
    col1, col2 = st.columns([1.2, 1])

    with col1:
        percent = (values[0] / sum(values) * 100) if sum(values) else 0
        st.markdown(f"""
            <div style="
                background-color: #eef2ff;
                padding: 1.6rem;
                border-radius: 16px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
                font-family: 'Inter', sans-serif;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.9rem; color: #6b7280;">{icon} {title}</div>
                <div style="font-size: 2rem; font-weight: 700; color: #111827;">{value}</div>
                <div style="font-size: 0.9rem; color: #9ca3af;">{subtext}</div>
                <hr style="margin: 0.8rem 0; border: none; border-top: 1px solid #e5e7eb;" />
                <div style="font-size: 0.85rem; color: #6b7280;">
                    <p><strong>Total Contract Value:</strong><br>Rp {total_value:,.0f} M</p>
                    <p><strong>Remaining Value:</strong><br>Rp {remaining:,.0f} M</p>
                    <p style="color: {'#10b981' if percent > 80 else '#f59e0b'};">
                        {percent:.1f}% of contract value realized
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        percent = (values[0] / sum(values) * 100) if sum(values) else 0
        fig = go.Figure(go.Pie(hole=0.85, pull=0, rotation=90,
            labels=labels,
            values=values,
            marker=dict(colors=['#0ea5e9', '#e2e8f0']),
            textinfo='none',
            hoverinfo='label+value+percent'
        ))
        fig.update_layout(
            annotations=[dict(text=f"{percent:.1f}%", font_size=20, showarrow=False)],
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=250
        )
        st.plotly_chart(fig, use_container_width=True, key=f"donut_{title}")

        st.markdown(f"""
            <div style="text-align:center; font-size: 0.85rem; color: #6b7280; margin-top: -0.5rem;">
                Breakdown between realized and remaining<br>
                Realized amount is {percent:.1f}% of the total
            </div>
        """, unsafe_allow_html=True)


# Default values in case files are not uploaded
avg_completion = 0.0
avg_realized_pct = 0.0
overdue_rate = 0.0
remaining_pct = 0.0

if project_file:
    dfp = pd.read_excel(pd.ExcelFile(project_file), sheet_name=0)
    dfp.columns = dfp.columns.str.strip()
    dfp['KONTRAK'] = dfp['KONTRAK'].astype(str).str.upper().str.strip()
    dfp['STATUS'] = dfp['STATUS'].astype(str).str.upper().str.strip()
    dfp['% COMPLETE'] = dfp['% COMPLETE'].apply(lambda x: x * 100 if x <= 1 else x)
    dfp['START'] = pd.to_datetime(dfp['START'], errors='coerce')
    dfp['PLAN END'] = pd.to_datetime(dfp['PLAN END'], errors='coerce')

    total_projects = dfp['KONTRAK'].nunique()
    avg_completion = dfp['% COMPLETE'].mean()
    total_tasks = len(dfp)
    on_time = ((dfp['PLAN END'] >= pd.Timestamp.today()) & (dfp['STATUS'] == 'SELESAI')).sum()
    overdue = ((dfp['PLAN END'] < pd.Timestamp.today()) & (dfp['STATUS'] != 'SELESAI')).sum()
    completed_tasks = dfp[dfp['STATUS'] == 'SELESAI'].shape[0]
    overdue_rate = (overdue / total_tasks) * 100 if total_tasks else 0

    st.subheader("🏗️ Project Monitoring Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        render_card("Total Projects", total_projects, "Unique KONTRAK", "#fef9c3", "📁")
    with col2:
        render_card("Total Tasks", total_tasks, "Rows of activities", "#dcfce7", "📝")
    with col3:
        render_card("Overdue Tasks", overdue, "Past due", "#fde68a", "⚠️")

    col4, col5, col6 = st.columns(3)
    with col4:
        render_card("On-Time Tasks", on_time, "Completed on-time", "#bae6fd", "⏱️")
    with col5:
        render_card("Completed Tasks", completed_tasks, f"of {total_tasks} total", "#d1fae5", "✅")
    col1, col2 = st.columns(2)
    with col1:
        render_progress_card("Avg Completion %", avg_completion, "#60a5fa", "🛠️")
    with col2:
        render_progress_card("Overdue Rate", overdue_rate, "#f87171", "⏰")
        

if contract_file:
    df = pd.read_excel(contract_file)
    df.columns = df.columns.str.strip()
    df.rename(columns={
        'Start Date': 'START',
        'End Date': 'END',
        'PROGRESS ACTUAL': 'PROGRESS',
        'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE',
        'Realisasi On  2023-2024': 'REALIZATION',
        '% Realisasi': 'REALIZED_PCT',
        'TIME GONE %': 'TIME_PCT',
        'STATUS': 'STATUS'
    }, inplace=True)

    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['CONTRACT_VALUE'] = pd.to_numeric(df['CONTRACT_VALUE'], errors='coerce')
    df['REALIZATION'] = pd.to_numeric(df['REALIZATION'], errors='coerce')
    df['REALIZED_PCT'] = pd.to_numeric(df['REALIZED_PCT'], errors='coerce') * 100
    df['TIME_PCT'] = pd.to_numeric(df['TIME_PCT'], errors='coerce') * 100

    total_contracts = len(df)
    avg_realized_pct = df['REALIZED_PCT'].mean()
    completed = df[df['REALIZED_PCT'] >= 100].shape[0]
    active_contracts = df[df['STATUS'].str.contains("ACTIVE", case=False, na=False)].shape[0]
    realized = df['REALIZATION'].sum()
    total_value = df['CONTRACT_VALUE'].sum()
    remaining = total_value - realized
    remaining_pct = (remaining / total_value) * 100 if total_value else 0

    st.subheader("📁 Contract Performance Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_card("Total Contracts", total_contracts, "", "#fef9c3", "📦")
    with col2:
        render_card("Completed (100%)", completed, "", "#dcfce7", "✅")
    with col3:
        render_card("Avg Realization %", f"{avg_realized_pct:.1f}%", "", "#e0f2fe", "📈")
    with col4:
        render_card("Active Contracts", active_contracts, "", "#f3e8ff", "🟢")

    col1, col2 = st.columns(2)
    with col1:
        render_progress_card("Remaining Value %", remaining_pct, "#facc15", "💸")
    with col2:
        render_progress_card("Avg Realization %", avg_realized_pct, "#34d399", "📦")

    
        

    render_card_with_donut(
        title="Realization",
        value=f"Rp {realized:,.0f} M",
        subtext="Total realized vs contract value",
        labels=["Realized", "Remaining"],
        values=[realized, remaining],
        colors=["#6366f1", "#e5e7eb"],
        icon="🥯",
        total_value=total_value,
        remaining=remaining
    )
else:
    st.info("Please upload both Project and Contract Excel files.")
