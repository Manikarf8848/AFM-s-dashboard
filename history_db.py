"""
history_db.py  —  persistent upload history using Parquet + JSON metadata.
Data is stored under .andon_data/ and survives server restarts.
"""

import hashlib
import json
import pathlib

import pandas as pd

_DATA_DIR = pathlib.Path(".andon_data")
_META_FILE = _DATA_DIR / "metadata.json"


def _ensure_dir():
    _DATA_DIR.mkdir(exist_ok=True)


def _load_meta() -> dict:
    _ensure_dir()
    if _META_FILE.exists():
        try:
            return json.loads(_META_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_meta(meta: dict):
    _ensure_dir()
    _META_FILE.write_text(json.dumps(meta, indent=2))


# ── Public API ────────────────────────────────────────────────────────────────

def compute_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def hash_exists(file_hash: str) -> bool:
    return file_hash in _load_meta()


def get_existing_name(file_hash: str) -> str:
    meta = _load_meta()
    return meta.get(file_hash, {}).get("file_name", "unknown")


def record_upload(file_name: str, df: pd.DataFrame, file_hash: str):
    _ensure_dir()
    parquet_path = _DATA_DIR / f"{file_hash}.parquet"
    df.to_parquet(parquet_path, index=False)

    weeks = []
    if "Week" in df.columns:
        weeks = sorted([int(w) for w in df["Week"].dropna().unique().tolist()])

    date_min = date_max = upload_ts = ""
    if "Time Created" in df.columns:
        tc = pd.to_datetime(df["Time Created"], errors="coerce").dropna()
        if not tc.empty:
            date_min = str(tc.min().date())
            date_max = str(tc.max().date())
            upload_ts = str(tc.max())

    meta = _load_meta()
    meta[file_hash] = {
        "file_name": file_name,
        "upload_ts": upload_ts,
        "total_andons": len(df),
        "week_numbers": weeks,
        "date_min": date_min,
        "date_max": date_max,
    }
    _save_meta(meta)


def load_dataframe(file_hash: str) -> pd.DataFrame | None:
    parquet_path = _DATA_DIR / f"{file_hash}.parquet"
    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path)
        except Exception:
            return None
    return None


def get_history(n: int = 20) -> list[dict]:
    meta = _load_meta()
    records = []
    for fhash, info in meta.items():
        records.append({
            "file_hash": fhash,
            "file_name": info.get("file_name", "unknown"),
            "upload_ts": info.get("upload_ts", ""),
            "total_andons": info.get("total_andons", 0),
            "week_numbers": info.get("week_numbers", []),
            "date_min": info.get("date_min", ""),
            "date_max": info.get("date_max", ""),
        })
    records.sort(key=lambda r: r["upload_ts"], reverse=True)
    return records[:n]


def remove_entry(file_hash: str):
    meta = _load_meta()
    if file_hash in meta:
        del meta[file_hash]
        _save_meta(meta)
    parquet_path = _DATA_DIR / f"{file_hash}.parquet"
    if parquet_path.exists():
        parquet_path.unlink()


def clear_history():
    meta = _load_meta()
    for fhash in list(meta.keys()):
        parquet_path = _DATA_DIR / f"{fhash}.parquet"
        if parquet_path.exists():
            parquet_path.unlink()
    _save_meta({})
