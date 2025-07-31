

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import hashlib
from datetime import datetime
import requests
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared import get_file
# --- Config & Auth ---
st.set_page_config(page_title="📁 Contract Summary Dashboard", layout="wide")
from auth import require_login
require_login()

contract_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/data_kontrak_new.xlsx",
    "📁 Upload Contract Data",
    "contract_file"
)

payment_term_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/Long_Format_Payment_Terms.xlsx",
    "📁 Upload Payment Data",
    "payment_terms_new"
)




# --- UI Header ---
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
    Contract Summary
</div>
""", unsafe_allow_html=True)

# --- Section Card Function ---
def section_card(title=None):
    section = st.container()
    section_id = f"section_{title.replace(' ', '_').lower() if title else 'no_title'}"
    if title:
        section.markdown(f"""
        <div id=\"{section_id}_header\" style=\"background: linear-gradient(to right, #3498db, #1abc9c); color: white; padding: 12px 15px; border-radius: 10px 10px 0 0; margin-bottom: 0; font-weight: 600; font-size: 1.2rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);\">
            {title}
        </div>
        """, unsafe_allow_html=True)
    return section



def metric_card(title, value, sub, icon="✅", theme="sky"):
    gradients = {
        "sky": "linear-gradient(135deg, #e0f7fa, #b2ebf2)",
        "mint": "linear-gradient(135deg, #e6f4ea, #b9fbc0)",
        "lavender": "linear-gradient(135deg, #e9d8fd, #d0bfff)",
        "peach": "linear-gradient(135deg, #ffe0b2, #ffcc80)",
        "rose": "linear-gradient(135deg, #fce4ec, #f8bbd0)",
        "sand": "linear-gradient(135deg, #f5f5f5, #e0e0e0)"
    }

    background = gradients.get(theme, gradients["sky"])
    text_color = "#222"
    sub_color = "#555"
    shadow_color = "rgba(0, 0, 0, 0.05)"

    return f"""
    <div style="
        padding: 1.6rem;
        background: {background};
        border-radius: 1.25rem;
        box-shadow: 0 4px 12px {shadow_color};
        text-align: center;
        margin-bottom: 1.5rem;
        height: 100%;
        width: 100%;
        transition: all 0.3s ease;
        font-family: 'Segoe UI', sans-serif;
    ">
        <div style="font-size: 2rem; margin-bottom: 0.6rem;">{icon}</div>
        <div style="font-size: 1.15rem; font-weight: 600; color: {text_color}; margin-bottom: 0.2rem;">{title}</div>
        <div style="font-size: 2.1rem; font-weight: 800; color: {text_color}; margin: 0.4rem 0;">{value}</div>
        <div style="color: {sub_color}; font-size: 0.9rem;">{sub}</div>
    </div>
    """





if contract_file:
    df = pd.read_excel(contract_file)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # Rename for consistency
    df.rename(columns={
        'Start Date': 'START',
        'End Date': 'END',
        'PROGRESS ACTUAL': 'PROGRESS'
    }, inplace=True)

    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['DURATION'] = (df['END'] - df['START']).dt.days
    df['PROGRESS'] = pd.to_numeric(df['PROGRESS'], errors='coerce')

    today = pd.Timestamp.today()
    df['TIME_GONE'] = ((today - df['START']) / (df['END'] - df['START'])).clip(0, 1) * 100

    # --- Metrics ---
    total_contracts = len(df)
    active_contracts = df[df['STATUS'] == 'ACTIVE'].shape[0]
    non_active_contracts = df[df['STATUS'].str.contains('NON ACTIVE', case=False, na=False)].shape[0]
    active_adendum_contracts = df[df['STATUS'].str.contains("ADENDUM", na=False, case=False)].shape[0]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(metric_card("Total Contracts", total_contracts, "All listed contracts", "📦"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Contracts", active_contracts, "Currently ongoing", "✅"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Non-Active Contracts", non_active_contracts, "Finished or inactive", "🔝"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Adendum Contracts", active_adendum_contracts, "Contracts with Adendum", "📝"), unsafe_allow_html=True)

    # --- Gantt Chart ---
    with section_card("Contract Timelines"):
        df_sorted = df.sort_values('START')
        df_plot = df_sorted.dropna(subset=['START', 'END'])  # Only valid ones plotted
        fig_gantt = px.timeline(
            df_plot,
            x_start='START',
            x_end='END',
            y='KONTRAK',
            color='STATUS',
            hover_data=['DURATION', 'PROGRESS', 'TIME_GONE'],
            title="Contract Gantt Timeline"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)


        import plotly.graph_objects as go

        # --- Color Logic ---
        def get_color(pct):
            return '#2ECC71' if pct >= 50 else '#E74C3C'  # Green if ≥50%, Red otherwise

        # --- Build Horizontal Bar Chart with Conditional Color and %
        def build_kpi_bar(df_subset, title):
            fig = go.Figure()
            for _, row in df_subset.iterrows():
                color = get_color(row['REALIZED_PCT'])

                # Realized
                fig.add_trace(go.Bar(
                    y=[row['KONTRAK']],
                    x=[row['REALIZATION']],
                    name='REALIZED',
                    orientation='h',
                    marker=dict(color=color),
                    text=f"{row['REALIZED_PCT']}%",
                    textposition='inside',
                    hovertemplate=(
                        f"<b>{row['KONTRAK']}</b><br>"
                        f"Total Contract: {row['CONTRACT_VALUE']:.1f} M<br>"
                        f"Realized: {row['REALIZATION']:.1f} M<br>"
                        f"Remaining: {row['REMAINING']:.1f} M<br>"
                        f"% Realized: {row['REALIZED_PCT']}%"
                    ),
                    showlegend=False
                ))

                # Remaining
                fig.add_trace(go.Bar(
                    y=[row['KONTRAK']],
                    x=[row['REMAINING']],
                    name='REMAINING',
                    orientation='h',
                    marker=dict(color='#D0D3D4'),
                    text=f"{row['REMAINING']:.1f} M",
                    textposition='inside',
                    hovertemplate=(
                        f"<b>{row['KONTRAK']}</b><br>"
                        f"Total Contract: {row['CONTRACT_VALUE']:.1f} M<br>"
                        f"Realized: {row['REALIZATION']:.1f} M<br>"
                        f"Remaining: {row['REMAINING']:.1f} M<br>"
                        f"% Realized: {row['REALIZED_PCT']}%"
                    ),
                    showlegend=False
                ))

            fig.update_layout(
                barmode='stack',
                title=title,
                xaxis=dict(
                    title="Contract Value (Millions)",
                    tickformat=".0f",
                    showgrid=True,
                    zeroline=True,
                    rangeslider=dict(visible=True)  # Enables zoom via slider
                ),
                yaxis=dict(
                    title="Project",
                    automargin=True
                ),
                height=600,
                margin=dict(l=300, r=50, t=60, b=50),
                dragmode=False  # Disable drag-to-zoom
            )
            return fig

        # --- Prepare Data ---
        df_chart = df.copy()
        df_chart.rename(columns={
            'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE',
            'Realisasi On  2023-2024': 'REALIZATION'
        }, inplace=True)

        df_chart = df_chart[df_chart['CONTRACT_VALUE'].notna() & df_chart['REALIZATION'].notna()].copy()
        df_chart['REMAINING'] = df_chart['CONTRACT_VALUE'] - df_chart['REALIZATION']
        df_chart[['REALIZATION', 'REMAINING']] = df_chart[['REALIZATION', 'REMAINING']].clip(lower=0)
        df_chart['REALIZED_PCT'] = (df_chart['REALIZATION'] / df_chart['CONTRACT_VALUE'] * 100).round(1)
        df_chart.sort_values(by='CONTRACT_VALUE', ascending=False, inplace=True)

        # Split top 5 and others
        top5 = df_chart.head(5)
        others = df_chart.iloc[5:]

        # --- Display in Streamlit ---
        with section_card("📊 Top 5 Contracts"):
            fig_top5 = build_kpi_bar(top5, "Top 5 Contracts by Value")
            st.plotly_chart(fig_top5, use_container_width=True, config={
                'scrollZoom': False,  # disable scroll-to-zoom
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'displayModeBar': 'always'
            })

        with section_card("📊 Remaining Contracts"):
            fig_others = build_kpi_bar(others, "Remaining Contracts by Value")
            st.plotly_chart(fig_others, use_container_width=True, config={
                'scrollZoom': False,  # disable scroll-to-zoom
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'displayModeBar': 'always'
            })


       

    # --- Time-Based Progress Category ---
        with section_card("📈 Project Progress Categories (Based on Time Elapsed)"):
            bins = [-1, 30, 50, 80, 100]
            labels = ['<30%', '30-50%', '50-80%', '>80%']
            df['TIME_GONE_CAT'] = pd.cut(df['TIME_GONE'], bins=bins, labels=labels)

            progress_counts = df['TIME_GONE_CAT'].value_counts().sort_index().reset_index()
            progress_counts.columns = ['Progress Range', 'Count']
            fig_progress = px.bar(progress_counts, x='Progress Range', y='Count', color='Progress Range',
                                title="Project Progress by Time Elapsed", text='Count')
            st.plotly_chart(fig_progress, use_container_width=True)

    # --- Status Pie Chart and Filter Table ---
    with section_card("📊 Contract Status Distribution and Filter"):
        col_pie, col_table = st.columns(2)

        with col_pie:
            status_counts = df['STATUS'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.4)
            st.plotly_chart(fig_status, use_container_width=True)

        with col_table:
            status_filter = st.selectbox("Select Status", options=["All"] + df['STATUS'].unique().tolist())
            if status_filter == "All":
                filtered_df = df
            else:
                filtered_df = df[df['STATUS'] == status_filter]

            st.dataframe(filtered_df[['KONTRAK', 'START', 'END', 'DURATION', 'STATUS', 'PROGRESS', 'TIME_GONE']].sort_values('END'), use_container_width=True)

   
   

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pandas.tseries.offsets import MonthBegin

if payment_term_file:

    import pandas as pd
    import plotly.graph_objects as go

    # --- Load & process data ---
    df = pd.read_excel(payment_term_file)
    df.columns = df.columns.str.strip().str.upper()
    df['VENDOR'] = df['VENDOR'].str.strip()
    df['STATUS'] = df['STATUS'].str.upper()

    # 🔥 CLEANING: Remove commas and convert to numeric
    df['AMOUNT'] = df['AMOUNT'].astype(str).str.replace(',', '', regex=False)
    df['TOTAL_CONTRACT_VALUE'] = df['TOTAL_CONTRACT_VALUE'].astype(str).str.replace(',', '', regex=False)
    df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
    df['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(df['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)

    # --- Summarize per vendor ---
    contract_base = df[['VENDOR', 'START_DATE', 'END_DATE', 'TOTAL_CONTRACT_VALUE']].drop_duplicates()
    contract_value_per_vendor = contract_base.groupby('VENDOR')['TOTAL_CONTRACT_VALUE'].sum()

    paid_df = df[df['STATUS'] == 'PAID']
    total_paid_per_vendor = paid_df.groupby('VENDOR')['AMOUNT'].sum()

    summary_df = pd.DataFrame({
        'CONTRACT_VALUE': contract_value_per_vendor,
        'TOTAL_PAID': total_paid_per_vendor
    }).fillna(0)

    summary_df['REMAINING'] = summary_df['CONTRACT_VALUE'] - summary_df['TOTAL_PAID']

    # ⛔️ Avoid division by zero using np.where
    import numpy as np
    summary_df['REALIZED_PCT'] = np.where(
        summary_df['CONTRACT_VALUE'] == 0,
        0,
        (summary_df['TOTAL_PAID'] / summary_df['CONTRACT_VALUE']) * 100
    )
    summary_df['REALIZED_PCT'] = summary_df['REALIZED_PCT'].round(1)

    summary_df = summary_df.reset_index()
    
    # --- Build chart ---
    def get_color(pct):
        return '#2ECC71' if pct >= 50 else '#E74C3C'
    
    def build_kpi_bar(df_subset, title="Progress Pembayaran (%)"):
        fig = go.Figure()
        for _, row in df_subset.iterrows():
            vendor = row['VENDOR']
            pct = row['REALIZED_PCT']
            rem_pct = 100 - pct
            paid = row['TOTAL_PAID']
            rem = row['REMAINING']
            total = row['CONTRACT_VALUE']
    
            fig.add_trace(go.Bar(
                y=[vendor], x=[pct], name='REALIZED',
                orientation='h', marker_color=get_color(pct),
                text=f"{pct:.1f}%", textposition='inside',
                hovertemplate=(
                    f"<b>{vendor}</b><br>Total Kontrak: Rp {total:,.0f}<br>"
                    f"Terbayar: Rp {paid:,.0f} ({pct:.1f}%)<br>"
                    f"Sisa: Rp {rem:,.0f} ({rem_pct:.1f}%)<extra></extra>"
                ), showlegend=False
            ))
    
            fig.add_trace(go.Bar(
                y=[vendor], x=[rem_pct], name='REMAINING',
                orientation='h', marker_color="#D0D3D4",
                text=f"{rem_pct:.1f}%", textposition='inside',
                hovertemplate=(
                    f"<b>{vendor}</b><br>Total Kontrak: Rp {total:,.0f}<br>"
                    f"Terbayar: Rp {paid:,.0f} ({pct:.1f}%)<br>"
                    f"Sisa: Rp {rem:,.0f} ({rem_pct:.1f}%)<extra></extra>"
                ), showlegend=False
            ))
    
        fig.update_layout(
            barmode='stack',
            title=title,
            xaxis=dict(title="Progress (%)", range=[0, 100]),
            yaxis=dict(title="", automargin=True),
            height=700,
            margin=dict(l=300, r=50, t=60, b=50),
            dragmode=False
        )
        return fig
    
    # --- Display in Streamlit ---
    with section_card("📊 Vendor Financial Progress"):
        fig_vendor = build_kpi_bar(summary_df)
        st.plotly_chart(fig_vendor, use_container_width=True, config={
            'scrollZoom': False,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
            'displayModeBar': 'always'
        })

    # --- Load dan format dasar ---
    df_terms = pd.read_excel(payment_term_file)
    df_terms.columns = df_terms.columns.str.strip().str.upper()
    df_terms['START_DATE'] = pd.to_datetime(df_terms['START_DATE'], errors='coerce')
    df_terms['END_DATE'] = pd.to_datetime(df_terms['END_DATE'], errors='coerce')

    # --- Filter Paid Terms ---
    df_paid = df_terms[df_terms['STATUS'].str.upper() == 'PAID'].copy()

    # --- Bagi 2: ada contract status & tidak ---
    with_status = df_terms[df_terms['CONTRACT_STATUS'].notna()].copy()
    without_status = df_terms[df_terms['CONTRACT_STATUS'].isna()].copy()

    # === 1) Yang ADA CONTRACT_STATUS ===
    paid_with_status = df_paid[df_paid['CONTRACT_STATUS'].notna()]
    total_paid_status = paid_with_status.groupby(['VENDOR', 'CONTRACT_STATUS'])['AMOUNT'].sum().reset_index()
    contract_status = with_status[['VENDOR', 'CONTRACT_STATUS', 'TOTAL_CONTRACT_VALUE', 'START_DATE']].drop_duplicates()
    summary_status = contract_status.merge(total_paid_status, on=['VENDOR', 'CONTRACT_STATUS'], how='left')
    summary_status['TOTAL_PAID'] = pd.to_numeric(summary_status['AMOUNT'], errors='coerce').fillna(0)
    summary_status['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(summary_status['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)
    summary_status.drop(columns='AMOUNT', inplace=True)
    
    summary_status['PCT_PROGRESS'] = np.where(
        summary_status['TOTAL_CONTRACT_VALUE'] == 0,
        0,
        (summary_status['TOTAL_PAID'] / summary_status['TOTAL_CONTRACT_VALUE']) * 100
    )
    summary_status['PCT_LABEL'] = summary_status['PCT_PROGRESS'].round(1).astype(str) + '%'


    # === 2) Yang TIDAK ADA CONTRACT_STATUS ===
    paid_without_status = df_paid[df_paid['CONTRACT_STATUS'].isna()]
    total_paid_vendor = paid_without_status.groupby('VENDOR')['AMOUNT'].sum().reset_index()
    contract_vendor = without_status[['VENDOR', 'TOTAL_CONTRACT_VALUE', 'START_DATE']].drop_duplicates()
    summary_vendor = contract_vendor.merge(total_paid_vendor, on='VENDOR', how='left')
    summary_vendor['TOTAL_PAID'] = pd.to_numeric(summary_vendor['AMOUNT'], errors='coerce').fillna(0)
    summary_vendor['TOTAL_CONTRACT_VALUE'] = pd.to_numeric(summary_vendor['TOTAL_CONTRACT_VALUE'], errors='coerce').fillna(0)
    summary_vendor['CONTRACT_STATUS'] = None
    summary_vendor.drop(columns='AMOUNT', inplace=True)

    summary_vendor['PCT_PROGRESS'] = np.where(
        summary_vendor['TOTAL_CONTRACT_VALUE'] == 0,
        0,
        (summary_vendor['TOTAL_PAID'] / summary_vendor['TOTAL_CONTRACT_VALUE']) * 100
    )
    summary_vendor['PCT_LABEL'] = summary_vendor['PCT_PROGRESS'].round(1).astype(str) + '%'

    # === Gabungkan semua summary ===
    vendor_summary = pd.concat([summary_status, summary_vendor], ignore_index=True)

    # --- Merge ke data utama ---
    df_terms = pd.merge(df_terms, vendor_summary[['VENDOR', 'CONTRACT_STATUS', 'PCT_PROGRESS', 'PCT_LABEL']],
                        on=['VENDOR', 'CONTRACT_STATUS'], how='left')

    # --- Label untuk sumbu Y (display project name + status + progress) ---
    def generate_display_name(row):
        if pd.notna(row['CONTRACT_STATUS']):
            return f"{row['VENDOR']} ({row['CONTRACT_STATUS']}) - {row['PCT_LABEL']}"
        else:
            return f"{row['VENDOR']} - {row['PCT_LABEL']}"

    df_terms['VENDOR_DISPLAY'] = df_terms.apply(generate_display_name, axis=1)

    # --- Hitung tanggal pembayaran ---
    df_terms['PAYMENT_DATE'] = df_terms.apply(
        lambda row: row['START_DATE'] + pd.DateOffset(months=int(row['TERM_NO']) - 1), axis=1
    )
    df_terms['PAYMENT_DATE'] = df_terms['PAYMENT_DATE'].dt.to_period('M').dt.to_timestamp()
    df_terms['END_DATE'] = df_terms['PAYMENT_DATE'] + pd.offsets.MonthEnd(0)

    # --- Assign warna status ---
    def assign_color(status):
        return '#3498db' if str(status).lower() == 'paid' else '#f1c40f'

    df_terms['COLOR'] = df_terms['STATUS'].apply(assign_color)

    # --- Rename untuk plot ---
    df_plot = df_terms.rename(columns={
        'VENDOR_DISPLAY': 'Project',
        'PAYMENT_DATE': 'Start',
        'END_DATE': 'End'
    })

    # --- Buat chart ---
    fig = px.timeline(
        df_plot,
        x_start="Start",
        x_end="End",
        y="Project",
        color="COLOR",
        color_discrete_map="identity",
        hover_data=["TERM_NO", "AMOUNT", "STATUS", "PCT_LABEL"]
    )

    # --- Garis hari ini ---
    today = datetime.today()
    fig.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=0,
        y1=1,
        xref='x',
        yref='paper',
        line=dict(color="red", width=2, dash="dash")
    )
    fig.add_annotation(
        x=today,
        y=1.02,
        xref="x",
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="red")
    )

    # --- Setup Tick Bulanan ---
    min_date = df_plot['Start'].min()
    max_date = df_plot['End'].max()
    tickvals = pd.date_range(min_date, max_date + MonthBegin(1), freq='MS')

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title="📆 Vendor Payment Progress Timeline",
        xaxis=dict(
            tickvals=tickvals,
            tickformat="%b<br>%Y",
            tickangle=0,
            tickfont=dict(size=8),
            showgrid=True,
            gridcolor="#eeeeee",
            gridwidth=1,
            type="date"
        ),
        yaxis=dict(automargin=True),
        showlegend=False,
        height=800,
        width=4000,
        autosize=False,
        margin=dict(l=250, r=50, t=70, b=80),
    )

    st.plotly_chart(fig, use_container_width=False)

        # --- Section: Filter Tanggal Transaksi dan Tabel Lengkap ---
    with section_card("📋 Tabel Transaksi Lengkap (Filter Tanggal Transaksi)"):
        st.subheader("📅 Filter Tanggal Transaksi")
    
        # Pastikan kolomnya ada dulu
        if 'TANGGAL_TRANSAKSI' in df_terms.columns:
            # Konversi aman
            df_terms['TANGGAL_TRANSAKSI'] = pd.to_datetime(df_terms['TANGGAL_TRANSAKSI'], errors='coerce')
    
            # Hapus baris yang null
            df_valid = df_terms[df_terms['TANGGAL_TRANSAKSI'].notna()].copy()
    
            # Kalau ternyata kosong semua, kasih warning
            if df_valid.empty:
                st.warning("Tidak ada data dengan tanggal transaksi yang valid.")
            else:
                # Ambil min & max date
                min_date = df_valid['TANGGAL_TRANSAKSI'].min().date()
                max_date = df_valid['TANGGAL_TRANSAKSI'].max().date()
    
                # Input tanggal
                start_date, end_date = st.date_input(
                    "Pilih rentang tanggal transaksi:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
                # Filter berdasarkan input
                filtered_df = df_valid[
                    (df_valid['TANGGAL_TRANSAKSI'] >= pd.to_datetime(start_date)) &
                    (df_valid['TANGGAL_TRANSAKSI'] <= pd.to_datetime(end_date))
                ]
    
                # Pilih kolom tertentu saja
                filtered_display = filtered_df.loc[:, ['VENDOR', 'AMOUNT', 'STATUS', 'TANGGAL_TRANSAKSI']]
    
                # Tampilkan tabel
                st.dataframe(filtered_display, use_container_width=True)
    
        else:
            st.warning("Kolom 'TANGGAL_TRANSAKSI' tidak ditemukan di data.")



    # --- Tabel Warning Termin Jatuh Tempo Bulan Ini ---
    today = datetime.today()
    current_month = today.month
    current_year = today.year
    
    # --- Format data: rupiah & tanggal ---
    def format_rupiah(x):
        return f"Rp {x:,.0f}"
    
    def format_date(x):
        return x.strftime('%d %b %Y') if pd.notna(x) else '-'
    
    # --- TABEL 1: Warning Termin Pending yang Jatuh Tempo Bulan Ini ---
    st.subheader("⚠️ Termin Pending yang Jatuh Tempo Bulan Ini")
    
    warning_due = df_plot[
        (df_plot['End'].dt.month == current_month) &
        (df_plot['End'].dt.year == current_year) &
        (df_plot['STATUS'].str.upper() == 'PENDING')
    ].copy()
    
    if not warning_due.empty:
        # Bersihin dan konversi AMOUNT
        warning_due['AMOUNT'] = warning_due['AMOUNT'].astype(str).str.replace(',', '', regex=False)
        warning_due['AMOUNT'] = pd.to_numeric(warning_due['AMOUNT'], errors='coerce').fillna(0)
    
        # Format tanggal dan rupiah
        warning_due['End'] = warning_due['End'].apply(format_date)
        warning_due['AMOUNT'] = warning_due['AMOUNT'].apply(format_rupiah)
    
        st.dataframe(
            warning_due[['VENDOR', 'TERM_NO', 'AMOUNT', 'End', 'STATUS']]
            .sort_values(by='End'),
            use_container_width=True
        )
    else:
        st.success("Tidak ada termin pending yang jatuh tempo bulan ini.")
    
    st.markdown("---")
    
    # --- TABEL 2: Late Payment (Pending Tapi Sudah Lewat Jatuh Tempo) ---
    st.subheader("❌ Termin Pending yang Lewat Jatuh Tempo")
    
    late_payment = df_plot[
        (df_plot['End'] < today) &
        (df_plot['STATUS'].str.upper() == 'PENDING')
    ].copy()
    
    if not late_payment.empty:
        # Bersihin dan konversi AMOUNT
        late_payment['AMOUNT'] = late_payment['AMOUNT'].astype(str).str.replace(',', '', regex=False)
        late_payment['AMOUNT'] = pd.to_numeric(late_payment['AMOUNT'], errors='coerce').fillna(0)
    
        # Format tanggal dan rupiah
        late_payment['End'] = late_payment['End'].apply(format_date)
        late_payment['AMOUNT'] = late_payment['AMOUNT'].apply(format_rupiah)
    
        st.dataframe(
            late_payment[['VENDOR', 'TERM_NO', 'AMOUNT', 'End', 'STATUS']]
            .sort_values(by='End'),
            use_container_width=True
        )
    else:
        st.success("Tidak ada termin pending yang lewat jatuh tempo.")
    
    
    




else:
    st.info("Upload an Excel file containing the contract data.")
 
