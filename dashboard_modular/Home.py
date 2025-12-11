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



import tempfile, os

def robust_read_excel(file_obj, sheet_name=None):
    """Safe excel loader fixing Streamlit + BytesIO issues."""
    if file_obj is None:
        st.error("❌ File not loaded (None).")
        st.stop()

    # Read raw bytes
    try:
        if hasattr(file_obj, "getvalue"):
            raw = file_obj.getvalue()
        else:
            file_obj.seek(0)
            raw = file_obj.read()
    except Exception as e:
        st.error(f"❌ Cannot read file buffer: {e}")
        st.stop()

    if raw is None or len(raw) == 0:
        st.error("❌ File is empty (0 bytes). Reload or re-upload.")
        st.stop()

    bio = BytesIO(raw)
    bio.seek(0)

    # Try normal read
    try:
        return pd.read_excel(bio, sheet_name=sheet_name)
    except:
        pass

    # Try engine=openpyxl
    try:
        bio.seek(0)
        return pd.read_excel(bio, sheet_name=sheet_name, engine="openpyxl")
    except:
        pass

    # Fallback: write to temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        df = pd.read_excel(tmp_path, sheet_name=sheet_name)
        os.remove(tmp_path)
        return df

    except Exception as e:
        st.error(f"❌ Final Excel read failed: {e}")
        st.stop()


st.set_page_config(page_title="Dashboard Home", layout="wide")
require_login()

from shared import get_file

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



# --- Load Payment Term Data ---
payment_term_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/Long_Format_Payment_Terms.xlsx",
    "💵 Upload Payment Term File",
    "payment_term_file"
)




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
    excel = pd.ExcelFile(project_file)
    print(excel.sheet_names)  # Debug: cek nama-nama sheet

    # --- Baca sheet utama ---
    dfp = pd.robust_read_excel(excel, sheet_name="BASE DATA (wajib update)")
    dfp.columns = dfp.columns.str.strip().str.upper()

    # --- Validasi kolom penting ---
    required_cols = ['KONTRAK', 'STATUS', '% COMPLETE', 'START', 'PLAN END']
    missing_cols = [col for col in required_cols if col not in dfp.columns]

    if missing_cols:
        st.error(f"Kolom berikut tidak ditemukan di file Excel: {', '.join(missing_cols)}")
    else:
        # --- Normalisasi data ---
        dfp['KONTRAK'] = dfp['KONTRAK'].astype(str).str.upper().str.strip()
        dfp['STATUS'] = dfp['STATUS'].astype(str).str.upper().str.strip()

        # pastikan % COMPLETE dalam 0–100
        dfp['% COMPLETE'] = pd.to_numeric(dfp['% COMPLETE'], errors='coerce').fillna(0)
        dfp['% COMPLETE'] = dfp['% COMPLETE'].apply(lambda x: x * 100 if x <= 1 else x)

        dfp['START'] = pd.to_datetime(dfp['START'], errors='coerce')
        dfp['PLAN END'] = pd.to_datetime(dfp['PLAN END'], errors='coerce')

        today = pd.Timestamp.today()

        # --- Hitung metrik utama ---
        total_projects = dfp['KONTRAK'].nunique()
        total_tasks = len(dfp)
        avg_completion = dfp['% COMPLETE'].mean()

        # Task selesai tepat waktu
        on_time = dfp[
            (dfp['STATUS'] == 'SELESAI') &
            (dfp['PLAN END'] >= today)
        ].shape[0]

        # Task overdue: sudah lewat PLAN END + belum selesai 100%
        overdue = dfp[
            (dfp['PLAN END'] < today) &
            (dfp['% COMPLETE'] < 100)
        ].shape[0]

        completed_tasks = dfp[dfp['STATUS'] == 'SELESAI'].shape[0]
        overdue_rate = (overdue / total_tasks) * 100 if total_tasks else 0

        # --- Tampilkan hasil ---
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
            render_card("On-Time Tasks", on_time, "Completed on-time", "#bae6fd", "⏱️")
        with col5:
            render_card("Completed Tasks", completed_tasks, f"of {total_tasks} total", "#d1fae5", "✅")

        col1, col2 = st.columns(2)
        with col1:
            render_progress_card("Avg Completion %", avg_completion, "#60a5fa", "🛠️")
        with col2:
            render_progress_card("Overdue Rate", overdue_rate, "#f87171", "⏰")

            

if contract_file:
    df = pd.robust_read_excel(contract_file)
    df.columns = df.columns.str.strip()

    # --- Rename kolom ---
    df.rename(columns={
        'Start Date': 'START',
        'End Date': 'END',
        'PROGRESS ACTUAL': 'PROGRESS',
        'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE',   # kontrak hanya 2023-2024
        'Realisasi On  2023-2024': 'REALIZATION_2324',
        'Realisasi On  2025': 'REALIZATION_2025',
        '% Realisasi': 'REALIZED_PCT',
        'TIME GONE %': 'TIME_PCT',
        'STATUS': 'STATUS'
    }, inplace=True)
    

    
    # --- Realisasi total (2023-2024 + 2025) ---
    df['REALIZATION'] = df[['REALIZATION_2324', 'REALIZATION_2025']].sum(axis=1, skipna=True)
    
    # --- Konversi tipe data ---
    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['CONTRACT_VALUE'] = pd.to_numeric(df['CONTRACT_VALUE'], errors='coerce')
    df['REALIZATION'] = pd.to_numeric(df['REALIZATION'], errors='coerce')
    df['REALIZED_PCT'] = pd.to_numeric(df['REALIZED_PCT'], errors='coerce') * 100
    df['TIME_PCT'] = pd.to_numeric(df['TIME_PCT'], errors='coerce') * 100
    
    # --- Summary metrics ---
    
    avg_realized_pct = df['REALIZED_PCT'].mean()
    completed = df[df['REALIZED_PCT'] >= 100].shape[0]
    realized = df['REALIZATION'].sum()
    total_contracts = len(df)
    active_contracts = df[df['STATUS'].str.contains('active', case=False, na=False) &
                          ~df['STATUS'].str.contains('adendum', case=False, na=False)].shape[0]
    
    
    # 👉 Logic: kalau CONTRACT_VALUE duplikat, hanya dihitung sekali
    unique_contracts = df.drop_duplicates(subset=['CONTRACT_VALUE'], keep='first')
    total_value = unique_contracts['CONTRACT_VALUE'].sum()
    
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




if payment_term_file:
    df_terms = pd.roubust_read_excel(payment_term_file, sheet_name="Sheet1")
    df_terms.columns = df_terms.columns.str.strip().str.upper()
    df_terms['STATUS'] = df_terms['STATUS'].str.upper()
    df_terms['VENDOR'] = df_terms['VENDOR'].str.strip()

    # Pastikan numeric (kalau ada koma/titik ribuan, pandas udah otomatis baca float)
    df_terms['AMOUNT'] = pd.to_numeric(df_terms['AMOUNT'], errors='coerce').fillna(0)
    df_terms['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(df_terms['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)

    df_terms['AMOUNT'] = pd.to_numeric(df_terms['AMOUNT'], errors='coerce').fillna(0)
    df_terms['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(df_terms['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)

    # Total paid per vendor (hanya yang sudah PAID)
    df_paid = df_terms[df_terms['STATUS'] == 'PAID']
    total_paid = df_paid.groupby('VENDOR')['AMOUNT'].sum()

    # Total contract per vendor (ambil yang unik saja)
    unique_contracts = df_terms[['VENDOR', 'START_DATE', 'END_DATE', 'TOTAL_CONTRACT_VALUE']].drop_duplicates()
    total_contract = unique_contracts.groupby('VENDOR')['TOTAL_CONTRACT_VALUE'].sum()

    # Gabungkan keduanya
    summary_df = total_contract.to_frame(name='CONTRACT_VALUE').join(
        total_paid.to_frame(name='TOTAL_PAID'),
        how='outer'
    )

    # Konversi ke numerik dan isi NaN jadi 0
    summary_df['CONTRACT_VALUE'] = pd.to_numeric(summary_df['CONTRACT_VALUE'], errors='coerce').fillna(0)
    summary_df['TOTAL_PAID'] = pd.to_numeric(summary_df['TOTAL_PAID'], errors='coerce').fillna(0)

    # Kalkulasi remaining
    summary_df['REMAINING'] = summary_df['CONTRACT_VALUE'] - summary_df['TOTAL_PAID']

    # Kalkulasi % realisasi (hindari divide by 0)
    summary_df['REALIZED_PCT'] = np.where(
        summary_df['CONTRACT_VALUE'] == 0,
        0,
        (summary_df['TOTAL_PAID'] / summary_df['CONTRACT_VALUE']) * 100
    )
    summary_df['REALIZED_PCT'] = summary_df['REALIZED_PCT'].round(1)

    # Reset index supaya VENDOR jadi kolom
    summary_df_reset = summary_df.reset_index()

    # Summary total
    total_paid_amt = summary_df['TOTAL_PAID'].sum()
    total_contract_amt = summary_df['CONTRACT_VALUE'].sum()
    total_remaining_amt = total_contract_amt - total_paid_amt
    pending_count = df_terms[df_terms['STATUS'] == 'PENDING'].shape[0]

    # Card & donut
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

    render_card_with_donut(
        title="Payment Realization",
        value=f"Rp {total_paid_amt:,.0f}",
        subtext="Based on paid vs contract value",
        labels=["Paid", "Remaining"],
        values=[total_paid_amt, total_remaining_amt],
        colors=["#10b981", "#fcd34d"],
        icon="💰",
        total_value=total_contract_amt,
        remaining=total_remaining_amt
    )

    # KPI bar chart
    def build_kpi_bar(df_subset, title="Progress Pembayaran per Vendor (%)"):
        fig = go.Figure()
        for _, row in df_subset.iterrows():
            vendor = row['VENDOR']
            pct = row['REALIZED_PCT']
            remaining_pct = 100 - pct
            paid = row['TOTAL_PAID']
            remaining = row['REMAINING']
            total = row['CONTRACT_VALUE']

            fig.add_trace(go.Bar(
                y=[vendor], x=[pct], orientation='h',
                marker_color="#10b981" if pct >= 50 else "#f87171",
                text=f"{pct:.1f}%", textposition='inside', showlegend=False,
                hovertemplate=f"<b>{vendor}</b><br>Total: Rp {total:,.0f}<br>Paid: Rp {paid:,.0f} ({pct:.1f}%)<br>Remaining: Rp {remaining:,.0f} ({remaining_pct:.1f}%)<extra></extra>"
            ))

            fig.add_trace(go.Bar(
                y=[vendor], x=[remaining_pct], orientation='h',
                marker_color="#e5e7eb", text=f"{remaining_pct:.1f}%",
                textposition='inside', showlegend=False,
                hovertemplate=f"<b>{vendor}</b><br>Total: Rp {total:,.0f}<br>Paid: Rp {paid:,.0f} ({pct:.1f}%)<br>Remaining: Rp {remaining:,.0f} ({remaining_pct:.1f}%)<extra></extra>"
            ))

        fig.update_layout(
            barmode='stack', height=700,
            margin=dict(l=300, r=50, t=60, b=50),
            title=title,
            xaxis=dict(title="Progress (%)", range=[0, 100]),
            yaxis=dict(title="", automargin=True),
            plot_bgcolor='white', paper_bgcolor='white'
        )
        return fig

    with st.expander("📉 Vendor Payment Progress Details", expanded=False):
        st.plotly_chart(build_kpi_bar(summary_df_reset), use_container_width=True)



else:
    st.info("Please upload both Project and Contract Excel files.")
