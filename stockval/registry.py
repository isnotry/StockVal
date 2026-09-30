"""自选股注册表：持久化到 registry.json（替代原脚本的硬编码 STOCKS 列表）。"""
import json
from pathlib import Path

from .config import REGISTRY_PATH


def load():
    if REGISTRY_PATH.exists():
        try:
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save(stocks):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(stocks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add(code, name, sector=""):
    code = str(code)
    stocks = load()
    if any(s.get("code") == code for s in stocks):
        return False
    stocks.append({"code": code, "name": name, "sector": sector or ""})
    save(stocks)
    return True


def remove(code):
    code = str(code)
    stocks = load()
    new = [s for s in stocks if s.get("code") != code]
    changed = len(new) != len(stocks)
    save(new)
    return changed


def get(code):
    return next((s for s in load() if s.get("code") == str(code)), None)


def codes():
    return [s.get("code") for s in load()]


def count():
    return len(load())
