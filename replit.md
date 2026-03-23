# LCY3 AFM Dashboard — Floor Health

A Streamlit data visualization tool for monitoring Floor Health and Andon performance at an Amazon fulfillment center (LCY3). Built by **Manish Karki**.

## Tech Stack
- Python 3.12
- Streamlit (port 5000, 0.0.0.0)
- Pandas, Plotly, openpyxl, pyarrow

## Project Structure

```
app.py              — Main Streamlit application
history_db.py       — Persistent storage layer (Parquet + JSON)
report_builder.py   — Excel report generation (daily + weekly .xlsx)
requirements.txt
.streamlit/config.toml

history/            — Persistent upload history (created at runtime)
├── daily/          — Per-day aggregated Parquet files
├── weekly/         — Per-week aggregated Parquet files
├── processed/      — Full raw DataFrames (one per upload)
└── metadata.json   — Index of all saved records

.andon_data/        — Legacy storage location (backward-compat, read-only)
```

## Key Features

### Dashboard Tabs
1. **Overview** — bar chart of top resolvers, donut of andon types, daily trend spline
2. **Leaderboard** — ranked resolver table with colour-coded performance badges
3. **AFM Profile** — individual resolver deep-dive
4. **Root Cause** — recurring issue analysis
5. **AFM Performance** — team performance metrics
6. **By Andon Type / Equipment / Zone / Shift / Blocking / Equipment ID** — pivot breakdowns (optional columns unlock these)
7. **Weekly Breakdown** — weekly trend charts
8. **Hourly Trend / Heatmap** — time-of-day analysis
9. **Raw Data** — full filtered DataFrame view
10. **Export** — download multi-sheet Excel reports
11. **History** — browse saved daily, weekly, and processed datasets per upload

### Persistent Storage (`history_db.py`)
Every uploaded file is saved to `history/`:
- `processed/<hash>.parquet` — full raw data
- `daily/<hash>_daily.parquet` — aggregated by date: total andons, avg resolve time, resolved count, top andon type, top resolver
- `weekly/<hash>_weekly.parquet` — same metrics grouped by ISO week number
- `metadata.json` — index with file name, upload date, week numbers, date range, andon count

**Key functions:** `compute_hash`, `hash_exists`, `get_existing_name`, `record_upload`, `load_dataframe`, `load_daily`, `load_weekly`, `get_history`, `remove_entry`, `clear_history`

### Sidebar
- Dark mode toggle
- Saved Datasets list — Load/Unload and Remove buttons per file, ACTIVE badge, Clear All

### Status Labels
- ✅ On target
- ⚠️ Above target
- ⚠️ Average (was "🚨 Slow" — renamed)

### Duplicate Detection
SHA-256 hash of uploaded file bytes; re-uploads are blocked and auto-pointed to the saved copy.

### Session State Keys
- `dark_mode` — boolean
- `saved_active_hashes` — list of file hashes currently loaded into the dashboard
- `duplicate_warnings` — list of warning messages

## Required Input Columns
`Status`, `Resolver`, `Andon Type`, `Dwell Time (hh:mm:ss)`, `Time Created`

## Optional Columns (unlock extra tabs)
`Equipment Type`, `Zone`, `Shift`, `Blocking`, `Equipment ID`
