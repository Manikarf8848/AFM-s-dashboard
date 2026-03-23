"""
history_db.py  —  Persistent upload history using local disk storage.
Each uploaded file is saved as a Parquet file, metadata in JSON.
Data survives server restarts.
"""

import os
import json
import hashlib
import datetime
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(__file__), ".andon_data")
_META_FILE = os.path.join(_DATA_DIR, "metadata.json")


def _ensure_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_meta() -> list:
    _ensure_dir()
    if not os.path.exists(_META_FILE):
        return []
    try:
        with open(_META_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_meta(records: list):
    _ensure_dir()
    with open(_META_FILE, "w") as f:
        json.dump(records, f, indent=2)


def compute_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()[:16]


def hash_exists(file_hash: str) -> bool:
    records = _load_meta()
    return any(r["file_hash"] == file_hash for r in records)


def get_existing_name(file_hash: str) -> str:
    records = _load_meta()
    for r in records:
        if r["file_hash"] == file_hash:
            return r["file_name"]
    return ""


def record_upload(file_name: str, df: pd.DataFrame, file_hash: str = ""):
    _ensure_dir()
    records = _load_meta()

    if file_hash and any(r["file_hash"] == file_hash for r in records):
        return

    weeks = []
    if "Week" in df.columns:
        weeks = sorted([int(w) for w in df["Week"].dropna().unique().tolist()])

    date_min = date_max = upload_ts = ""
    if "Time Created" in df.columns:
        tc = pd.to_datetime(df["Time Created"], errors="coerce").dropna()
        if not tc.empty:
            date_min = str(tc.min().date())
            date_max = str(tc.max().date())

    upload_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not file_hash:
        file_hash = hashlib.sha256(file_name.encode()).hexdigest()[:16]

    parquet_path = os.path.join(_DATA_DIR, f"{file_hash}.parquet")
    try:
        df.to_parquet(parquet_path, index=False)
    except Exception:
        try:
            df.to_csv(parquet_path.replace(".parquet", ".csv"), index=False)
            parquet_path = parquet_path.replace(".parquet", ".csv")
        except Exception:
            pass

    records.insert(0, {
        "file_name":    file_name,
        "file_hash":    file_hash,
        "upload_ts":    upload_ts,
        "total_andons": len(df),
        "week_numbers": weeks,
        "date_min":     date_min,
        "date_max":     date_max,
        "data_path":    parquet_path,
    })
    _save_meta(records)


def get_history(n: int = 50) -> list:
    return _load_meta()[:n]


def load_dataframe(file_hash: str) -> pd.DataFrame | None:
    records = _load_meta()
    for r in records:
        if r["file_hash"] == file_hash:
            path = r.get("data_path", "")
            if path and os.path.exists(path):
                try:
                    if path.endswith(".parquet"):
                        return pd.read_parquet(path)
                    else:
                        return pd.read_csv(path)
                except Exception:
                    return None
    return None


def remove_entry(file_hash: str):
    records = _load_meta()
    new_records = []
    for r in records:
        if r["file_hash"] == file_hash:
            path = r.get("data_path", "")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        else:
            new_records.append(r)
    _save_meta(new_records)


def clear_history():
    records = _load_meta()
    for r in records:
        path = r.get("data_path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    _save_meta([])
