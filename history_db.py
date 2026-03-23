"""
history_db.py  —  persistent upload history with structured storage.

history/
├── daily/      — per-day aggregated records for each upload
├── weekly/     — per-week aggregated records for each upload
└── processed/  — full raw DataFrames (parquet)
"""

import hashlib
import json
import pathlib

import pandas as pd

_BASE_DIR  = pathlib.Path("history")
_DAILY_DIR = _BASE_DIR / "daily"
_WEEK_DIR  = _BASE_DIR / "weekly"
_PROC_DIR  = _BASE_DIR / "processed"
_META_FILE = _BASE_DIR / "metadata.json"

_OLD_DIR   = pathlib.Path(".andon_data")


def _ensure_dirs():
    for d in (_DAILY_DIR, _WEEK_DIR, _PROC_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _load_meta() -> dict:
    _ensure_dirs()
    if _META_FILE.exists():
        try:
            return json.loads(_META_FILE.read_text())
        except Exception:
            return {}
    # Backward-compat: migrate old .andon_data/metadata.json
    old = _OLD_DIR / "metadata.json"
    if old.exists():
        try:
            return json.loads(old.read_text())
        except Exception:
            return {}
    return {}


def _save_meta(meta: dict):
    _ensure_dirs()
    _META_FILE.write_text(json.dumps(meta, indent=2))


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _compute_daily(df: pd.DataFrame, file_name: str) -> pd.DataFrame | None:
    if "Time Created" not in df.columns:
        return None
    tmp = df.copy()
    tmp["_date"] = pd.to_datetime(tmp["Time Created"], errors="coerce").dt.date
    tmp = tmp.dropna(subset=["_date"])
    if tmp.empty:
        return None

    agg = tmp.groupby("_date").size().reset_index(name="Total_Andons")

    if "Resolve_Min" in tmp.columns:
        agg["Avg_Resolve_Min"] = (
            tmp.groupby("_date")["Resolve_Min"].mean().values
        )

    if "Status" in tmp.columns:
        resolved = (
            tmp[tmp["Status"] == "Resolved"]
            .groupby("_date")
            .size()
            .rename("Resolved")
        )
        agg = agg.join(resolved, on="_date")

    if "Andon Type" in tmp.columns:
        top = (
            tmp.groupby(["_date", "Andon Type"])
            .size()
            .reset_index(name="_n")
        )
        top = (
            top.loc[top.groupby("_date")["_n"].idxmax()][["_date", "Andon Type"]]
            .rename(columns={"Andon Type": "Top_Andon_Type"})
        )
        agg = agg.merge(top, on="_date", how="left")

    if "Resolver" in tmp.columns:
        top_res = (
            tmp.groupby(["_date", "Resolver"])
            .size()
            .reset_index(name="_n")
        )
        top_res = (
            top_res.loc[top_res.groupby("_date")["_n"].idxmax()][["_date", "Resolver"]]
            .rename(columns={"Resolver": "Top_Resolver"})
        )
        agg = agg.merge(top_res, on="_date", how="left")

    agg.rename(columns={"_date": "Date"}, inplace=True)
    agg["File_Name"]   = file_name
    agg["Upload_Date"] = str(pd.Timestamp.now().date())
    return agg


def _compute_weekly(df: pd.DataFrame, file_name: str) -> pd.DataFrame | None:
    if "Week" not in df.columns:
        return None
    tmp = df.copy()
    tmp["Week"] = pd.to_numeric(tmp["Week"], errors="coerce")
    tmp = tmp.dropna(subset=["Week"])
    tmp["Week"] = tmp["Week"].astype(int)
    if tmp.empty:
        return None

    agg = tmp.groupby("Week").size().reset_index(name="Total_Andons")

    if "Resolve_Min" in tmp.columns:
        agg["Avg_Resolve_Min"] = (
            tmp.groupby("Week")["Resolve_Min"].mean().values
        )

    if "Status" in tmp.columns:
        resolved = (
            tmp[tmp["Status"] == "Resolved"]
            .groupby("Week")
            .size()
            .rename("Resolved")
        )
        agg = agg.join(resolved, on="Week")

    if "Andon Type" in tmp.columns:
        top = (
            tmp.groupby(["Week", "Andon Type"])
            .size()
            .reset_index(name="_n")
        )
        top = (
            top.loc[top.groupby("Week")["_n"].idxmax()][["Week", "Andon Type"]]
            .rename(columns={"Andon Type": "Top_Andon_Type"})
        )
        agg = agg.merge(top, on="Week", how="left")

    if "Resolver" in tmp.columns:
        top_res = (
            tmp.groupby(["Week", "Resolver"])
            .size()
            .reset_index(name="_n")
        )
        top_res = (
            top_res.loc[top_res.groupby("Week")["_n"].idxmax()][["Week", "Resolver"]]
            .rename(columns={"Resolver": "Top_Resolver"})
        )
        agg = agg.merge(top_res, on="Week", how="left")

    agg["File_Name"]   = file_name
    agg["Upload_Date"] = str(pd.Timestamp.now().date())
    return agg


# ── Public API ────────────────────────────────────────────────────────────────

def compute_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def hash_exists(file_hash: str) -> bool:
    return file_hash in _load_meta()


def get_existing_name(file_hash: str) -> str:
    return _load_meta().get(file_hash, {}).get("file_name", "unknown")


def record_upload(file_name: str, df: pd.DataFrame, file_hash: str):
    _ensure_dirs()

    # ── processed/ ──────────────────────────────────────────────────────────
    df.to_parquet(_PROC_DIR / f"{file_hash}.parquet", index=False)

    # ── daily/ ──────────────────────────────────────────────────────────────
    daily_df = _compute_daily(df, file_name)
    has_daily = daily_df is not None
    if has_daily:
        daily_df.to_parquet(_DAILY_DIR / f"{file_hash}_daily.parquet", index=False)

    # ── weekly/ ─────────────────────────────────────────────────────────────
    weekly_df = _compute_weekly(df, file_name)
    has_weekly = weekly_df is not None
    if has_weekly:
        weekly_df.to_parquet(_WEEK_DIR / f"{file_hash}_weekly.parquet", index=False)

    # ── metadata ────────────────────────────────────────────────────────────
    weeks = []
    if "Week" in df.columns:
        weeks = sorted([int(w) for w in df["Week"].dropna().unique().tolist()])

    date_min = date_max = upload_ts = ""
    if "Time Created" in df.columns:
        tc = pd.to_datetime(df["Time Created"], errors="coerce").dropna()
        if not tc.empty:
            date_min  = str(tc.min().date())
            date_max  = str(tc.max().date())
            upload_ts = str(tc.max())

    meta = _load_meta()
    meta[file_hash] = {
        "file_name":    file_name,
        "upload_ts":    upload_ts,
        "upload_date":  str(pd.Timestamp.now().date()),
        "total_andons": len(df),
        "week_numbers": weeks,
        "date_min":     date_min,
        "date_max":     date_max,
        "has_daily":    has_daily,
        "has_weekly":   has_weekly,
    }
    _save_meta(meta)


def load_dataframe(file_hash: str) -> pd.DataFrame | None:
    for path in (
        _PROC_DIR / f"{file_hash}.parquet",
        _OLD_DIR  / f"{file_hash}.parquet",   # backward compat
    ):
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception:
                pass
    return None


def load_daily(file_hash: str) -> pd.DataFrame | None:
    path = _DAILY_DIR / f"{file_hash}_daily.parquet"
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            return None
    return None


def load_weekly(file_hash: str) -> pd.DataFrame | None:
    path = _WEEK_DIR / f"{file_hash}_weekly.parquet"
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            return None
    return None


def get_history(n: int = 20) -> list[dict]:
    meta = _load_meta()
    records = []
    for fhash, info in meta.items():
        records.append({
            "file_hash":    fhash,
            "file_name":    info.get("file_name", "unknown"),
            "upload_ts":    info.get("upload_ts", ""),
            "upload_date":  info.get("upload_date", ""),
            "total_andons": info.get("total_andons", 0),
            "week_numbers": info.get("week_numbers", []),
            "date_min":     info.get("date_min", ""),
            "date_max":     info.get("date_max", ""),
            "has_daily":    info.get("has_daily", False),
            "has_weekly":   info.get("has_weekly", False),
        })
    records.sort(key=lambda r: r["upload_ts"], reverse=True)
    return records[:n]


def remove_entry(file_hash: str):
    meta = _load_meta()
    if file_hash in meta:
        del meta[file_hash]
        _save_meta(meta)
    for path in (
        _PROC_DIR / f"{file_hash}.parquet",
        _DAILY_DIR / f"{file_hash}_daily.parquet",
        _WEEK_DIR  / f"{file_hash}_weekly.parquet",
        _OLD_DIR   / f"{file_hash}.parquet",
    ):
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass


def clear_history():
    for fhash in list(_load_meta().keys()):
        remove_entry(fhash)
    _save_meta({})
