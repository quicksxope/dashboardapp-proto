import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from auth import require_login
from io import BytesIO
import hashlib
from datetime import datetime
import numpy as np
import tempfile, os

# ---------------------------------------------------------
# Excel Loader — robust + fallback + safe
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Cached Excel Loader
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def load_excel_cached(file_obj, sheet_name=None):
    if file_obj is None:
        return None

    # Hash the bytes for stable caching
    if hasattr(file_obj, "getvalue"):
        raw = file_obj.getvalue()
    else:
        file_obj.seek(0)
        raw = file_obj.read()

    key_hash = hashlib.md5(raw).hexdigest()

    return robust_read_excel(BytesIO(raw), sheet_name=sheet_name)



# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard Home", layout="wide")
require_login()

from shared import get_file


# ---------------------------------------------------------
# Load files (from GitHub or Upload)
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# DEBUG info
# ---------------------------------------------------------
with st.sidebar.expander("DEBUG Files"):
    for name, f in [
        ("project_file", project_file),
        ("contract_file", contract_file),
        ("payment_term_file", payment_term_file)
    ]:
        st.write(f"**{name}** type:", type(f))
        if hasattr(f, "getvalue"):
            st.write("bytes:", len(f.getvalue()))



# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------
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



# ---------------------------------------------------------
# UI COMPONENTS (cards)
# ---------------------------------------------------------
def render_card(title, value, subtext="", color="#fef9c3", icon="📦"):
    st.markdown(f'''
        <div style="
            background-color:{color};
            padding:1.4rem 1.6rem;
            border-radius:16px;
            box-shadow:0 1px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        ">
            <div style="font-size:0.9rem; color:#4b5563;">{icon} {title}</div>
            <div style="font-size:2rem; font-weight:700;">{value}</div>
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
            color: white;
        ">
            <div style="font-weight:600; font-size:1.05rem;">{icon} {title}</div>
            <div style="background-color: #374151; height: 10px; border-radius: 9999px; margin: 0.4rem 0;">
                <div style="width: {percent:.2f}%; background-color: {color}; height: 100%;"></div>
            </div>
            <div style="font-size: 0.85rem;">Progress: {percent:.2f}%</div>
        </div>
    """, unsafe_allow_html=True)



def render_card_with_donut(title, value, subtext, labels, values, colors, icon="🥯", total_value=None, remaining=None):
    total_fmt = f"Rp {total_value:,.0f} M" if total_value is not None else "-"
    remaining_fmt = f"Rp {remaining:,.0f} M" if remaining is not None else "-"

    col1, col2 = st.columns([1.2, 1])
    percent = (values[0] / sum(values) * 100) if sum(values) else 0

    with col1:
        st.markdown(f"""
            <div style="
                background-color: #eef2ff;
                padding: 1.6rem;
                border-radius: 16px;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 0.9rem;">{icon} {title}</div>
                <div style="font-size: 2rem; font-weight: 700;">{value}</div>
                <div style="font-size: 0.9rem; color: #9ca3af;">{subtext}</div>
                <hr />
                <p><strong>Total Contract Value:</strong><br>{total_fmt}</p>
                <p><strong>Remaining Value:</strong><br>{remaining_fmt}</p>
                <p style="color: {'#10b981' if percent > 80 else '#f59e0b'};">
                    {percent:.1f}% realized
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        fig = go.Figure(go.Pie(
            hole=0.85,
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            textinfo='none',
        ))
        fig.update_layout(
            annotations=[dict(text=f"{percent:.1f}%", font_size=20, showarrow=False)],
            showlegend=False,
            height=260
        )
        st.plotly_chart(fig, use_container_width=True)



# ---------------------------------------------------------
# PROJECT FILE SECTION
# ---------------------------------------------------------
if project_file:
    dfp = load_excel_cached(project_file, sheet_name="BASE DATA (wajib update)")

    if dfp is not None:
        dfp.columns = dfp.columns.str.strip().str.upper()

        required = ['KONTRAK', 'STATUS', '% COMPLETE', 'START', 'PLAN END']
        miss = [c for c in required if c not in dfp.columns]
        if miss:
            st.error(f"Missing columns: {miss}")
        else:
            dfp['% COMPLETE'] = pd.to_numeric(dfp['% COMPLETE'], errors='coerce').fillna(0)
            dfp['% COMPLETE'] = dfp['% COMPLETE'].apply(lambda x: x*100 if x <= 1 else x)
            dfp['PLAN END'] = pd.to_datetime(dfp['PLAN END'], errors='coerce')
            dfp['START'] = pd.to_datetime(dfp['START'], errors='coerce')

            today = pd.Timestamp.today()
            total_projects = dfp['KONTRAK'].nunique()
            total_tasks = len(dfp)
            avg_completion = dfp['% COMPLETE'].mean()

            overdue = dfp[(dfp['PLAN END'] < today) & (dfp['% COMPLETE'] < 100)].shape[0]
            completed_tasks = dfp[dfp['STATUS'].str.upper() == 'SELESAI'].shape[0]
            on_time = dfp[(dfp['STATUS'].str.upper()=='SELESAI') & (dfp['PLAN END']>=today)].shape[0]

            st.subheader("🏗️ Project Monitoring Summary")

            col1, col2, col3 = st.columns(3)
            col1.write(render_card("Total Projects", total_projects, "Unique KONTRAK"))
            col2.write(render_card("Total Tasks", total_tasks))
            col3.write(render_card("Overdue Tasks", overdue))

            col4, col5 = st.columns(2)
            col4.write(render_card("On-Time Tasks", on_time))
            col5.write(render_card("Completed Tasks", completed_tasks))

            col6, col7 = st.columns(2)
            col6.write(render_progress_card("Avg Completion %", avg_completion))
            col7.write(render_progress_card("Overdue Rate", (overdue/total_tasks*100) if total_tasks else 0))



# ---------------------------------------------------------
# CONTRACT SUMMARY SECTION
# ---------------------------------------------------------
if contract_file:
    df = load_excel_cached(contract_file)

    if df is not None:
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

        df['REALIZATION'] = df[['REALIZATION_2324','REALIZATION_2025']].sum(axis=1, skipna=True)

        df['CONTRACT_VALUE'] = pd.to_numeric(df['CONTRACT_VALUE'], errors='coerce')
        df['REALIZATION'] = pd.to_numeric(df['REALIZATION'], errors='coerce')
        df['REALIZED_PCT'] = pd.to_numeric(df['REALIZED_PCT'], errors='coerce') * 100

        realized = df['REALIZATION'].sum()
        unique_contracts = df.drop_duplicates(subset=['CONTRACT_VALUE'])
        total_value = unique_contracts['CONTRACT_VALUE'].sum()
        remaining = total_value - realized
        remaining_pct = remaining / total_value * 100 if total_value else 0

        st.subheader("📁 Contract Performance Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.write(render_card("Total Contracts", len(df)))
        c2.write(render_card("Completed (100%)", df[df['REALIZED_PCT']>=100].shape[0]))
        c3.write(render_card("Avg Realization %", f"{df['REALIZED_PCT'].mean():.1f}%"))
        c4.write(render_card("Active Contracts", df[df['STATUS'].str.contains("active",case=False,na=False)].shape[0]))

        p1, p2 = st.columns(2)
        p1.write(render_progress_card("Remaining Value %", remaining_pct))
        p2.write(render_progress_card("Avg Realization %", df['REALIZED_PCT'].mean()))

        render_card_with_donut(
            title="Realization",
            value=f"Rp {realized:,.0f} M",
            subtext="Total realized vs contract value",
            labels=["Realized","Remaining"],
            values=[realized,remaining],
            colors=["#10b981","#e5e7eb"],
            total_value=total_value,
            remaining=remaining
        )



# ---------------------------------------------------------
# PAYMENT TERMS SECTION
# ---------------------------------------------------------
if payment_term_file:
    df_terms = load_excel_cached(payment_term_file, sheet_name="Sheet1")

    if df_terms is not None:
        df_terms.columns = df_terms.columns.str.upper().str.strip()

        df_terms['AMOUNT'] = pd.to_numeric(df_terms['AMOUNT'], errors='coerce').fillna(0)
        df_terms['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(df_terms['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)
        df_terms['STATUS'] = df_terms['STATUS'].str.upper()

        df_paid = df_terms[df_terms['STATUS']=="PAID"]
        total_paid = df_paid.groupby("VENDOR")['AMOUNT'].sum()

        unique_contracts = df_terms[['VENDOR','START_DATE','END_DATE','TOTAL_CONTRACT_VALUE']].drop_duplicates()
        total_contract = unique_contracts.groupby("VENDOR")['TOTAL_CONTRACT_VALUE'].sum()

        summary_df = total_contract.to_frame("CONTRACT_VALUE").join(total_paid.to_frame("TOTAL_PAID"), how="outer").fillna(0)
        summary_df['REMAINING'] = summary_df['CONTRACT_VALUE'] - summary_df['TOTAL_PAID']
        summary_df['REALIZED_PCT'] = (summary_df['TOTAL_PAID'] / summary_df['CONTRACT_VALUE']) * 100
        summary_df['REALIZED_PCT'] = summary_df['REALIZED_PCT'].fillna(0).round(1)

        st.subheader("💰 Payment Progress Summary")

        total_paid_amt = summary_df['TOTAL_PAID'].sum()
        total_contract_amt = summary_df['CONTRACT_VALUE'].sum()
        remaining_amt = total_contract_amt - total_paid_amt
        pending_terms = df_terms[df_terms['STATUS']=="PENDING"].shape[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.write(render_card("Total Paid", f"Rp {total_paid_amt:,.0f}"))
        c2.write(render_card("Remaining", f"Rp {remaining_amt:,.0f}"))
        c3.write(render_card("Vendor Count", summary_df.shape[0]))
        c4.write(render_card("Pending Terms", pending_terms))

        render_card_with_donut(
            title="Payment Realization",
            value=f"Rp {total_paid_amt:,.0f}",
            subtext="Paid vs Contract value",
            labels=["Paid","Remaining"],
            values=[total_paid_amt,remaining_amt],
            colors=["#22c55e","#e5e7eb"],
            total_value=total_contract_amt,
            remaining=remaining_amt
        )
