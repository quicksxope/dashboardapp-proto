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

financial_file = get_file(
    "quicksxope/dashboardapp-proto/contents/data/financial_progress.xlsx",
    "📁 Upload Contract Data",
    "financial_file"
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

# --- Section Card ---
def section_card(title=None):
    section = st.container()
    if title:
        section.markdown(f"""
        <div style=\"background: linear-gradient(to right, #3498db, #1abc9c); color: white; padding: 12px 15px; border-radius: 10px 10px 0 0; font-weight: 600; font-size: 1.2rem;\">
            {title}
        </div>
        """, unsafe_allow_html=True)
    return section

# --- Metric Card ---
def metric_card(title, value, sub, icon="✅", bg="#6C5CE7"):
    gradient = f"linear-gradient(135deg, {bg}, #00CEC9)"
    return f"""
    <div class=\"metric-card\" style=\"padding:1.2rem; background:{gradient}; border-radius:1.5rem; box-shadow:0 4px 12px rgba(0, 0, 0, 0.2); text-align:center; height:100%;\">
        <div style=\"font-size:1.8rem;\">{icon}</div>
        <div style=\"font-size:1.1rem; font-weight:600; color:white;\">{title}</div>
        <div style=\"font-size:2rem; font-weight:700; color:white;\">{value}</div>
        <div style=\"color:#DADDE1; font-size:0.85rem;\">{sub}</div>
    </div>
    """

# --- Chart Utils ---
def get_color(pct): return '#2ECC71' if pct >= 50 else '#E74C3C'

def build_kpi_bar(df_subset, title):
    fig = go.Figure()

    show_legend_green = True
    show_legend_red = True
    show_legend_remaining = True

    for _, row in df_subset.iterrows():
        color = get_color(row['REALIZED_PCT'])
        kontrak_name = row['KONTRAK']
        realized = row['REALIZATION']
        remaining = row['REMAINING']
        total = row['CONTRACT_VALUE']
        pct = row['REALIZED_PCT']

        # --- Realized Bar ---
        if pct >= 50:
            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[realized],
                name="REALIZED ≥ 50%" if show_legend_green else None,
                orientation='h',
                marker=dict(color="#2ECC71"),
                text=f"{pct:.1f}%",
                textposition='inside',
                showlegend=show_legend_green,
                hovertemplate=(
                    f"<b>{kontrak_name}</b><br>"
                    f"Total Contract: {total:.1f} M<br>"
                    f"Realized: {realized:.1f} M<br>"
                    f"Remaining: {remaining:.1f} M<br>"
                    f"% Realized: {pct:.1f}%<extra></extra>"
                )
            ))
            show_legend_green = False
        else:
            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[realized],
                name="REALIZED < 50%" if show_legend_red else None,
                orientation='h',
                marker=dict(color="#E74C3C"),
                text=f"{pct:.1f}%",
                textposition='inside',
                showlegend=show_legend_red,
                hovertemplate=(
                    f"<b>{kontrak_name}</b><br>"
                    f"Total Contract: {total:.1f} M<br>"
                    f"Realized: {realized:.1f} M<br>"
                    f"Remaining: {remaining:.1f} M<br>"
                    f"% Realized: {pct:.1f}%<extra></extra>"
                )
            ))
            show_legend_red = False

        # --- Remaining Bar ---
        fig.add_trace(go.Bar(
            y=[kontrak_name],
            x=[remaining],
            name="REMAINING" if show_legend_remaining else None,
            orientation='h',
            marker=dict(color="#D0D3D4"),
            text=f"{remaining:.1f} M",
            textposition='inside',
            showlegend=show_legend_remaining,
            hovertemplate=(
                f"<b>{kontrak_name}</b><br>"
                f"Total Contract: {total:.1f} M<br>"
                f"Realized: {realized:.1f} M<br>"
                f"Remaining: {remaining:.1f} M<br>"
                f"% Realized: {pct:.1f}%<extra></extra>"
            )
        ))
        show_legend_remaining = False

    fig.update_layout(
        barmode='stack',
        title=title,
        xaxis=dict(title="Contract Value (Millions)", tickformat=".0f"),
        yaxis=dict(automargin=True),
        height=600,
        margin=dict(l=300, r=50, t=60, b=50),
        dragmode=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig


# --- Main Processing ---
if contract_file:
    df = pd.read_excel(contract_file)
    df.columns = [str(c).strip() for c in df.columns]
    df.rename(columns={'Start Date': 'START', 'End Date': 'END', 'PROGRESS ACTUAL': 'PROGRESS'}, inplace=True)
    df['START'] = pd.to_datetime(df['START'], errors='coerce')
    df['END'] = pd.to_datetime(df['END'], errors='coerce')
    df['DURATION'] = (df['END'] - df['START']).dt.days
    df['PROGRESS'] = pd.to_numeric(df['PROGRESS'], errors='coerce')
    today = pd.Timestamp.today()
    df['TIME_GONE'] = ((today - df['START']) / (df['END'] - df['START'])).clip(0, 1) * 100

    # --- Metrics Display ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(metric_card("Total Contracts", len(df), "All listed contracts", "📦"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Contracts", df[df['STATUS'] == 'ACTIVE'].shape[0], "Currently ongoing", "✅"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Non-Active Contracts", df[df['STATUS'].str.contains('NON ACTIVE', case=False, na=False)].shape[0], "Finished or inactive", "🔝"), unsafe_allow_html=True)
        st.markdown(metric_card("Active Adendum Contracts", df[df['STATUS'].str.contains('ADENDUM', case=False, na=False)].shape[0], "Contracts with Adendum", "📝"), unsafe_allow_html=True)

    # --- Gantt Chart ---
    with section_card("🗖️ Gantt Chart - Contract Timelines"):
        df_plot = df.dropna(subset=['START', 'END'])
        fig_gantt = px.timeline(df_plot.sort_values('START'), x_start='START', x_end='END', y='KONTRAK', color='STATUS',
                                hover_data=['DURATION', 'PROGRESS', 'TIME_GONE'])
        fig_gantt.update_yaxes(autorange='reversed')
        st.plotly_chart(fig_gantt, use_container_width=True)

    # --- Top 5 Chart ---
    df_chart = df.copy()
    df_chart.rename(columns={'Nilai Kontrak 2023-2024': 'CONTRACT_VALUE', 'Realisasi On  2023-2024': 'REALIZATION'}, inplace=True)
    df_chart = df_chart[df_chart['CONTRACT_VALUE'].notna() & df_chart['REALIZATION'].notna()]
    df_chart['REMAINING'] = df_chart['CONTRACT_VALUE'] - df_chart['REALIZATION']
    df_chart[['REALIZATION', 'REMAINING']] = df_chart[['REALIZATION', 'REMAINING']].clip(lower=0)
    df_chart['REALIZED_PCT'] = (df_chart['REALIZATION'] / df_chart['CONTRACT_VALUE'] * 100).round(1)
    df_chart.sort_values(by='CONTRACT_VALUE', ascending=False, inplace=True)

    top5 = df_chart.head(5)
    others = df_chart.iloc[5:]

    with section_card("📊 Top 5 Contracts (Realization % and Conditional Color)"):
        st.plotly_chart(build_kpi_bar(top5, "Top 5 Contracts by Value"), use_container_width=True)

    with section_card("📊 Remaining Contracts (Scaled View)"):
        st.plotly_chart(build_kpi_bar(others, "Remaining Contracts by Value"), use_container_width=True)



       

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


if financial_file:
    df_financial = pd.read_excel(financial_file)
    st.success("Financial progress file loaded!")

    import plotly.graph_objects as go

    def get_color(pct):
        return '#2ECC71' if pct >= 50 else '#E74C3C'

    def build_kpi_bar(df_subset, title="Progress Pembayaran (%)"):
        fig = go.Figure()

        show_legend_realized = True
        show_legend_remaining = True

        for _, row in df_subset.iterrows():
            kontrak_name = row['Vendor']
            pct = row['REALIZED_PCT']
            remaining_pct = 100 - pct
            realized_value = row['REALIZATION']
            remaining_value = row['REMAINING']
            contract_value = row['CONTRACT_VALUE']

            # Bar: Realisasi (Hijau)
            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[pct],
                name='REALIZED (%)' if show_legend_realized else None,
                orientation='h',
                marker_color=get_color(pct),
                text=f"{pct:.1f}%",
                textposition='inside',
                hovertemplate=(
                    f"<b>{kontrak_name}</b><br>"
                    f"Total Kontrak: Rp {contract_value:,.0f}<br>"
                    f"Terbayarkan: Rp {realized_value:,.0f} ({pct:.1f}%)<br>"
                    f"Sisa: Rp {remaining_value:,.0f} ({remaining_pct:.1f}%)<extra></extra>"
                ),
                showlegend=show_legend_realized
            ))
            show_legend_realized = False

            # Bar: Sisa (Abu)
            fig.add_trace(go.Bar(
                y=[kontrak_name],
                x=[remaining_pct],
                name='REMAINING (%)' if show_legend_remaining else None,
                orientation='h',
                marker_color="#D0D3D4",
                text=f"{remaining_pct:.1f}%",
                textposition='inside',
                hovertemplate=(
                    f"<b>{kontrak_name}</b><br>"
                    f"Total Kontrak: Rp {contract_value:,.0f}<br>"
                    f"Terbayarkan: Rp {realized_value:,.0f} ({pct:.1f}%)<br>"
                    f"Sisa: Rp {remaining_value:,.0f} ({remaining_pct:.1f}%)<extra></extra>"
                ),
                showlegend=show_legend_remaining
            ))
            show_legend_remaining = False

        fig.update_layout(
            barmode='stack',
            title=title,
            xaxis=dict(title="Progress (%)", range=[0, 100]),
            yaxis=dict(title="", automargin=True),
            height=700,
            margin=dict(l=300, r=50, t=60, b=50),
            dragmode=False,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    with section_card("📊 Financial Progress Chart (from Uploaded File)"):
        fig_fin = build_kpi_bar(df_financial, "Progress Pembayaran Seluruh Kontrak")
        st.plotly_chart(fig_fin, use_container_width=True, config={
            'scrollZoom': False,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
            'displayModeBar': 'always'
        })



else:
    st.info("Upload an Excel file containing the contract data.")
