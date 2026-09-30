"""引导页渲染：卡片网格 + PE 升序 + 可点击筛选。"""
import glob
import json
from datetime import datetime
from pathlib import Path

from ..cache import OUTPUT_DIR, data_path
from ..config import TEMPLATES_DIR
from .. import registry


def _val_tag(pe):
    if pe is None or pe == 0:
        return ("—", "#64748b")
    if pe < 15:
        return ("低估", "#22c55e")
    elif pe < 25:
        return ("合理", "#fbbf24")
    return ("偏高", "#ef4444")


def _hold_tag(pe, dy):
    if pe is None:
        return ("—", "#64748b")
    if pe < 15 and (dy or 0) > 5:
        return ("可持有", "#22c55e")
    elif pe < 25:
        return ("观望", "#fbbf24")
    return ("规避", "#ef4444")


def collect():
    """以 registry 为权威来源生成卡片数据：注册表里的股票永远出现在导航页，
    缺 *_data.json 或 quote 含 error 的显示「待抓取」占位卡片。"""
    stocks = []
    for s in registry.load():
        code = str(s.get("code", ""))
        name = s.get("name") or code
        sector = s.get("sector", "")
        fp = OUTPUT_DIR / f"{code}_data.json"
        d = None
        if fp.exists():
            try:
                d = json.loads(Path(fp).read_text(encoding="utf-8"))
            except Exception:
                d = None
        if not d or "error" in d.get("quote", {}):
            stocks.append({
                "code": code, "name": name, "sector": sector,
                "price": 0, "chg": 0, "pe": 0, "pb": 0, "dy": 0, "mcap": 0,
                "vt": "—", "vc": "#64748b", "ht": "—", "hc": "#64748b",
                "data_date": "", "missing": True,
            })
            continue
        q = d.get("quote", {})
        dy = d.get("dividend_yield_ttm", {}).get("yield_pct", 0)
        pe = q.get("pe_ttm", 0)
        vt, vc = _val_tag(pe)
        ht, hc = _hold_tag(pe, dy)
        stocks.append({
            "code": d.get("code", code), "name": d.get("name", name),
            "sector": d.get("sector", sector),
            "price": q.get("price", 0), "chg": q.get("change_pct", 0),
            "pe": pe, "pb": q.get("pb", 0), "dy": dy, "mcap": q.get("mcap_yi", 0),
            "vt": vt, "vc": vc, "ht": ht, "hc": hc,
            "data_date": d.get("data_date", ""), "missing": False,
        })
    stocks.sort(key=lambda s: s["pe"] if (not s["missing"] and s["pe"]) else float("inf"))
    return stocks


def build_index():
    stocks = collect()
    if not stocks:
        print("⚠️ 未找到任何 *_data.json，请先运行 fetch / refresh")
        return None

    low_pe = sum(1 for s in stocks if s["pe"] and s["pe"] < 15)
    high_dy = sum(1 for s in stocks if s["dy"] and s["dy"] > 5)
    up = sum(1 for s in stocks if s["chg"] and s["chg"] >= 0)

    stats = f"""<div class="stat clickable active" data-filter="all" onclick="applyFilter(this)"><div class="n">{len(stocks)}</div><div class="l">覆盖标的（点击筛选）</div></div>
      <div class="stat clickable" data-filter="lowpe" onclick="applyFilter(this)"><div class="n" style="color:#22c55e">{low_pe}</div><div class="l">PE&lt;15 低估</div></div>
      <div class="stat clickable" data-filter="highdy" onclick="applyFilter(this)"><div class="n" style="color:#fbbf24">{high_dy}</div><div class="l">股息率&gt;5%</div></div>
      <div class="stat clickable" data-filter="up" onclick="applyFilter(this)"><div class="n">{up}/{len(stocks)}</div><div class="l">当日上涨</div></div>"""

    cards = ""
    for s in stocks:
        if s["missing"]:
            cards += f"""
      <div class="card missing" data-missing="1" title="运行 stockval refresh {s['code']} 抓取数据">
        <div class="card-top">
          <div>
            <div class="s-name">{s['name']}</div>
            <div class="s-code">{s['code']} · {s['sector']}</div>
          </div>
          <div class="s-price">
            <div class="price">—</div>
            <div class="chg" style="color:#64748b">待抓取</div>
          </div>
        </div>
        <div class="card-metrics">
          <div class="m"><span>PE(TTM)</span><b>—</b></div>
          <div class="m"><span>PB</span><b>—</b></div>
          <div class="m"><span>股息率</span><b>—</b></div>
          <div class="m"><span>市值</span><b>—</b></div>
        </div>
        <div class="card-tags">
          <span class="tag" style="background:#64748b20;color:#64748b">未抓取</span>
          <span class="tag ext">refresh {s['code']} →</span>
        </div>
      </div>"""
            continue
        chg_color = "#ef4444" if s["chg"] >= 0 else "#22c55e"
        cards += f"""
      <a class="card" href="{s['code']}_valuation_report.html" target="_blank" data-pe="{s['pe']}" data-dy="{s['dy']}" data-chg="{s['chg']}">
        <div class="card-top">
          <div>
            <div class="s-name">{s['name']}</div>
            <div class="s-code">{s['code']} · {s['sector']}</div>
          </div>
          <div class="s-price">
            <div class="price">¥{s['price']:.2f}</div>
            <div class="chg" style="color:{chg_color}">{s['chg']:+.2f}%</div>
          </div>
        </div>
        <div class="card-metrics">
          <div class="m"><span>PE(TTM)</span><b style="color:{s['vc']}">{s['pe']:.1f}x</b></div>
          <div class="m"><span>PB</span><b>{s['pb']:.2f}x</b></div>
          <div class="m"><span>股息率</span><b style="color:#fbbf24">{s['dy']:.2f}%</b></div>
          <div class="m"><span>市值</span><b>¥{s['mcap']:.0f}亿</b></div>
        </div>
        <div class="card-tags">
          <span class="tag" style="background:{s['vc']}20;color:{s['vc']}">贵: {s['vt']}</span>
          <span class="tag" style="background:{s['hc']}20;color:{s['hc']}">拿: {s['ht']}</span>
          <span class="tag ext">详情 →</span>
        </div>
      </a>"""

    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tokens = {
        "TITLE": "A股全维估值体检 · 股票导航",
        "SUB": (f"共 {len(stocks)} 支标的 · 实时行情/机构一致预期/融资资金/股东筹码/研报/分红 七维透视"
                f" · 数据日期 {next((s['data_date'] for s in stocks if s['data_date']), '—')} · 卡片按 PE(TTM) 由低到高排序"),
        "STATS": stats,
        "CARDS": cards,
        "FILTER_COUNT": str(len(stocks)),
        "FOOT_SRC": (f"数据来源：腾讯财经 · 东方财富(datacenter/reportapi) · 同花顺(机构一致预期EPS)"
                     f"　|　生成时间：{gen_time}"),
    }

    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    for k, v in tokens.items():
        html = html.replace(f"[[{k}]]", str(v))
    return html
