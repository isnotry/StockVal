"""缓存层：每只股票的数据 JSON 落盘到 output/，带 fetch_time 时间戳。"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from .config import OUTPUT_DIR, CACHE_MAX_AGE_HOURS


def data_path(code):
    return OUTPUT_DIR / f"{code}_data.json"


def report_path(code):
    return OUTPUT_DIR / f"{code}_valuation_report.html"


def index_path():
    return OUTPUT_DIR / "index.html"


def is_fresh(code, max_age_hours=CACHE_MAX_AGE_HOURS):
    p = data_path(code)
    if not p.exists():
        return False
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        ft = d.get("fetch_time")
        if not ft:
            return False
        ft_dt = datetime.strptime(ft, "%Y-%m-%d %H:%M:%S")
        return datetime.now() - ft_dt < timedelta(hours=max_age_hours)
    except Exception:
        return False


def save(code, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data_path(code).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def load(code):
    p = data_path(code)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def delete(code):
    for p in (data_path(code), report_path(code)):
        if p.exists():
            p.unlink()
