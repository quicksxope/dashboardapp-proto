
# --- Full cleaned and corrected 02_Contract_Summary.py file ---
# Note: Due to length, this is a simplified header with the fixed KPI bar chart and payment_term_file block only.
# You can paste this directly into your dashboard_modular/pages/02_Contract_Summary.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import get_file

from auth import require_login
st.set_page_config(page_title="📁 Contract Summary Dashboard", layout="wide")
require_login()

contract_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/data_kontrak_new.xlsx",
    "📁 Upload Contract Data",
    "contract_file"
)

financial_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/financial_progress.xlsx",
    "📁 Upload Financial Data",
    "financial_file"
)

payment_term_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/payment_terms_new.xlsx",
    "📁 Upload Payment Data",
    "payment_terms_new"
)

if financial_file:
    df_financial = pd.read_excel(financial_file)

    def get_color(pct):
        return '#2ECC71' if pct >= 50 else '#E74C3C'

    def build_kpi_bar(df_subset, title="Progress Pembayaran (%)"):
        fig = go.Figure()
        for _, row in df_subset.iterrows():
            kontrak_name = row['Vendor']
            pct = row['REALIZED_PCT']
            remaining_pct = 100 - pct
            realized_value = row['REALIZATION']
            remaining_value = row['REMAINING']
            contract_value = row['CONTRACT_VALUE']

            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[pct],
                name='REALIZED (%)',
                orientation='h',
                marker_color=get_color(pct),
                text=f"{pct:.1f}%",
                textposition='inside',
                hovertemplate=(
                    f"<b>{kontrak_name}</b><br>"
                    f"Total Kontrak: Rp {contract_value:,.0f}<br>"
                    f"Terbayarkan: Rp {realized_value:,.0f}<br>"
                    f"Sisa: Rp {remaining_value:,.0f}"
                ),
                showlegend=False
            ))
            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[remaining_pct],
                name='REMAINING (%)',
                orientation='h',
                marker_color="#D0D3D4",
                text=f"{remaining_pct:.1f}%",
                textposition='inside',
                showlegend=False
            ))

        fig.update_layout(
            barmode='stack',
            title=title,
            xaxis=dict(title="Progress (%)", range=[0, 100]),
            yaxis=dict(title="", automargin=True),
            height=700,
            margin=dict(l=300, r=50, t=60, b=50),
        )
        return fig

    st.subheader("📊 Financial Progress Chart")
    fig_fin = build_kpi_bar(df_financial, "Progress Pembayaran Seluruh Kontrak")
    st.plotly_chart(fig_fin, use_container_width=True)

if payment_term_file:
    df_terms = pd.read_excel(payment_term_file)
    df_terms.columns = df_terms.columns.str.strip().str.upper()

    df_terms['START_DATE'] = pd.to_datetime(df_terms['START_DATE'], errors='coerce')

    df_paid = df_terms[df_terms['STATUS'].str.upper() == 'PAID']
    total_paid = df_paid.groupby('VENDOR')['AMOUNT'].sum().reset_index()
    total_paid.columns = ['VENDOR', 'TOTAL_PAID']

    vendor_contract = df_terms[['VENDOR', 'TOTAL_CONTRACT_VALUE', 'START_DATE']].drop_duplicates()
    vendor_summary = pd.merge(vendor_contract, total_paid, on='VENDOR', how='left')
    vendor_summary['TOTAL_PAID'] = vendor_summary['TOTAL_PAID'].fillna(0)
    vendor_summary['PCT_PROGRESS'] = (vendor_summary['TOTAL_PAID'] / vendor_summary['TOTAL_CONTRACT_VALUE']) * 100
    vendor_summary['PCT_LABEL'] = vendor_summary['PCT_PROGRESS'].round(1).astype(str) + '%'
    vendor_summary['VENDOR_DISPLAY'] = vendor_summary['VENDOR'] + ' (' + vendor_summary['PCT_LABEL'] + ')'

    df_plot = pd.merge(df_terms, vendor_summary[['VENDOR', 'PCT_PROGRESS', 'PCT_LABEL', 'VENDOR_DISPLAY']], on='VENDOR', how='left')
    df_plot['PAYMENT_DATE'] = df_plot.apply(lambda row: row['START_DATE'] + pd.DateOffset(months=int(row['TERM_NO']) - 1), axis=1)
    df_plot['END_DATE'] = df_plot['PAYMENT_DATE'] + pd.DateOffset(days=25)

    def assign_color(status):
        return '#3498db' if str(status).lower() == 'paid' else '#f1c40f'
    df_plot['COLOR'] = df_plot['STATUS'].apply(assign_color)

    df_plot_ready = df_plot.rename(columns={
        'VENDOR_DISPLAY': 'Project',
        'PAYMENT_DATE': 'Start',
        'END_DATE': 'End'
    })

    fig = px.timeline(
        df_plot_ready,
        x_start="Start",
        x_end="End",
        y="Project",
        color="COLOR",
        color_discrete_map="identity",
        hover_data=["TERM_NO", "AMOUNT", "STATUS", "PCT_PROGRESS"]
    )

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

    fig.update_yaxes(autorange="reversed", showgrid=True, gridcolor='rgba(200,200,200,0.3)')
    fig.update_layout(
        title="📆 Vendor Payment Progress Timeline",
        xaxis=dict(tickformat="%b %Y", dtick="M1", rangeslider_visible=True),
        showlegend=False,
        height=750,
        margin=dict(l=130, r=30, t=60, b=40),
    )

    start_x = df_plot_ready['Start'].min()
    end_x = df_plot_ready['End'].max()
    monthly_ticks = pd.date_range(start=start_x, end=end_x, freq='MS')

    for tick in monthly_ticks:
        fig.add_vline(x=tick, line=dict(color='lightgray', width=1), layer='below')

    st.plotly_chart(fig, use_container_width=True)
