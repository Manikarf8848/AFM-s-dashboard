import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import io
import report_builder
import history_db

st.set_page_config(page_title="LCY3 AFM Dashboard", layout="wide", page_icon="📊")

# ── Configuration & State ───────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "saved_active_hashes" not in st.session_state:
    st.session_state.saved_active_hashes = []

DM = st.session_state.dark_mode

# ── Dynamic UI Theming ──────────────────────────────────────────────────────
_bg      = "#0f1117" if DM else "#f8f9fa"
_bg2     = "#1a1d27" if DM else "#ffffff"
_bg3     = "#22263a" if DM else "#e9ecef"
_card    = "#1e2235" if DM else "#ffffff"
_text    = "#e8eaf6" if DM else "#1e1e1e"
_sub     = "#8892b0" if DM else "#6c757d"
_accent  = "#7986cb" if DM else "#3949ab"
_border  = "#3949ab"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
* {{ font-family: 'Inter', sans-serif !important; }}
.stApp {{ background: {_bg} !important; }}
[data-testid="stSidebar"] {{ background: {_bg2} !important; border-right: 1px solid {"#2a2d3e" if DM else "#dee2e6"} !important; }}

.dash-header {{
    background: {"linear-gradient(135deg, #0d1333 0%, #1a237e 100%)" if DM else "linear-gradient(135deg, #1a237e 0%, #3949ab 100%)"};
    padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 2rem;
    color: white !important; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}}

.kpi-box {{
    background: {_card}; border-radius: 16px; padding: 1.5rem;
    text-align: center; border-top: 4px solid {_border};
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: transform 0.2s ease;
}}
.kpi-box:hover {{ transform: translateY(-3px); }}
.kpi-label {{ font-size: 0.8rem; color: {_sub}; font-weight: 700; text-transform: uppercase; }}
.kpi-value {{ font-size: 2.2rem; font-weight: 900; color: {_text}; margin: 0.3rem 0; }}

.sec-title {{
    font-size: 1.2rem; font-weight: 800; color: {_text};
    padding-bottom: 0.5rem; border-bottom: 2px solid {_accent};
    margin: 1.5rem 0 1rem 0;
}}

.stButton > button {{
    background: {_accent} !important; color: white !important;
    border-radius: 8px !important; border: none !important;
    font-weight: 600 !important; padding: 0.5rem 1.5rem !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Logic Components ────────────────────────────────────────────────────────
def get_threshold(andon_type):
    thresholds = {"Amnesty": 10, "Drive Lacking Capability": 10}
    return thresholds.get(andon_type, 5)

def within_threshold(row):
    t = get_threshold(row["Andon Type"])
    return row["Resolve_Min"] <= t

def build_group_pivot(df, group_col):
    """
    Architectural Pattern: Pivot & Inject
    1. Group by Date/Type to get time-series matrices.
    2. Iterate through categories to build multi-index columns.
    3. Inject a 'Total' summary row at the bottom.
    """
    cats = sorted(df[group_col].dropna().unique())
    df = df.copy()
    df["Date"] = df["Time Created"].dt.date
    df["DateLabel"] = df["Time Created"].dt.strftime("%b %d, %Y")
    
    # Base metrics
    date_count = df.groupby(["Date", "DateLabel", group_col])["Resolve_Min"].count().reset_index()
    date_avg   = df.groupby(["Date", "DateLabel", group_col])["Resolve_Min"].mean().reset_index()
    
    date_labels = df[["Date", "DateLabel"]].drop_duplicates().set_index("Date")["DateLabel"].to_dict()
    
    cols_dict = {}
    for cat in cats:
        c_count = date_count[date_count[group_col] == cat].set_index("Date")["Resolve_Min"]
        c_avg   = date_avg[date_avg[group_col] == cat].set_index("Date")["Resolve_Min"].round(2)
        cols_dict[(cat, "Andons")] = c_count
        cols_dict[(cat, "Avg Time")] = c_avg

    cols_dict[("Total", "Andons")] = df.groupby("Date")["Resolve_Min"].count()
    cols_dict[("Total", "Avg Time")] = df.groupby("Date")["Resolve_Min"].mean().round(2)

    tbl = pd.DataFrame(cols_dict).sort_index(ascending=False)
    tbl.index = [date_labels.get(d, str(d)) for d in tbl.index]
    tbl.columns = pd.MultiIndex.from_tuples(tbl.columns)

    # --- FIX: Safe Dictionary Construction ---
    grand = {}
    for cat in cats:
        subset = df[df[group_col] == cat]
        grand[(cat, "Andons")] = int(len(subset))
        grand[(cat, "Avg Time")] = round(subset["Resolve_Min"].mean(), 2) if not subset.empty else 0
    
    grand[("Total", "Andons")] = int(len(df))
    grand[("Total", "Avg Time")] = round(df["Resolve_Min"].mean(), 2) if not df.empty else 0
    
    grand_row = pd.DataFrame([grand], index=["Total"])
    grand_row.columns = pd.MultiIndex.from_tuples(grand_row.columns)
    
    return pd.concat([tbl, grand_row])

# ── App Layout ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="dash-header">
    <h1 style="margin:0; font-size:2.2rem; font-weight:900;">📊 LCY3 AFM Dashboard</h1>
    <p style="margin:5px 0 0 0; opacity:0.8; font-weight:500;">Floor Performance & Root Cause Analysis</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("Settings")
    if st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode):
        st.session_state.dark_mode = True
    else:
        st.session_state.dark_mode = False
    
    st.divider()
    st.subheader("Data Input")
    files = st.file_uploader("Upload CSV/JSON", accept_multiple_files=True)

# ── Data Processing ─────────────────────────────────────────────────────────
if files:
    parts = []
    for f in files:
        df_part = pd.read_json(f) if f.name.endswith(".json") else pd.read_csv(f)
        parts.append(df_part)
    
    df = pd.concat(parts, ignore_index=True)
    
    # Pre-processing Pipeline
    # [Data Ingestion] -> [Cleaning] -> [Enrichment]
    df["Time Created"] = pd.to_datetime(df["Time Created"], errors='coerce')
    df["Resolve_Min"] = pd.to_timedelta(df["Dwell Time (hh:mm:ss)"], errors='coerce').dt.total_seconds() / 60
    df = df.dropna(subset=["Time Created", "Resolve_Min"])
    
    # Filters
    st.markdown('<div class="sec-title">Active Filters</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_types = st.multiselect("Andon Types", options=df["Andon Type"].unique())
    with c2:
        sel_res = st.multiselect("Resolvers", options=df["Resolver"].unique())
    with c3:
        dt_range = st.date_input("Date Range", [df["Time Created"].min().date(), df["Time Created"].max().date()])

    fdf = df.copy()
    if sel_types: fdf = fdf[fdf["Andon Type"].isin(sel_types)]
    if sel_res: fdf = fdf[fdf["Resolver"].isin(sel_res)]
    if len(dt_range) == 2:
        fdf = fdf[(fdf["Time Created"].dt.date >= dt_range[0]) & (fdf["Time Created"].dt.date <= dt_range[1])]

    # ── KPI Row ─────────────────────────────────────────────────────────────
    if not fdf.empty:
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kpi-box"><div class="kpi-label">Total Andons</div><div class="kpi-value">{len(fdf):,}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-box"><div class="kpi-label">Avg Resolve</div><div class="kpi-value">{fdf["Resolve_Min"].mean():.1f}m</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-box"><div class="kpi-label">Within Target</div><div class="kpi-value">{fdf.apply(within_threshold, axis=1).mean()*100:.1f}%</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi-box"><div class="kpi-label">Peak Hour</div><div class="kpi-value">{fdf["Time Created"].dt.hour.mode()[0]}:00</div></div>', unsafe_allow_html=True)

        # ── Analysis Tabs ───────────────────────────────────────────────────
        t1, t2, t3 = st.tabs(["📈 Trends", "🏆 Leaderboard", "📋 Detailed Pivot"])
        
        with t1:
            fig = px.histogram(fdf, x="Time Created", color="Andon Type", nbins=50, title="Andon Frequency Over Time")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=_text)
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            lb = fdf.groupby("Resolver")["Resolve_Min"].agg(["count", "mean"]).reset_index()
            lb.columns = ["Resolver", "Count", "Avg Time"]
            st.dataframe(lb.sort_values("Count", ascending=False), use_container_width=True, hide_index=True)

        with t3:
            pivot_tbl = build_group_pivot(fdf, "Andon Type")
            st.dataframe(pivot_tbl, use_container_width=True)
    else:
        st.warning("No data found for the current filters.")
else:
    st.info("Please upload data files to begin analysis.")
