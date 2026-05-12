import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import io
import report_builder
import history_db

st.set_page_config(page_title="LCY3 AFM Dashboard", layout="wide", page_icon="📊")

# ── Initial Session State ───────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "saved_active_hashes" not in st.session_state:
    st.session_state.saved_active_hashes = []
if "duplicate_warnings" not in st.session_state:
    st.session_state.duplicate_warnings = []

DM = st.session_state.dark_mode

# ── Color Palette & CSS Variables ───────────────────────────────────────────
_bg      = "#0f1117" if DM else "#f8f9fa"
_bg2     = "#1a1d27" if DM else "#ffffff"
_bg3     = "#22263a" if DM else "#e9ecef"
_card    = "#1e2235" if DM else "#ffffff"
_text    = "#e8eaf6" if DM else "#1e1e1e"
_sub     = "#8892b0" if DM else "#6c757d"
_border  = "#3949ab"
_accent  = "#7986cb" if DM else "#3949ab"

_css_sidebar_border   = "#2a2d3e" if DM else "#dee2e6"
_css_header_bg        = "linear-gradient(135deg, #0d1333 0%, #1a237e 45%, #3949ab 100%)" if DM else "linear-gradient(135deg, #1a237e 0%, #283593 50%, #3949ab 100%)"
_css_header_shadow    = "0 4px 32px rgba(57,73,171,0.6), 0 0 0 1px rgba(121,134,203,0.15)" if DM else "0 4px 24px rgba(57,73,171,0.4), 0 0 0 1px rgba(57,73,171,0.2)"
_css_kpi_shadow       = "0 4px 20px rgba(0,0,0,0.3), 0 0 0 1px rgba(57,73,171,0.12)" if DM else "0 2px 12px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.05)"
_css_kpi_hover_shadow = "0 12px 36px rgba(57,73,171,0.4), 0 0 0 1px rgba(121,134,203,0.25)" if DM else "0 8px 24px rgba(57,73,171,0.15), 0 0 0 1px rgba(57,73,171,0.1)"
_css_profile_shadow   = "0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(57,73,171,0.15)" if DM else "0 2px 16px rgba(0,0,0,0.06)"
_css_profile_hover    = "0 8px 32px rgba(57,73,171,0.5), 0 0 0 1px rgba(121,134,203,0.2)" if DM else "0 6px 24px rgba(57,73,171,0.15)"
_css_tabs_hover_bg    = "rgba(57,73,171,0.1)" if DM else "rgba(57,73,171,0.05)"
_css_tabs_active_bg   = "rgba(57,73,171,0.15)" if DM else "rgba(57,73,171,0.08)"
_css_input_border     = "#3949ab" if DM else "#ced4da"
_css_rc_bg1           = "#1e2235" if DM else "#fff3e0"
_css_rc_bg2           = "#22263a" if DM else "#fff8e1"
_css_rc_shadow        = "0 4px 16px rgba(0,0,0,0.3)" if DM else "0 2px 12px rgba(245,158,11,0.1)"
_css_top_bg           = "linear-gradient(135deg, #1e2235, #252847)" if DM else "linear-gradient(135deg, #ffffff, #fdfbf7)"
_css_top_border       = "2px solid rgba(245,158,11,0.4)" if DM else "2px solid rgba(245,158,11,0.3)"
_css_top_shadow       = "0 4px 24px rgba(245,158,11,0.15), 0 0 0 1px rgba(245,158,11,0.1)" if DM else "0 4px 16px rgba(245,158,11,0.1)"
_css_top_hover        = "0 8px 32px rgba(245,158,11,0.25)" if DM else "0 8px 24px rgba(245,158,11,0.15)"
_css_chart_shadow     = "0 4px 20px rgba(0,0,0,0.3), 0 0 0 1px rgba(57,73,171,0.1)" if DM else "0 2px 12px rgba(0,0,0,0.04)"
_css_chart_hover      = "0 8px 32px rgba(57,73,171,0.3), 0 0 0 1px rgba(121,134,203,0.2)" if DM else "0 6px 20px rgba(57,73,171,0.12)"
_css_btn_bg           = "linear-gradient(135deg, #1a237e, #3949ab)" if DM else "linear-gradient(135deg, #3949ab, #5c6bc0)"
_css_uploader_bg      = "rgba(30,34,53,0.7)" if DM else "rgba(255,255,255,0.8)"
_css_uploader_border  = "2px dashed rgba(57,73,171,0.4)" if DM else "2px dashed rgba(57,73,171,0.3)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, .stApp, .block-container, [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', sans-serif !important;
}}

.stApp {{ background: {_bg} !important; }}
.block-container {{ padding-top: 1rem; background: {_bg} !important; padding-bottom: 2rem; }}
[data-testid="stSidebar"] {{ background: {_bg2} !important; border-right: 1px solid {_css_sidebar_border} !important; }}
[data-testid="stSidebar"] * {{ color: {_text} !important; }}

::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: {_bg2}; border-radius: 4px; }}
::-webkit-scrollbar-thumb {{ background: {_accent}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: #5c6bc0; }}

.dash-header {{
    background: {_css_header_bg};
    padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;
    color: white !important; display: flex; align-items: center; gap: 1.5rem;
    box-shadow: {_css_header_shadow};
    animation: slideDown 0.5s cubic-bezier(0.22,1,0.36,1);
    position: relative; overflow: hidden;
}}
.dash-header::before {{
    content: ''; position: absolute; top: -50%; right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(121,134,203,0.15) 0%, transparent 70%);
    pointer-events: none;
}}
@keyframes slideDown {{
    from {{ transform: translateY(-20px); opacity: 0; }}
    to   {{ transform: translateY(0);     opacity: 1; }}
}}
.dash-header h1 {{ margin: 0; font-size: 2rem; font-weight: 900; letter-spacing: -0.03em; color: #ffffff !important; text-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
.dash-header p  {{ margin: 0.4rem 0 0 0; opacity: 0.9; font-size: 0.9rem; color: #e8eaf6 !important; font-weight: 500; }}
.dash-header strong {{ color: #ffffff !important; }}

.kpi-box {{
    background: {_card}; border-radius: 16px; padding: 1.25rem;
    box-shadow: {_css_kpi_shadow};
    text-align: center; border-top: 4px solid {_border};
    transition: transform 0.25s cubic-bezier(0.22,1,0.36,1), box-shadow 0.25s cubic-bezier(0.22,1,0.36,1);
    animation: fadeUp 0.45s cubic-bezier(0.22,1,0.36,1) both;
    cursor: default; height: 100%;
}}
.kpi-box:hover {{
    transform: translateY(-4px);
    box-shadow: {_css_kpi_hover_shadow};
}}
@keyframes fadeUp {{
    from {{ transform: translateY(16px); opacity: 0; }}
    to   {{ transform: translateY(0);    opacity: 1; }}
}}
.kpi-label {{ font-size: 0.75rem; color: {_sub}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }}
.kpi-value {{ font-size: 2.2rem; font-weight: 900; color: {_text}; line-height: 1.2; letter-spacing: -0.02em; margin: 0.2rem 0; }}
.kpi-sub   {{ font-size: 0.75rem; color: {_sub}; margin-top: 0.25rem; font-weight: 500; }}

.sec-title {{
    font-size: 1.1rem; font-weight: 700; color: {_text};
    padding: 0.5rem 0; border-bottom: 2px solid {_accent};
    margin-bottom: 1rem; margin-top: 0.5rem; letter-spacing: -0.01em;
}}

.profile-card {{
    background: {_card}; border-radius: 16px; padding: 1.5rem;
    border-left: 6px solid {_accent};
    box-shadow: {_css_profile_shadow};
    animation: fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
    transition: box-shadow 0.25s ease;
}}
.profile-card:hover {{ box-shadow: {_css_profile_hover}; }}
.profile-name {{ font-size: 1.6rem; font-weight: 800; color: {_text}; margin-bottom: 0.2rem; }}
.profile-sub  {{ font-size: 0.9rem; color: {_sub}; font-weight: 500; }}

.badge {{
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; margin: 4px 4px 0 0;
    transition: transform 0.15s ease;
}}
.badge:hover {{ transform: scale(1.05); }}
.badge-gold   {{ background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }}
.badge-red    {{ background: rgba(239,83,80,0.15);  color: #ef5350; border: 1px solid rgba(239,83,80,0.4); }}
.badge-green  {{ background: rgba(76,175,80,0.15);  color: #4caf50; border: 1px solid rgba(76,175,80,0.4); }}
.badge-blue   {{ background: rgba(121,134,203,0.15); color: {_accent}; border: 1px solid rgba(121,134,203,0.4); }}

div[data-testid="stTabs"] button {{
    font-weight: 600; font-size: 0.9rem; padding-bottom: 0.5rem;
    color: {_sub} !important;
    transition: color 0.2s ease, background 0.2s ease;
    border-radius: 8px 8px 0 0;
}}
div[data-testid="stTabs"] button:hover {{ color: {_accent} !important; background: {_css_tabs_hover_bg} !important; }}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {_accent} !important; border-bottom-color: {_accent} !important; background: {_css_tabs_active_bg} !important;
}}

[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; border: 1px solid rgba(121,134,203,0.2); }}

[data-testid="stTextInput"] input, [data-testid="stSelectbox"] select {{
    background: {_bg2} !important; color: {_text} !important;
    border-color: {_css_input_border} !important; border-radius: 8px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}
[data-testid="stTextInput"] input:focus {{ border-color: {_accent} !important; box-shadow: 0 0 0 3px rgba(57,73,171,0.2) !important; }}

p, .stMarkdown, [data-testid="stMarkdownContainer"] * {{ color: {_text}; }}

.rc-banner {{
    background: linear-gradient(135deg, {_css_rc_bg1} 0%, {_css_rc_bg2} 100%);
    border-left: 6px solid #f59e0b; border-radius: 12px;
    padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
    animation: fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow: {_css_rc_shadow};
}}
.rc-issue {{ font-size: 1.15rem; font-weight: 800; color: #f59e0b; }}
.rc-sub   {{ font-size: 0.9rem; color: {_sub}; margin-top: 6px; font-weight: 500; }}

.top-performer-card {{
    background: {_css_top_bg}; border: {_css_top_border};
    border-radius: 16px; padding: 1.4rem 1.5rem; margin-bottom: 1rem;
    box-shadow: {_css_top_shadow};
    animation: fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease; height: 100%;
}}
.top-performer-card:hover {{ transform: translateY(-4px); box-shadow: {_css_top_hover}; }}

.chart-card {{
    background: {_card}; border-radius: 16px; padding: 1rem; margin-bottom: 1rem;
    box-shadow: {_css_chart_shadow};
    transition: box-shadow 0.25s ease, transform 0.25s ease;
    animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both;
}}
.chart-card:hover {{ transform: translateY(-3px); box-shadow: {_css_chart_hover}; }}

.stButton > button {{
    background: {_css_btn_bg} !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: opacity 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(57,73,171,0.3) !important;
}}
.stButton > button:hover {{
    opacity: 0.95 !important; transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(57,73,171,0.45) !important;
}}

[data-testid="stFileUploader"] {{
    background: {_css_uploader_bg} !important; border-radius: 12px !important;
    border: {_css_uploader_border} !important; transition: border-color 0.2s ease, background 0.2s ease !important;
}}
[data-testid="stFileUploader"]:hover {{ border-color: {_accent} !important; background: {_card} !important; }}
</style>
""", unsafe_allow_html=True)

# ── Department Station Mappings ─────────────────────────────────────────────
DEPT_STATIONS = {
    "ARSAW": [
        "2319","2320","2327","2328","2335","2336","2341","2342","2348","2349",
        "2356","2357","2362","2363","2368","2369","2376","2377","2382","2383",
        "3317","3318","3325","3326","3333","3334","3339","3340","3346","3347",
        "3355","3356","3361","3362","3367","3368","3376","3377","3382","3383",
        "4320","4321","4328","4329","4335","4336","4341","4342","4348","4349",
        "4356","4357","4363","4364","4369","4370","4377","4378","4385","4386",
    ],
    "PTR": [
        "2118","2119","2125","2126","2134","2135","2141","2142","2147","2148",
        "2152","2153","2159","2160","2165","2166","3118","3119","3125","3126",
        "3134","3135","3141","3142","3147","3148","3153","3154","3159","3160",
        "3166","3167","4118","4119","4125","4126","4137","4138","4144","4145",
        "4150","4151","4155","4156","4162","4163","4169","4170",
    ],
    "ARStow": [
        "2223","2227","2229","2232","2235","2238","2241","2243","2247","2251",
        "2254","2257","2259","2263","2265","2269","3232","3235","3236","3239",
        "3241","3244","3246","3249","3253","3254","3256","3258","3260","3263",
        "3265","3268","4229","4231","4233","4235","4238","4240","4242","4243",
        "4247","4249","4251","4254","4256","4258","4260","4263",
    ],
}
ALL_KNOWN_STATIONS = set()
for _s in DEPT_STATIONS.values():
    ALL_KNOWN_STATIONS.update(_s)

DEPT_COLORS = {
    "ARSAW":     "#7986cb",
    "PTR":       "#66bb6a",
    "ARStow":    "#ffa726",
    "Universal": "#ef5350",
}

def get_department(equipment_id):
    if pd.isna(equipment_id): return "Universal"
    eid = str(equipment_id).strip()
    for dept, stations in DEPT_STATIONS.items():
        if eid in stations: return dept
    return "Universal"

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='font-size:1.2rem;font-weight:800;color:{_text};margin-bottom:10px;'>⚙️ Settings</div>", unsafe_allow_html=True)
    dm_toggle = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dm_toggle_key")
    if dm_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dm_toggle
        st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='font-size:1rem;font-weight:700;color:{_text};margin-bottom:12px;'>💾 Saved Datasets</div>", unsafe_allow_html=True)
    
    try:
        history_records = history_db.get_history(50)
    except Exception:
        history_records = []
        
    if history_records:
        for rec in history_records:
            fhash = rec.get("file_hash", "")
            fname = rec.get("file_name", "unknown")
            display_name = fname[:24] + "…" if len(fname) > 24 else fname
            is_active = fhash in st.session_state.saved_active_hashes
            weeks_str = ", ".join([f"Wk {w}" for w in rec.get("week_numbers", [])]) or "—"
            active_badge = f"<span style='background:rgba(76,175,80,0.2);color:#4caf50;border:1px solid rgba(76,175,80,0.4);border-radius:10px;padding:2px 8px;font-size:0.65rem;font-weight:800;margin-left:6px;'>ACTIVE</span>" if is_active else ""
            
            st.markdown(f"""
            <div style="background:{_bg3}; border-radius:12px; padding:12px; margin-bottom:8px; border-left:4px solid {_accent};">
                <div style="font-weight:700;color:{_text};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;font-size:0.85rem;" title="{fname}">
                    📄 {display_name} {active_badge}
                </div>
                <div style="color:{_sub};font-size:0.75rem;">Saved: {rec.get('upload_ts','')[:16]}</div>
                <div style="color:{_accent};font-size:0.75rem;font-weight:600;">{rec.get('total_andons',0):,} andons · {weeks_str}</div>
                <div style="color:{_sub};font-size:0.75rem;">{rec.get('date_min','')} → {rec.get('date_max','')}</div>
            </div>""", unsafe_allow_html=True)
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                load_label = "Unload" if is_active else "Load"
                load_icon = "⏏" if is_active else "▶"
                if st.button(f"{load_icon} {load_label}", key=f"load_{fhash}", use_container_width=True):
                    if is_active: st.session_state.saved_active_hashes = [h for h in st.session_state.saved_active_hashes if h != fhash]
                    else:
                        if fhash not in st.session_state.saved_active_hashes: st.session_state.saved_active_hashes.append(fhash)
                    st.rerun()
            with btn_col2:
                if st.button("Remove", key=f"rm_{fhash}", use_container_width=True):
                    history_db.remove_entry(fhash)
                    st.session_state.saved_active_hashes = [h for h in st.session_state.saved_active_hashes if h != fhash]
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear All Saved Data", use_container_width=True):
            history_db.clear_history()
            st.session_state.saved_active_hashes = []
            st.rerun()
    else:
        st.markdown(f"<div style='color:{_sub};font-size:0.85rem;padding:10px;text-align:center;background:{_bg3};border-radius:8px;'>No saved datasets yet.<br>Upload a file to save it.</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div style='font-size:0.75rem;color:{_sub};text-align:center;'>LCY3 AFM Dashboard<br>Made by <b style='color:{_accent};'>Manish Karki</b></div>", unsafe_allow_html=True)

# ── Main Header ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dash-header">
    <div>
        <h1>📊 LCY3 AFM Dashboard — Floor Health</h1>
        <p>Made by <strong>Manish Karki</strong></p>
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload one or more Andon data files (CSV or JSON)", type=["json", "csv"], accept_multiple_files=True)

# ── Global Thresholds ───────────────────────────────────────────────────────
THRESHOLDS = {
    "Amnesty": 10,
    "Drive Lacking Capability": 10,
}
DEFAULT_THRESHOLD = 5
NO_THRESHOLD = ["Unreachable Charger"]
BLOCKING_EXCLUDE_TYPES = ["Product Problem", "Out of Work"]

def get_threshold(andon_type):
    if andon_type in NO_THRESHOLD: return None
    return THRESHOLDS.get(andon_type, DEFAULT_THRESHOLD)

# ── Column Canonicalization ─────────────────────────────────────────────────
CANONICAL_COLS = {
    "status": "Status", "resolver": "Resolver", "andon type": "Andon Type",
    "dwell time (hh:mm:ss)": "Dwell Time (hh:mm:ss)", "time created": "Time Created",
    "equipment type": "Equipment Type", "zone": "Zone", "shift": "Shift",
    "blocking": "Blocking", "equipment id": "Equipment ID", "id": "Equipment ID",
    "creator": "Creator", "created by": "Creator", "time resolved": "Time Resolved", "resolved at": "Time Resolved",
}

@st.cache_data
def load_data(file):
    df = pd.read_json(file) if file.name.endswith(".json") else pd.read_csv(file)
    df.columns = df.columns.str.strip()
    rename_map = {col: CANONICAL_COLS[col.lower()] for col in df.columns if col.lower() in CANONICAL_COLS}
    return df.rename(columns=rename_map)

# ── Helper Functions ────────────────────────────────────────────────────────
def dwell_color(val, series):
    if pd.isna(val): return ""
    valid = series.dropna()
    if len(valid) < 2 or valid.max() == valid.min(): return ""
    mn, mx = valid.min(), valid.max()
    norm = (val - mn) / (mx - mn)
    if norm >= 0.85: r, g, b = 229, 57, 53
    elif norm >= 0.65: r, g, b = 251, 140, 0
    elif norm >= 0.45: r, g, b = 253, 216, 53
    elif norm >= 0.2: r, g, b = 129, 199, 132
    else: r, g, b = 67, 160, 71
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fg = "white" if lum < 155 else "black"
    return f"background-color: rgb({r},{g},{b}); color: {fg}; font-weight: 600"

def build_group_pivot(df, group_col):
    cats = sorted(df[group_col].dropna().unique())
    df = df.copy()
    df["DateLabel"] = df["Time Created"].dt.strftime("%b %d, %Y")
    df["Date"] = df["Time Created"].dt.date

    date_count = df.groupby(["Date", "DateLabel", group_col])["Resolve_Min"].count().reset_index()
    date_avg   = df.groupby(["Date", "DateLabel", group_col])["Resolve_Min"].mean().reset_index()
    all_dates = df[["Date", "DateLabel"]].drop_duplicates().sort_values("Date", ascending=False)
    date_labels = all_dates.set_index("Date")["DateLabel"].to_dict()

    cols_dict = {}
    for cat in cats:
        cols_dict[(cat, "Andons")] = date_count[date_count[group_col] == cat].set_index("Date")["Resolve_Min"]
        cols_dict[(cat, "Avg Time")] = date_avg[date_avg[group_col] == cat].set_index("Date")["Resolve_Min"].round(2)

    cols_dict[("Total", "Andons")]   = df.groupby("Date")["Resolve_Min"].count()
    cols_dict[("Total", "Avg Time")] = df.groupby("Date")["Resolve_Min"].mean().round(2)

    tbl = pd.DataFrame(cols_dict).sort_index(ascending=False)
    tbl.index = [date_labels.get(d, str(d)) for d in tbl.index]
    tbl.index.name = "Rows"
    tbl.columns = pd.MultiIndex.from_tuples(tbl.columns)

    grand = {
        (cat, "Andons"): int(df[df[group_col] == cat]["Resolve_Min"].count()),
        (cat, "Avg Time"): round(df[df[group_col] == cat]["Resolve_Min"].mean(), 2) for cat in cats
    }
    grand[("Total", "Andons")] = int(df["Resolve_Min"].count())
    grand[("Total", "Avg Time")] = round(df["Resolve_Min"].mean(), 2)
    grand_row = pd.DataFrame(grand, index=["Total"])
    grand_row.columns = pd.MultiIndex.from_tuples(grand_row.columns)
    
    return pd.concat([tbl, grand_row])

def apply_pivot_style(tbl):
    avg_cols = [c for c in tbl.columns if c[1] == "Avg Time"]
    def _style(data):
        s = pd.DataFrame("", index=data.index, columns=data.columns)
        data_rows = [i for i in data.index if i != "Total"]
        for col in avg_cols:
            if col in data.columns:
                series = data.loc[data_rows, col]
                for idx in data_rows: s.loc[idx, col] = dwell_color(data.loc[idx, col], series)
        if "Total" in data.index: s.loc["Total"] = "font-weight: 700; background-color: #e8eaf6; color: #1a237e"
        return s
    return tbl.style.apply(_style, axis=None).format({c: "{:.2f}" for c in tbl.columns if c[1] == "Avg Time"}, na_rep="—").format({c: "{:,.0f}" for c in tbl.columns if c[1] == "Andons"}, na_rep="—")

def donut_chart(df, col, title):
    counts = df.groupby(col)["Resolve_Min"].count().reset_index()
    counts.columns = [col, "Count"]
    fig = px.pie(counts, names=col, values="Count", hole=0.55, color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textinfo="percent+label", pull=[0.03] * len(counts))
    fig.add_annotation(text=f"{counts['Count'].sum():,}", x=0.5, y=0.5, font_size=22, font_color=_text, showarrow=False)
    fig.update_layout(showlegend=True, title=title, height=340, legend=dict(orientation="h", yanchor="bottom", y=-0.35), margin=dict(t=40, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color=_text))
    return fig

def hbar_chart(df, col, title):
    avg = df.groupby(col)["Resolve_Min"].mean().reset_index().sort_values("Resolve_Min").rename(columns={"Resolve_Min": "Avg Time (min)"})
    fig = px.bar(avg, x="Avg Time (min)", y=col, orientation="h", text=avg["Avg Time (min)"].round(2), color="Avg Time (min)", color_continuous_scale="Blues")
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, title=title, height=340, yaxis_title="", xaxis_title="Avg Dwell Time (min)", margin=dict(t=40, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color=_text))
    return fig

def make_tab_pdf(title, fdf, within_threshold):
    # Safe guard for empty FDF
    if fdf.empty: return None 
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"LCY3 AFM Dashboard — {title}", styles["Title"]), Spacer(1, 12)]
        
        within_pct = fdf.apply(within_threshold, axis=1).mean() * 100 if len(fdf) > 0 else 0
        kpi_data = [
            ["Metric", "Value"],
            ["Total Andons", f"{len(fdf):,}"],
            ["Avg Resolve Time", f"{fdf['Resolve_Min'].mean():.2f} min"],
            ["Median Resolve Time", f"{fdf['Resolve_Min'].median():.2f} min"],
            ["% Within Threshold", f"{within_pct:.1f}%"],
        ]
        t = Table(kpi_data, colWidths=[200, 200])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#3949ab")), ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f5f5f5"), colors.white]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#c5cae9")), ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.extend([t, Spacer(1, 16)])
        
        lb = fdf.groupby("Resolver").agg(Total=("Resolve_Min","count"), Avg=("Resolve_Min","mean")).reset_index().sort_values("Avg").head(20)
        lb_data = [["Rank","Resolver","Total Andons","Avg Time (min)"]]
        for i, row in enumerate(lb.itertuples(), 1): lb_data.append([str(i), row.Resolver, str(row.Total), f"{row.Avg:.2f}"])
        lt = Table(lb_data, colWidths=[40, 220, 100, 100])
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a237e")), ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f5f5f5"), colors.white]),
            ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#c5cae9")), ("PADDING", (0,0), (-1,-1), 5),
        ]))
        story.extend([Paragraph("Leaderboard (Top 20)", styles["Heading2"]), Spacer(1, 6), lt])
        doc.build(story)
        buf.seek(0)
        return buf.getvalue()
    except ImportError: pass

    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"LCY3 AFM Dashboard — {title}", ln=True, align="C")
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        within_pct = fdf.apply(within_threshold, axis=1).mean() * 100 if len(fdf) > 0 else 0
        for label, val in [("Total Andons", f"{len(fdf):,}"), ("Avg Resolve Time", f"{fdf['Resolve_Min'].mean():.2f} min"), ("Median Resolve Time", f"{fdf['Resolve_Min'].median():.2f} min"), ("% Within Threshold", f"{within_pct:.1f}%")]:
            pdf.cell(90, 8, label, border=1); pdf.cell(90, 8, val, border=1, ln=True)
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Leaderboard (Top 20)", ln=True)
        pdf.set_font("Helvetica", size=9)
        lb = fdf.groupby("Resolver").agg(Total=("Resolve_Min","count"), Avg=("Resolve_Min","mean")).reset_index().sort_values("Avg").head(20)
        for i, row in enumerate(lb.itertuples(), 1):
            pdf.cell(10, 7, str(i), border=1); pdf.cell(90, 7, str(row.Resolver)[:40], border=1); pdf.cell(30, 7, str(row.Total), border=1); pdf.cell(30, 7, f"{row.Avg:.2f}", border=1, ln=True)
        return pdf.output(dest="S").encode("latin-1")
    except ImportError: return None

# ── File Processing ─────────────────────────────────────────────────────────
_parts_new, _dup_warnings, _new_file_names = [], [], []
required_cols = ["Status", "Resolver", "Andon Type", "Dwell Time (hh:mm:ss)", "Time Created"]

if uploaded_files:
    for uf in uploaded_files:
        raw_bytes = uf.read()
        uf.seek(0)
        
        try: file_hash = history_db.compute_hash(raw_bytes)
        except Exception: file_hash = hashlib.md5(raw_bytes).hexdigest()

        try:
            if history_db.hash_exists(file_hash):
                existing_name = history_db.get_existing_name(file_hash)
                _dup_warnings.append(f"**{uf.name}** is identical to a previously saved file (**{existing_name}**) — skipped duplicates.")
                if file_hash not in st.session_state.saved_active_hashes: st.session_state.saved_active_hashes.append(file_hash)
                continue
        except Exception: pass

        part = load_data(uf)
        missing = [c for c in required_cols if c not in part.columns]
        if missing:
            st.error(f"**{uf.name}** is missing required column(s): {', '.join(f'`{c}`' for c in missing)}")
            st.stop()
            
        part["_source_file"] = uf.name
        _parts_new.append(part)
        _new_file_names.append(uf.name)

        raw_for_preprocess = part.copy()
        raw_for_preprocess["Resolve_Min"] = pd.to_timedelta(raw_for_preprocess["Dwell Time (hh:mm:ss)"], errors="coerce").dt.total_seconds() / 60
        raw_for_preprocess["Time Created"] = pd.to_datetime(raw_for_preprocess["Time Created"], errors="coerce")
        raw_for_preprocess = raw_for_preprocess.dropna(subset=["Time Created"])
        raw_for_preprocess["Week"] = raw_for_preprocess["Time Created"].dt.isocalendar().week.astype('Int64')
        try:
            history_db.record_upload(uf.name, raw_for_preprocess, file_hash)
            if file_hash not in st.session_state.saved_active_hashes: st.session_state.saved_active_hashes.append(file_hash)
        except Exception: pass

for w in _dup_warnings: st.warning(w, icon="⚠️")

_parts_saved = []
for fhash in st.session_state.saved_active_hashes:
    try:
        sdf = history_db.load_dataframe(fhash)
        if sdf is not None and not sdf.empty:
            rec = next((r for r in history_db.get_history() if r.get("file_hash") == fhash), {})
            sdf["_source_file"] = rec.get("file_name", fhash)
            _parts_saved.append(sdf)
    except Exception: pass

_all_parts = _parts_new + _parts_saved

if _all_parts or uploaded_files:
    _usable_parts = [p for p in _all_parts if not p.empty]
    if not _usable_parts:
        st.info("No active data. Load a saved dataset from the sidebar or upload a new file.")
        st.stop()
        
    df = pd.concat(_usable_parts, ignore_index=True)
    df = df[df["Status"] == "Resolved"].copy()
    df = df[~df["Andon Type"].isin(BLOCKING_EXCLUDE_TYPES)]
    df["Resolver"] = df["Resolver"].fillna("System").replace("", "System")
    df["Resolve_Min"] = pd.to_timedelta(df["Dwell Time (hh:mm:ss)"], errors="coerce").dt.total_seconds() / 60
    df = df[df["Resolve_Min"].notna()]
    df["Time Created"] = pd.to_datetime(df["Time Created"], errors="coerce")
    df = df[df["Time Created"].notna()]
    df["Date"] = df["Time Created"].dt.date
    df["Hour"] = df["Time Created"].dt.hour
    df["Week"] = df["Time Created"].dt.isocalendar().week.astype('Int64')

    if df.empty:
        st.warning("⚠️ The uploaded datasets contain no valid, resolved andons after filtering.")
        st.stop()

    optional_cols = {
        "Equipment Type": "Equipment Type" in df.columns, "Zone": "Zone" in df.columns,
        "Shift": "Shift" in df.columns, "Blocking": "Blocking" in df.columns,
        "Equipment ID": "Equipment ID" in df.columns, "Creator": "Creator" in df.columns,
        "Time Resolved": "Time Resolved" in df.columns,
    }

    active_source_names = df["_source_file"].unique().tolist() if "_source_file" in df.columns else []
    if active_source_names:
        file_summary_rows = []
        for fname in active_source_names:
            fpart = df[df["_source_file"] == fname]
            if fpart.empty: continue
            file_summary_rows.append((fname, len(fpart), fpart["Time Created"].min(), fpart["Time Created"].max()))

        if file_summary_rows:
            card_cols = st.columns(len(file_summary_rows))
            for col_obj, (fname, cnt, dt_min, dt_max) in zip(card_cols, file_summary_rows):
                date_label = (dt_min.strftime("%d %b %Y") if dt_min.date() == dt_max.date() else f"{dt_min.strftime('%d %b')} – {dt_max.strftime('%d %b %Y')}")
                display_name = fname if len(fname) <= 28 else fname[:25] + "…"
                col_obj.markdown(f"""
                <div style="background:{_card}; border:1px solid {"rgba(57,73,171,0.2)" if DM else "#e2e8f0"};
                            border-left:5px solid {_accent}; border-radius:12px; padding:16px; margin-bottom:12px;
                            box-shadow: {_css_chart_shadow};">
                    <div style="font-size:0.8rem; color:{_accent}; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{fname}">📄 {display_name}</div>
                    <div style="font-size:1.8rem; font-weight:900; color:{_text}; line-height:1.2; margin:4px 0;">{cnt:,}</div>
                    <div style="font-size:0.75rem; color:{_sub}; font-weight:500;">andons resolved</div>
                    <div style="font-size:0.75rem; color:{_accent}; margin-top:8px; font-weight:600;">📅 {date_label}</div>
                    <div style="font-size:0.75rem; color:{_sub};">⏰ {dt_min.strftime('%H:%M')} → {dt_max.strftime('%H:%M')}</div>
                </div>""", unsafe_allow_html=True)

    # ── Filters ─────────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns([2.5, 1.2, 1.2, 1.2])
    with f1:
        min_d, max_d = df["Date"].min(), df["Date"].max()
        date_range = st.date_input("📅 Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    with f2:
        shift_opts = ["All"] + sorted(df["Shift"].dropna().unique().tolist()) if optional_cols["Shift"] else ["All"]
        sel_shift = st.selectbox("⏳ Shift", shift_opts)
    with f3:
        resolver_opts = ["All"] + sorted(df["Resolver"].unique().tolist())
        sel_resolver = st.selectbox("🧑‍💻 Resolver", resolver_opts)
    with f4:
        andon_opts = ["All"] + sorted(df["Andon Type"].dropna().unique().tolist())
        sel_andon = st.selectbox("🚨 Andon Type", andon_opts)

    with st.expander("More filters"):
        all_resolvers_list = sorted(df["Resolver"].unique().tolist())
        excluded_resolvers = st.multiselect("Hide resolvers from dashboard", options=all_resolvers_list, default=[], help="Temporarily hide logins.")
        search_resolver = st.text_input("🔎 Search resolver by login", "")

    # Apply Filters
    fdf = df.copy()
    if len(date_range) == 2: fdf = fdf[(fdf["Date"] >= date_range[0]) & (fdf["Date"] <= date_range[1])]
    if sel_shift != "All" and optional_cols["Shift"]: fdf = fdf[fdf["Shift"] == sel_shift]
    if sel_resolver != "All": fdf = fdf[fdf["Resolver"] == sel_resolver]
    if sel_andon != "All": fdf = fdf[fdf["Andon Type"] == sel_andon]
    if excluded_resolvers: fdf = fdf[~fdf["Resolver"].isin(excluded_resolvers)]
    if search_resolver.strip(): fdf = fdf[fdf["Resolver"].str.contains(search_resolver.strip(), case=False, na=False)]

    if fdf.empty:
        st.warning("⚠️ **No data matches your selected filters.** Please adjust the date range or selection to view the dashboard.", icon="⚠️")
        st.stop()

    # ── Core KPIs ───────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)

    def within_threshold(row):
        t = get_threshold(row["Andon Type"])
        if t is None: return True
        return row["Resolve_Min"] <= t

    within_pct = fdf.apply(within_threshold, axis=1).mean() * 100
    efficiency_avg = (fdf.groupby("Resolver").agg(n=("Resolve_Min","count"), avg=("Resolve_Min","mean")).apply(lambda r: r["n"]/r["avg"] if r["avg"] > 0 else 0, axis=1).mean())

    for col_obj, label, val, sub in [
        (k1, "Total Andons", f"{len(fdf):,}", "Resolved records"),
        (k2, "Avg Resolve Time", f"{fdf['Resolve_Min'].mean():.2f} min", "Per andon"),
        (k3, "Median Resolve Time", f"{fdf['Resolve_Min'].median():.2f} min", "50th percentile"),
        (k4, "% Within Threshold", f"{within_pct:.1f}%", "vs type targets"),
        (k5, "Avg Efficiency Score", f"{efficiency_avg:.1f}", "Andons ÷ Avg Time"),
    ]:
        col_obj.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs Configuration ──────────────────────────────────────────────────
    tab_names = ["📊 Overview", "🏆 Leaderboard", "👤 AFM Profile", "🔍 Root Cause", "AFM Performance", "📋 AFM General", "By Andon Type", "Weekly Breakdown"]
    if optional_cols["Equipment Type"]: tab_names.append("By Equipment Type")
    if optional_cols["Zone"]:           tab_names.append("By Zone")
    if optional_cols["Shift"]:          tab_names.append("By Shift")
    if optional_cols["Blocking"]:       tab_names.append("Blocking Analysis")
    if optional_cols["Blocking"] and optional_cols["Equipment ID"]: tab_names.append("🏭 Dept Blocking Analysis")
    if optional_cols["Equipment ID"]:   tab_names.append("Equipment ID Analysis")
    tab_names += ["Hourly Trend", "Heatmap", "Raw Data", "📤 Export", "📂 History"]

    tabs = st.tabs(tab_names)
    tab = {n: t for n, t in zip(tab_names, tabs)}

    def tab_pdf_download(tab_label, df_for_pdf):
        pdf_bytes = make_tab_pdf(tab_label, df_for_pdf, within_threshold)
        if pdf_bytes:
            st.download_button(label="⬇️ Download View as PDF", data=pdf_bytes, file_name=f"LCY3_{tab_label.replace(' ','_')}.pdf", mime="application/pdf", key=f"pdf_{tab_label}")

    # ── Tab: Overview ───────────────────────────────────────────────────────
    with tab["📊 Overview"]:
        tab_pdf_download("Overview", fdf)
        st.markdown('<div class="sec-title">Dashboard Overview — Key Insights at a Glance</div>', unsafe_allow_html=True)

        ov1, ov2 = st.columns(2)
        with ov1:
            st.markdown(f"<div style='font-size:0.9rem;font-weight:700;color:{_text};margin-bottom:0.4rem;'>📊 Andons by Resolver (Top 15)</div>", unsafe_allow_html=True)
            top_resolvers = fdf.groupby("Resolver")["Resolve_Min"].count().nlargest(15).reset_index().rename(columns={"Resolve_Min": "Andons"}).sort_values("Andons")
            max_v = top_resolvers["Andons"].max() if not top_resolvers.empty else 0
            colors_bar = ["#7986cb" if (v/max_v if max_v>0 else 0) >= 0.85 else "#5c6bc0" if (v/max_v if max_v>0 else 0) >= 0.5 else "#3949ab" for v in top_resolvers["Andons"]]
            fig_ov_bar = go.Figure(go.Bar(y=top_resolvers["Resolver"], x=top_resolvers["Andons"], orientation="h", marker_color=colors_bar, text=top_resolvers["Andons"], textposition="outside"))
            fig_ov_bar.update_layout(height=380, xaxis_title="Andon Count", yaxis_title="", margin=dict(t=10, b=20, l=0, r=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=_text))
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(fig_ov_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with ov2:
            st.markdown(f"<div style='font-size:0.9rem;font-weight:700;color:{_text};margin-bottom:0.4rem;'>🥧 Andon Types Distribution</div>", unsafe_allow_html=True)
            type_counts_ov = fdf["Andon Type"].value_counts().reset_index()
            type_counts_ov.columns = ["Andon Type", "Count"]
            if not type_counts_ov.empty:
                fig_ov_pie = px.pie(type_counts_ov.head(10), names="Andon Type", values="Count", hole=0.55, color_discrete_sequence=["#7986cb","#5c6bc0","#3949ab","#42a5f5","#26c6da","#66bb6a","#ffa726","#ef5350","#ab47bc","#26a69a"])
                fig_ov_pie.update_traces(textinfo="percent+label", pull=[0.04 if i == 0 else 0 for i in range(len(type_counts_ov.head(10)))])
                fig_ov_pie.add_annotation(text=f"<b>{int(type_counts_ov['Count'].sum()):,}</b>", x=0.5, y=0.5, font_size=20, font_color=_text, showarrow=False)
                fig_ov_pie.update_layout(height=380, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.35, font=dict(size=10)), margin=dict(t=10, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color=_text))
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.plotly_chart(fig_ov_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:0.9rem;font-weight:700;color:{_text};margin:1rem 0 0.4rem;'>📈 Daily Andon Trend</div>", unsafe_allow_html=True)
        daily_ov = fdf.groupby("Date").agg(Count=("Resolve_Min", "count"), Avg=("Resolve_Min", "mean")).reset_index().sort_values("Date")
        if not daily_ov.empty:
            fig_ov_line = go.Figure()
            fig_ov_line.add_trace(go.Scatter(x=daily_ov["Date"], y=daily_ov["Count"], mode="lines+markers", name="Daily Andons", line=dict(color="#7986cb", width=3, shape="spline"), marker=dict(size=8, color="#7986cb"), fill="tozeroy", fillcolor="rgba(121,134,203,0.15)" if DM else "rgba(57,73,171,0.08)"))
            fig_ov_line.add_trace(go.Scatter(x=daily_ov["Date"], y=daily_ov["Avg"].round(2), mode="lines+markers", name="Avg Time (min)", yaxis="y2", line=dict(color="#ffa726", width=2, dash="dot"), marker=dict(size=6, color="#ffa726")))
            fig_ov_line.add_hline(y=DEFAULT_THRESHOLD, line_dash="dash", line_color="#ef5350", annotation_text=f"Target ({DEFAULT_THRESHOLD} min)", yref="y2")
            fig_ov_line.update_layout(height=340, xaxis_title="", yaxis_title="Andon Count", yaxis2=dict(title="Avg Time (min)", overlaying="y", side="right", showgrid=False, color="#ffa726"), margin=dict(t=20, b=40, l=0, r=60), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02), font=dict(color=_text))
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(fig_ov_line, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab: Leaderboard ────────────────────────────────────────────────────
    with tab["🏆 Leaderboard"]:
        tab_pdf_download("Leaderboard", fdf)
        lb = fdf.groupby("Resolver").agg(Total_Andons=("Resolve_Min", "count"), Avg_Time=("Resolve_Min", "mean")).reset_index()
        lb["Avg_Time"] = lb["Avg_Time"].round(2)
        lb["Efficiency"] = (lb["Total_Andons"] / lb["Avg_Time"]).replace([float('inf'), -float('inf')], 0).round(2)
        lb["Within_Threshold"] = fdf.groupby("Resolver").apply(lambda g: g.apply(within_threshold, axis=1).mean() * 100).round(1).values
        lb = lb.sort_values("Avg_Time").reset_index(drop=True)
        lb.index += 1
        
        if not lb.empty:
            fastest      = lb.iloc[0]["Resolver"]
            most_active  = lb.nlargest(1, "Total_Andons").iloc[0]["Resolver"]
            most_eff     = lb.nlargest(1, "Efficiency").iloc[0]["Resolver"]

            def assign_badge(r):
                badges = []
                if r == fastest: badges.append("⚡ Fastest")
                if r == most_active: badges.append("🔥 Most Active")
                if r == most_eff: badges.append("🎯 Most Efficient")
                return "  ".join(badges)
            
            lb["Badge"] = lb["Resolver"].apply(assign_badge)
            lb["Status"] = lb["Avg_Time"].apply(lambda x: "⚠️ Average" if x > DEFAULT_THRESHOLD * 1.5 else "⚠️ Above target" if x > DEFAULT_THRESHOLD else "✅ On target")

            b1, b2, b3 = st.columns(3)
            for box, icon, title, name, color in [(b1, "⚡", "Fastest Resolver", fastest, "#f59e0b"), (b2, "🔥", "Most Active", most_active, "#ef5350"), (b3, "🎯", "Most Efficient", most_eff, "#4caf50")]:
                stats = lb[lb["Resolver"] == name].iloc[0]
                box.markdown(f"""
                <div class="top-performer-card" style="border-left: 5px solid {color};">
                    <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:{color};margin-bottom:4px;">{icon} {title}</div>
                    <div style="font-size:1.4rem;font-weight:900;color:{_text};line-height:1.2;">⭐ {name}</div>
                    <div style="font-size:0.8rem;color:{_sub};margin-top:6px;"><b style="color:{_text};">{stats['Total_Andons']:,}</b> andons · <b style="color:{color};">{stats['Avg_Time']:.2f} min</b> avg</div>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div class="sec-title">Full Rankings</div>', unsafe_allow_html=True)
            def style_lb(data):
                s = pd.DataFrame("", index=data.index, columns=data.columns)
                for idx in data.index:
                    if "Average" in str(data.loc[idx, "Status"]): s.loc[idx, "Avg Time (min)"] = "background-color: rgb(229,57,53); color:white; font-weight:700"
                    elif "Above target" in str(data.loc[idx, "Status"]): s.loc[idx, "Avg Time (min)"] = "background-color: rgb(251,140,0); color:black; font-weight:700"
                    else: s.loc[idx, "Avg Time (min)"] = "background-color: rgb(67,160,71); color:white; font-weight:700"
                return s

            display_lb = lb[["Resolver", "Total_Andons", "Avg_Time", "Efficiency", "Within_Threshold", "Badge", "Status"]].copy()
            display_lb.columns = ["Resolver", "Total Andons", "Avg Time (min)", "Efficiency Score", "% Within Threshold", "Badge", "Status"]
            st.dataframe(display_lb.style.apply(style_lb, axis=None).format({"Avg Time (min)": "{:.2f}", "Efficiency Score": "{:.2f}", "% Within Threshold": "{:.1f}%"}), use_container_width=True, height=450)

    # ── Tab: AFM Profile ────────────────────────────────────────────────────
    with tab["👤 AFM Profile"]:
        tab_pdf_download("AFM_Profile", fdf)
        st.markdown('<div class="sec-title">AFM Resolver Profile — Drill Down</div>', unsafe_allow_html=True)
        sel_profile = st.selectbox("Select Resolver", sorted(fdf["Resolver"].unique().tolist()), key="profile_sel")
        pdf = fdf[fdf["Resolver"] == sel_profile]

        if not pdf.empty:
            p_total = len(pdf)
            p_avg = pdf["Resolve_Min"].mean()
            p_med = pdf["Resolve_Min"].median()
            p_within = pdf.apply(within_threshold, axis=1).mean() * 100
            p_eff = p_total / p_avg if p_avg > 0 else 0

            st.markdown(f"""
            <div class="profile-card">
                <div class="profile-name">🧑‍💻 {sel_profile}</div>
                <div class="profile-sub">Resolver · {p_total:,} andons handled</div>
            </div>""", unsafe_allow_html=True)

            pk1, pk2, pk3, pk4, pk5 = st.columns(5)
            for c_obj, lbl, val, sub in [(pk1, "Total Andons", f"{p_total:,}", "handled"), (pk2, "Avg Time", f"{p_avg:.2f} min", "per andon"), (pk3, "Median Time", f"{p_med:.2f} min", "50th pct"), (pk4, "% Within Target", f"{p_within:.1f}%", "threshold"), (pk5, "Efficiency Score", f"{p_eff:.1f}", "andons÷avg")]:
                c_obj.markdown(f'<div class="kpi-box"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            show_cols = ["Time Created", "Andon Type", "Resolve_Min", "Status"]
            if optional_cols["Zone"]: show_cols.append("Zone")
            if optional_cols["Equipment ID"]: show_cols.append("Equipment ID")
            st.dataframe(pdf[show_cols].sort_values("Time Created", ascending=False).rename(columns={"Resolve_Min": "Time (min)"}), use_container_width=True, height=400, hide_index=True)

    # ── Tab: Root Cause Analysis ────────────────────────────────────────────
    with tab["🔍 Root Cause"]:
        tab_pdf_download("Root_Cause", fdf)
        st.markdown('<div class="sec-title">Root Cause Analysis — Recurring Issues</div>', unsafe_allow_html=True)
        type_counts = fdf["Andon Type"].value_counts()
        
        if not type_counts.empty:
            top_issue = type_counts.index[0]
            top_pct = type_counts.iloc[0] / len(fdf) * 100
            st.markdown(f"""
            <div class="rc-banner">
                <div class="rc-issue">🚨 Top Recurring Issue: {top_issue} ({top_pct:.1f}%)</div>
                <div class="rc-sub">{int(type_counts.iloc[0]):,} of {len(fdf):,} andons · Avg resolve time: {fdf[fdf['Andon Type']==top_issue]['Resolve_Min'].mean():.2f} min</div>
            </div>""", unsafe_allow_html=True)

            rc1, rc2 = st.columns(2)
            with rc1:
                tc_df = type_counts.reset_index()
                tc_df.columns = ["Andon Type", "Count"]
                tc_df["% of Total"] = (tc_df["Count"] / tc_df["Count"].sum() * 100).round(1)
                tc_df["Avg Time"] = tc_df["Andon Type"].map(fdf.groupby("Andon Type")["Resolve_Min"].mean().round(2))
                st.dataframe(tc_df.style.format({"Count": "{:,}", "% of Total": "{:.1f}%", "Avg Time": "{:.2f}"}), use_container_width=True, height=350, hide_index=True)

            with rc2:
                fig_rc_pie = px.pie(tc_df.head(12), names="Andon Type", values="Count", hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
                fig_rc_pie.update_layout(height=350, margin=dict(t=20, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig_rc_pie, use_container_width=True)

    # ── Tab: AFM Performance ────────────────────────────────────────────────
    with tab["AFM Performance"]:
        st.markdown('<div class="sec-title">Performance Matrix: Resolver × Andon Type</div>', unsafe_allow_html=True)
        sel_andon_types_afm = st.multiselect("🔽 Filter by Andon Type (empty = all)", options=sorted(fdf["Andon Type"].dropna().unique()), default=[], key="afm_perf_andon_filter")
        afm_fdf = fdf[fdf["Andon Type"].isin(sel_andon_types_afm)] if sel_andon_types_afm else fdf.copy()

        if afm_fdf.empty: st.warning("No data matches the selected Andon Type filter.")
        else:
            andon_types = sorted(afm_fdf["Andon Type"].dropna().unique())
            all_resolvers = sorted(afm_fdf["Resolver"].unique())
            cp = afm_fdf.pivot_table(index="Resolver", columns="Andon Type", values="Resolve_Min", aggfunc="count", fill_value=0).reindex(all_resolvers, fill_value=0)
            ap = afm_fdf.pivot_table(index="Resolver", columns="Andon Type", values="Resolve_Min", aggfunc="mean").round(2).reindex(all_resolvers)
            
            afm_cols = {}
            for cat in andon_types:
                afm_cols[(cat, "Count")] = cp[cat].astype(int)
                afm_cols[(cat, "Avg Time")] = ap[cat]
            afm_cols[("Total", "Count")] = cp[andon_types].sum(axis=1).astype(int)
            afm_cols[("Total", "Avg Time")] = afm_fdf.groupby("Resolver")["Resolve_Min"].mean().reindex(all_resolvers).round(2)
            
            afm_tbl = pd.DataFrame(afm_cols)
            afm_tbl.columns = pd.MultiIndex.from_tuples(afm_tbl.columns)
            st.dataframe(afm_tbl.style.format("{:.2f}", na_rep="—"), use_container_width=True, height=450)

    # ── Tab: AFM General ────────────────────────────────────────────────────
    with tab["📋 AFM General"]:
        if not optional_cols["Blocking"]: st.warning("⚠️ Data does not have a 'Blocking' column.")
        else:
            _base = fdf.copy()
            _base["_BL"] = _base["Blocking"].apply(lambda v: "no" if pd.isna(v) else ("yes" if str(v).strip().lower() in ("yes", "true", "1", "y") else "no"))
            st.markdown('<div class="sec-title">Performance by Strategic Category</div>', unsafe_allow_html=True)
            gf1, gf2, gf3 = st.columns([2, 2, 2])
            with gf1: gen_hidden = st.multiselect("🙈 Hide Resolvers", options=sorted(_base["Resolver"].unique().tolist()), default=[])
            with gf2: gen_show = st.multiselect("👁️ Show Only", options=sorted(_base["Resolver"].unique().tolist()), default=[])
            with gf3: gen_andon = st.multiselect("🔽 Filter Types", options=sorted(_base["Andon Type"].dropna().unique().tolist()), default=[])
            
            _gdf = _base[_base["Resolver"].isin(gen_show)] if gen_show else _base[~_base["Resolver"].isin(gen_hidden)] if gen_hidden else _base.copy()
            if gen_andon: _gdf = _gdf[_gdf["Andon Type"].isin(gen_andon)]
            
            if _gdf.empty: st.warning("No data matches current filters.")
            else:
                bl_df = _gdf[(_gdf["_BL"] == "yes") & (~_gdf["Andon Type"].isin(["Amnesty", "Drive Lacking Capability"]))]
                t_bl_today = _gdf[(_gdf["Date"] == _gdf["Date"].max()) & (_gdf["_BL"] == "yes") & (~_gdf["Andon Type"].isin(["Amnesty", "Drive Lacking Capability"]))] if not _gdf.empty else pd.DataFrame()
                t_hrs = (t_bl_today["Resolve_Min"].sum() / 60) if not t_bl_today.empty else 0
                
                hl1, hl2 = st.columns(2)
                hl1.markdown(f'<div class="kpi-box" style="border-top-color:#ef5350;"><div class="kpi-label">Latest Day Hours Lost</div><div class="kpi-value" style="color:#ef5350;">{t_hrs:.2f} hrs</div></div>', unsafe_allow_html=True)
                hl2.markdown(f'<div class="kpi-box" style="border-top-color:#3949ab;"><div class="kpi-label">Total Hours Lost</div><div class="kpi-value" style="color:#3949ab;">{bl_df["Resolve_Min"].sum()/60:.2f} hrs</div></div>', unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                daily_bl = bl_df.groupby("Date").agg(Hrs=("Resolve_Min", lambda x: x.sum()/60)).reset_index()
                if not daily_bl.empty:
                    fig_hl = px.bar(daily_bl, x="Date", y="Hrs", title="Daily Hours Lost (Blocking)", color_discrete_sequence=["#ef5350"])
                    fig_hl.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_hl, use_container_width=True)

    # ── Extra Tabs Fallbacks ────────────────────────────────────────────────
    with tab["By Andon Type"]:
        tbl_at = build_group_pivot(fdf, "Andon Type")
        st.dataframe(apply_pivot_style(tbl_at), use_container_width=True)

    with tab["Weekly Breakdown"]:
        st.markdown('<div class="sec-title">Weekly Summaries</div>', unsafe_allow_html=True)
        if not fdf.empty:
            wk_cnt = fdf.pivot_table(index="Andon Type", columns="Week", values="Resolve_Min", aggfunc="count", fill_value=0)
            st.dataframe(wk_cnt.style.format("{:,.0f}"), use_container_width=True)

    if optional_cols["Blocking"] and optional_cols["Equipment ID"]:
        with tab["🏭 Dept Blocking Analysis"]:
            st.markdown('<div class="sec-title">Department Blocking Impact</div>', unsafe_allow_html=True)
            dept_bl = fdf[(fdf["Blocking"].apply(lambda v: str(v).strip().lower() in ("yes", "true", "1", "y"))) & (~fdf["Andon Type"].isin(BLOCKING_EXCLUDE_TYPES))].copy()
            if not dept_bl.empty:
                dept_bl["Department"] = dept_bl["Equipment ID"].apply(get_department)
                dept_sum = dept_bl.groupby("Department").agg(Count=("Resolve_Min","count"), Hrs=("Resolve_Min", lambda x: x.sum()/60)).reset_index()
                fig_dpt = px.pie(dept_sum, names="Department", values="Hrs", hole=0.5, color="Department", color_discrete_map=DEPT_COLORS, title="Hours Lost by Dept")
                fig_dpt.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_dpt, use_container_width=True)

    with tab["Raw Data"]:
        st.markdown('<div class="sec-title">Raw Data Export</div>', unsafe_allow_html=True)
        st.dataframe(fdf, use_container_width=True, hide_index=True)

    with tab["📤 Export"]:
        st.markdown('<div class="sec-title">Generate Excel & PDF Reports</div>', unsafe_allow_html=True)
        st.info("💡 Report building scripts trigger via the pre-configured external modules (`report_builder`, `pdf_report`). Ensure these remain in your working directory.")

    with tab["📂 History"]:
        st.markdown('<div class="sec-title">Saved Data Log</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(history_records), use_container_width=True, hide_index=True)

else:
    # ── Landing State ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; padding:5rem 2rem;
                background: {"linear-gradient(135deg, #1a1d27 0%, #1e2235 100%)" if DM else "linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)"};
                border-radius:16px; margin-top:1.5rem;
                border: 2px dashed {"rgba(121,134,203,0.3)" if DM else "rgba(57,73,171,0.2)"};
                box-shadow: {_css_chart_shadow};">
        <div style="font-size:4rem;margin-bottom:1rem;">📊</div>
        <h2 style="color:{"#ffffff" if DM else "#1a237e"}; margin-bottom:0.5rem; font-size:1.8rem; font-weight:900;">Welcome to the LCY3 AFM Dashboard</h2>
        <p style="color:{_sub}; font-size:1.05rem;">Upload a <strong style="color:{_accent};">JSON or CSV file</strong> above to explore your Andon data</p>
    </div>
    """, unsafe_allow_html=True)
