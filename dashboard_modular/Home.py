import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth import require_login
from io import BytesIO
import hashlib
from datetime import datetime
import requests
import numpy as np

st.set_page_config(page_title="Dashboard Home", layout="wide")
require_login()

from shared import get_file


# === SAFE HELPER FOR LOADING EXCEL FILES ===
def safe_read_excel(file, sheet_name=None):
    if file is None:
        st.error("❌ File gagal dimuat. Silakan upload ulang.")
        st.stop()

    try:
        if sheet_name:
            return pd.read_excel(file, sheet_name=sheet_name)
        return pd.read_excel(file)
    except Exception as e:
        st.error(f"❌ Gagal membaca file Excel: {e}")
        st.stop()



# === LOAD FILES ===
project_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/Data_project_monitoring.xlsx",
    "📊 Upload Project Data",
    "project_file"
)

contract_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/data_kontrak_new.xlsx",
    "📁 Upload Contract Data",
    "contract_file"
)

payment_term_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/Long_Format_Payment_Terms.xlsx",
    "💵 Upload Payment Term File",
    "payment_term_file"
)



# === UI HEADER ===
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



# === RENDER UTILITY FUNCTIONS ===
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



# ========================================================================================
# 🟦 SECTION 1 — PROJECT FILE
# ========================================================================================
if project_file:
    excel = safe_read_excel(project_file)  # SAFE
    dfp = safe_read_excel(project_file, sheet_name="BASE DATA (wajib update)")

    dfp.columns = dfp.columns.str.strip().str.upper()

    required_cols = ['KONTRAK', 'STATUS', '% COMPLETE', 'START', 'PLAN END']
    missing_cols = [col for col in required_cols if col not in dfp.columns]

    if missing_cols:
        st.error(f"Kolom berikut tidak ditemukan di file Project: {', '.join(missing_cols)}")
        st.stop()

    # --- Data cleaning ---
    dfp['KONTRAK'] = dfp['KONTRAK'].astype(str).str.upper().str.strip()
    dfp['STATUS'] = dfp['STATUS'].astype(str).str.upper().str.strip()
    dfp['% COMPLETE'] = pd.to_numeric(dfp['% COMPLETE'], errors='coerce').fillna(0)
    dfp['% COMPLETE'] = dfp['% COMPLETE'].apply(lambda x: x * 100 if x <= 1 else x)
    dfp['START'] = pd.to_datetime(dfp['START'], errors='coerce')
    dfp['PLAN END'] = pd.to_datetime(dfp['PLAN END'], errors='coerce')

    today = pd.Timestamp.today()

    total_projects = dfp['KONTRAK'].nunique()
    total_tasks = len(dfp)
    avg_completion = dfp['% COMPLETE'].mean()
    on_time = dfp[(dfp['STATUS'] == 'SELESAI') & (dfp['PLAN END'] >= today)].shape[0]
    overdue = dfp[(dfp['PLAN END'] < today) & (dfp['% COMPLETE'] < 100)].shape[0]
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

    col4, col5, _ = st.columns(3)
    with col4:
        render_card("On-Time Tasks", on_time, "Completed on time", "#bae6fd", "⏱️")
    with col5:
        render_card("Completed Tasks", completed_tasks, f"of {total_tasks} total", "#d1fae5", "✅")

    col1, col2 = st.columns(2)
    with col1:
        render_progress_card("Avg Completion %", avg_completion, "#60a5fa", "🛠️")
    with col2:
        render_progress_card("Overdue Rate", overdue_rate, "#f87171", "⏰")



# ========================================================================================
# 🟩 SECTION 2 — CONTRACT FILE
# ========================================================================================
if contract_file:
    df = safe_read_excel(contract_file)
    df.columns = df.columns.str.strip()

    df.rename(columns={
        'Start Date': 'START',
        'End Date': 'END',
        'PROGRESS ACTUAL': 'PROGRESS',
        'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE',
        'Realisasi On  2023-2024': 'REALIZATION_2324',
        'Realisasi On  2025': 'REALIZATION_2025',
        '% Realisasi': 'REALIZED_PCT',
        'TIME GONE %': 'TIME_PCT',
    }, inplace=True)

    df['REALIZATION'] = df[['REALIZATION_2324', 'REALIZATION_2025']].sum(axis=1, skipna=True)
    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['CONTRACT_VALUE'] = pd.to_numeric(df['CONTRACT_VALUE'], errors='coerce')
    df['REALIZATION'] = pd.to_numeric(df['REALIZATION'], errors='coerce')
    df['REALIZED_PCT'] = pd.to_numeric(df['REALIZED_PCT'], errors='coerce') * 100
    df['TIME_PCT'] = pd.to_numeric(df['TIME_PCT'], errors='coerce') * 100

    total_contracts = len(df)
    completed = df[df['REALIZED_PCT'] >= 100].shape[0]
    realized = df['REALIZATION'].sum()
    active_contracts = df[df['STATUS'].str.contains('active', case=False, na=False)].shape[0]

    unique_contracts = df.drop_duplicates(subset=['CONTRACT_VALUE'], keep='first')
    total_value = unique_contracts['CONTRACT_VALUE'].sum()

    remaining = total_value - realized
    remaining_pct = (remaining / total_value) * 100 if total_value else 0
    avg_realized_pct = df['REALIZED_PCT'].mean()

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



# ========================================================================================
# 🟧 SECTION 3 — PAYMENT TERM FILE
# ========================================================================================
if payment_term_file:
    df_terms = safe_read_excel(payment_term_file, sheet_name="Sheet1")

    df_terms.columns = df_terms.columns.str.strip().str.upper()
    df_terms['STATUS'] = df_terms['STATUS'].str.upper()
    df_terms['VENDOR'] = df_terms['VENDOR'].str.strip()

    df_terms['AMOUNT'] = pd.to_numeric(df_terms['AMOUNT'], errors='coerce').fillna(0)
    df_terms['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(df_terms['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)

    df_paid = df_terms[df_terms['STATUS'] == 'PAID']
    total_paid = df_paid.groupby('VENDOR')['AMOUNT'].sum()

    unique_contracts = df_terms[['VENDOR', 'START_DATE', 'END_DATE', 'TOTAL_CONTRACT_VALUE']].drop_duplicates()
    total_contract = unique_contracts.groupby('VENDOR')['TOTAL_CONTRACT_VALUE'].sum()

    summary_df = total_contract.to_frame(name='CONTRACT_VALUE').join(
        total_paid.to_frame(name='TOTAL_PAID'), how='outer'
    )

    summary_df['CONTRACT_VALUE'] = pd.to_numeric(summary_df['CONTRACT_VALUE']).fillna(0)
    summary_df['TOTAL_PAID'] = pd.to_numeric(summary_df['TOTAL_PAID']).fillna(0)

    summary_df['REMAINING'] = summary_df['CONTRACT_VALUE'] - summary_df['TOTAL_PAID']

    summary_df['REALIZED_PCT'] = np.where(
        summary_df['CONTRACT_VALUE'] == 0,
        0,
        (summary_df['TOTAL_PAID'] / summary_df['CONTRACT_VALUE']) * 100
    ).round(1)

    summary_df_reset = summary_df.reset_index()

    total_paid_amt = summary_df['TOTAL_PAID'].sum()
    total_contract_amt = summary_df['CONTRACT_VALUE'].sum()
    total_remaining_amt = total_contract_amt - total_paid_amt
    pending_count = df_terms[df_terms['STATUS'] == 'PENDING'].shape[0]

    st.subheader("💰 Payment Progress Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_card("Total Paid", f"Rp {total_paid_amt:,.0f}", "", "#dcfce7", "💸")
    with col2:
        render_card("Remaining", f"Rp {total_remaining_amt:,.0f}", "", "#fde68a", "🕐")
    with col3:
        render_card("Vendor Count", summary_df.shape[0], "Unique vendors", "#e0f2fe", "🏢")
    with col4:
        render_card("Pending Terms", pending_count, "Termin belum dibayar", "#fef2f2", "⚠️")

    # ===== KPI BAR =====
    def build_kpi_bar(df_subset, title="Progress Pembayaran per Vendor (%)"):
        fig = go.Figure()
        for _, row in df_subset.iterrows():
            vendor = row['VENDOR']
            pct = row['REALIZED_PCT']
            rem_pct = 100 - pct
            paid = row['TOTAL_PAID']
            rem = row['REMAINING']
            total = row['CONTRACT_VALUE']

            fig.add_trace(go.Bar(
                y=[vendor], x=[pct], orientation='h',
                marker_color="#10b981" if pct >= 50 else "#f87171",
                text=f"{pct:.1f}%", textposition='inside', showlegend=False,
                hovertemplate=f"<b>{vendor}</b><br>"
                              f"Total: Rp {total:,.0f}<br>"
                              f"Paid: Rp {paid:,.0f} ({pct:.1f}%)<br>"
                              f"Remaining: Rp {rem:,.0f}"
            ))

            fig.add_trace(go.Bar(
                y=[vendor], x=[rem_pct], orientation='h',
                marker_color="#e5e7eb",
                text=f"{rem_pct:.1f}%", textposition='inside',
                showlegend=False
            ))

        fig.update_layout(
            barmode='stack',
            height=700,
            margin=dict(l=300, r=50, t=60, b=50),
            title=title,
            xaxis=dict(range=[0, 100], title="Progress (%)"),
            yaxis=dict(automargin=True),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    with st.expander("📉 Vendor Payment Progress Details", expanded=False):
        st.plotly_chart(build_kpi_bar(summary_df_reset), use_container_width=True)



# ========================================================================================
# If no files uploaded
# ========================================================================================
if not (project_file or contract_file or payment_term_file):
    st.info("Please upload at least one Excel file.")
