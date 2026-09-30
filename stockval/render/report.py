"""单只股票报告渲染：从缓存数据 D 生成暗色科技风 HTML。"""
import json
from datetime import datetime
from pathlib import Path

from ..config import TEMPLATES_DIR
from .utils import color_up_down, fmt_yi, fmt_wan, fmt_num

RATING_COLOR = {
    "买入": "#ef4444", "增持": "#f97316", "中性": "#fbbf24",
    "减持": "#22c55e", "卖出": "#16a34a",
}


def _load_template():
    return (TEMPLATES_DIR / "report.html").read_text(encoding="utf-8")


def gen_price_svg(klines):
    if not klines or not isinstance(klines, list):
        return '<div style="color:#888;text-align:center;padding:40px">K线数据不可用</div>'
    W, H = 900, 280
    PAD_L, PAD_R, PAD_T, PAD_B = 50, 20, 20, 35
    cw = W - PAD_L - PAD_R
    ch = H - PAD_T - PAD_B
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    n = len(klines)
    y_min = min(lows) * 0.98
    y_max = max(highs) * 1.02
    y_range = y_max - y_min if y_max > y_min else 1

    def x(i):
        return PAD_L + (i / max(n - 1, 1)) * cw

    def y(val):
        return PAD_T + (1 - (val - y_min) / y_range) * ch

    grid_lines = ""
    for i in range(5):
        gy = PAD_T + (i / 4) * ch
        gv = y_max - (i / 4) * y_range
        grid_lines += f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W-PAD_R}" y2="{gy:.1f}" stroke="#1a1a2e" stroke-width="0.5"/>'
        grid_lines += f'<text x="{PAD_L-5}" y="{gy+4:.1f}" fill="#666" font-size="10" text-anchor="end" font-family="monospace">{gv:.2f}</text>'
    points = " ".join(f"{x(i):.1f},{y(closes[i]):.1f}" for i in range(n))
    area_path = f"M {x(0):.1f},{y(closes[0]):.1f} " + " ".join(f"L {x(i):.1f},{y(closes[i]):.1f}" for i in range(1, n))
    area_path += f" L {x(n-1):.1f},{PAD_T+ch} L {x(0):.1f},{PAD_T+ch} Z"
    band_path = f"M {x(0):.1f},{y(highs[0]):.1f} " + " ".join(f"L {x(i):.1f},{y(highs[i]):.1f}" for i in range(1, n))
    band_path += " " + " ".join(f"L {x(i):.1f},{y(lows[n-1-i]):.1f}" for i in range(n)) + " Z"
    x_labels = ""
    step = max(1, n // 8)
    for i in range(0, n, step):
        x_labels += f'<text x="{x(i):.1f}" y="{H-15}" fill="#666" font-size="9" text-anchor="middle" font-family="monospace">{klines[i]["date"][5:]}</text>'
    last_x, last_y = x(n - 1), y(closes[-1])
    trend_color = "#ef4444" if closes[-1] >= closes[0] else "#22c55e"
    return f'''<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{trend_color}" stop-opacity="0.15"/><stop offset="100%" stop-color="{trend_color}" stop-opacity="0"/></linearGradient></defs>
  {grid_lines}
  <path d="{area_path}" fill="url(#priceGrad)"/>
  <polyline points="{points}" fill="none" stroke="{trend_color}" stroke-width="1.5" stroke-linejoin="round"/>
  <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="{trend_color}"/>
  <text x="{last_x:.1f}" y="{last_y-8:.1f}" fill="{trend_color}" font-size="11" text-anchor="middle" font-family="monospace" font-weight="bold">{closes[-1]:.2f}</text>
  {x_labels}
  <text x="{PAD_L}" y="{H-2}" fill="#555" font-size="9" font-family="monospace">数据源: 腾讯财经 | {klines[0]["date"]} ~ {klines[-1]["date"]} ({n}个交易日)</text>
</svg>'''


def gen_margin_bar_svg(mb_chart_data):
    if not mb_chart_data:
        return '<div style="color:#888;text-align:center;padding:40px">融资数据不可用</div>'
    W, H = 900, 220
    PAD_L, PAD_R, PAD_T, PAD_B = 55, 20, 20, 35
    cw = W - PAD_L - PAD_R
    ch = H - PAD_T - PAD_B
    n = len(mb_chart_data)
    vals = [d["net"] / 1e8 for d in mb_chart_data]
    y_max = max(max(vals), 0)
    y_min = min(min(vals), 0)
    y_range = y_max - y_min if y_max > y_min else 1

    def x(i):
        return PAD_L + (i / max(n, 1)) * cw

    def y(val):
        return PAD_T + (1 - (val - y_min) / y_range) * ch

    bar_w = max(cw / n * 0.7, 2)
    zero_y = y(0)
    grid = ""
    for i in range(5):
        gy = PAD_T + (i / 4) * ch
        gv = y_max - (i / 4) * y_range
        grid += f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W-PAD_R}" y2="{gy:.1f}" stroke="#1a1a2e" stroke-width="0.5"/>'
        grid += f'<text x="{PAD_L-5}" y="{gy+4:.1f}" fill="#666" font-size="10" text-anchor="end" font-family="monospace">{gv:+.2f}</text>'
    grid += f'<line x1="{PAD_L}" y1="{zero_y:.1f}" x2="{W-PAD_R}" y2="{zero_y:.1f}" stroke="#444" stroke-width="0.8"/>'
    bars = ""
    for i, v in enumerate(vals):
        bx = x(i) + (cw / n - bar_w) / 2
        if v >= 0:
            by = y(v)
            bh = zero_y - by
            color = "#ef4444"
        else:
            by = zero_y
            bh = y(v) - zero_y
            color = "#22c55e"
        bars += f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85" rx="1"/>'
    x_labels = ""
    step = max(1, n // 8)
    for i in range(0, n, step):
        x_labels += f'<text x="{x(i)+cw/n/2:.1f}" y="{H-15}" fill="#666" font-size="9" text-anchor="middle" font-family="monospace">{mb_chart_data[i]["date"][5:]}</text>'
    return f'''<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto" xmlns="http://www.w3.org/2000/svg">
  {grid}{bars}{x_labels}
  <text x="{PAD_L}" y="{H-2}" fill="#555" font-size="9" font-family="monospace">数据源: 东方财富 datacenter | 融资余额日变化(净买入替代) | 近{n}个交易日</text>
</svg>'''


def gen_margin_trend_svg(margin_rev):
    if not margin_rev:
        return '<div style="color:#888;text-align:center;padding:40px">融资余额趋势不可用</div>'
    W, H = 900, 180
    PAD_L, PAD_R, PAD_T, PAD_B = 50, 20, 15, 30
    cw = W - PAD_L - PAD_R
    ch = H - PAD_T - PAD_B
    data = margin_rev[-40:] if len(margin_rev) >= 40 else margin_rev
    n = len(data)
    vals = [d["rzye"] / 1e8 for d in data]
    y_min = min(vals) * 0.95
    y_max = max(vals) * 1.05
    y_range = y_max - y_min if y_max > y_min else 1

    def x(i):
        return PAD_L + (i / max(n - 1, 1)) * cw

    def y(val):
        return PAD_T + (1 - (val - y_min) / y_range) * ch

    grid = ""
    for i in range(4):
        gy = PAD_T + (i / 3) * ch
        gv = y_max - (i / 3) * y_range
        grid += f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W-PAD_R}" y2="{gy:.1f}" stroke="#1a1a2e" stroke-width="0.5"/>'
        grid += f'<text x="{PAD_L-5}" y="{gy+4:.1f}" fill="#666" font-size="10" text-anchor="end" font-family="monospace">{gv:.1f}</text>'
    points = " ".join(f"{x(i):.1f},{y(vals[i]):.1f}" for i in range(n))
    area_path = f"M {x(0):.1f},{y(vals[0]):.1f} " + " ".join(f"L {x(i):.1f},{y(vals[i]):.1f}" for i in range(1, n))
    area_path += f" L {x(n-1):.1f},{PAD_T+ch} L {x(0):.1f},{PAD_T+ch} Z"
    x_labels = ""
    step = max(1, n // 6)
    for i in range(0, n, step):
        x_labels += f'<text x="{x(i):.1f}" y="{H-10}" fill="#666" font-size="9" text-anchor="middle" font-family="monospace">{data[i]["date"][5:]}</text>'
    return f'''<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="mgrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#6366f1" stop-opacity="0.2"/><stop offset="100%" stop-color="#6366f1" stop-opacity="0"/></linearGradient></defs>
  {grid}
  <path d="{area_path}" fill="url(#mgrad)"/>
  <polyline points="{points}" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linejoin="round"/>
  <circle cx="{x(n-1):.1f}" cy="{y(vals[-1]):.1f}" r="3" fill="#6366f1"/>
  <text x="{x(n-1):.1f}" y="{y(vals[-1])-8:.1f}" fill="#818cf8" font-size="11" text-anchor="middle" font-family="monospace" font-weight="bold">{vals[-1]:.2f}亿</text>
  {x_labels}
  <text x="{PAD_L}" y="{H-1}" fill="#555" font-size="9" font-family="monospace">数据源: 东方财富 | 融资余额趋势 | 近{n}个交易日</text>
</svg>'''


def build_report_html(D):
    q = D.get("quote", {})
    eps = D.get("eps_forecast", {})
    ff = D.get("fund_flow", {})
    margin = D.get("margin", {})
    holders = D.get("holders", [])
    reports = D.get("reports", [])
    dividends = D.get("dividends", [])
    div_yield = D.get("dividend_yield_ttm", {})
    klines = D.get("klines", [])
    fetch_time = D.get("fetch_time", "")
    data_date = D.get("data_date", "")
    name = D.get("name", D.get("code", ""))
    sector = D.get("sector", "")
    prefix = D.get("prefix", "sh" if str(D.get("code", "")).startswith("6") else "sz")
    prefix_upper = prefix.upper()

    margin_daily = margin.get("daily", [])
    margin_rev = list(reversed(margin_daily))
    margin_netbuys = []
    for i in range(1, len(margin_rev)):
        change = margin_rev[i]["rzye"] - margin_rev[i - 1]["rzye"]
        margin_netbuys.append({"date": margin_rev[i]["date"], "net": change, "rzye": margin_rev[i]["rzye"]})
    mb_chart_data = margin_netbuys[-30:] if len(margin_netbuys) >= 30 else margin_netbuys
    mb_20 = margin_netbuys[-20:] if len(margin_netbuys) >= 20 else margin_netbuys
    mb_20_sum = sum(d["net"] for d in mb_20)
    mb_20_up = sum(1 for d in mb_20 if d["net"] > 0)
    mb_20_down = sum(1 for d in mb_20 if d["net"] < 0)

    price = q.get("price", 0)
    pe_ttm = q.get("pe_ttm", 0)
    pb = q.get("pb", 0)
    fwd_pe = eps.get("forward_pe")
    cagr = eps.get("cagr_pct")
    peg = eps.get("peg")
    digest = eps.get("digest_years")
    dy = div_yield.get("yield_pct", 0)
    mcap = q.get("mcap_yi", 0)
    chg_color = color_up_down(q.get("change_pct", 0))

    # ── 实时行情 ──
    realtime_metrics = f"""
      <div class="metric"><span class="metric-label">现价</span><span class="metric-value" style="font-size:18px;color:{chg_color}">¥{price:.2f}</span></div>
      <div class="metric"><span class="metric-label">今开 / 昨收</span><span class="metric-value">¥{q.get('open',0):.2f} / ¥{q.get('last_close',0):.2f}</span></div>
      <div class="metric"><span class="metric-label">最高 / 最低</span><span class="metric-value">¥{q.get('high',0):.2f} / ¥{q.get('low',0):.2f}</span></div>
      <div class="metric"><span class="metric-label">52周最高 / 最低</span><span class="metric-value highlight">¥{q.get('week52_high',0):.2f} / ¥{q.get('week52_low',0):.2f}</span></div>
      <div class="metric"><span class="metric-label">PE(TTM) / PE(静)</span><span class="metric-value highlight">{fmt_num(pe_ttm)}x / {fmt_num(q.get('pe_static',0))}x</span></div>
      <div class="metric"><span class="metric-label">PB(市净率)</span><span class="metric-value highlight">{fmt_num(pb)}x</span></div>
      <div class="metric"><span class="metric-label">总市值 / 流通市值</span><span class="metric-value">¥{mcap:.0f}亿 / ¥{q.get('float_mcap_yi',0):.0f}亿</span></div>
      <div class="metric"><span class="metric-label">换手率 / 振幅</span><span class="metric-value">{fmt_num(q.get('turnover_pct',0))}% / {fmt_num(q.get('amplitude_pct',0))}%</span></div>
      <div class="metric"><span class="metric-label">量比 / 成交额</span><span class="metric-value">{fmt_num(q.get('vol_ratio',0))} / {fmt_wan(q.get('amount_wan',0))}</span></div>"""

    # ── 估值指标 ──
    valuation_metrics = f"""
      <div class="metric"><span class="metric-label">PE(TTM)</span><span class="metric-value highlight">{fmt_num(pe_ttm)}x</span></div>
      <div class="metric"><span class="metric-label">前向PE</span><span class="metric-value highlight">{fmt_num(fwd_pe)}x</span></div>
      <div class="metric"><span class="metric-label">PB</span><span class="metric-value">{fmt_num(pb)}x</span></div>
      <div class="metric"><span class="metric-label">EPS增速CAGR</span><span class="metric-value {'down' if cagr and cagr<0 else 'up'}">{fmt_num(cagr)}%</span></div>
      <div class="metric"><span class="metric-label">PEG</span><span class="metric-value {'neutral' if peg is None else ''}">{fmt_num(peg) if peg else 'N/A(增速为负)'}</span></div>
      <div class="metric"><span class="metric-label">PE消化至30x需</span><span class="metric-value" style="color:#22c55e">{'已低于30x' if digest==0 else f'{digest}年'}</span></div>
      <div class="metric"><span class="metric-label">覆盖机构数</span><span class="metric-value">{eps.get('analyst_count',0)}家</span></div>
      <div class="metric"><span class="metric-label">TTM股息率</span><span class="metric-value highlight">{fmt_num(dy)}%</span></div>
      <div style="margin-top:12px;padding:8px;background:#1a1a2e;border-radius:4px;font-size:12px;color:#94a3b8"><span style="color:#fbbf24">📌 判读：</span>前向PE仅{fmt_num(fwd_pe)}x远低于30x锚点，EPS预期{'下滑' if cagr and cagr<0 else '增长'}，PEG{'不适用(增速为负)' if peg is None else f'={peg}'}</div>"""

    # ── EPS 表 + 公式 ──
    parsed_years = eps.get("parsed_years", [])
    eps_rows = "".join(f"""<tr>
      <td style="text-align:center;font-weight:600;color:#e2e8f0">{y['year']}</td>
      <td style="text-align:center">{y['analyst_count']}家</td>
      <td style="text-align:center;font-family:monospace;color:#fbbf24">{y['avg_eps']:.2f}</td></tr>""" for y in parsed_years)
    eps_formulas = f"""
        <div>📊 <span style="color:#e2e8f0">前向PE</span> = ¥{price:.2f} / {fmt_num(eps.get('eps_current'))} = <span class="highlight">{fmt_num(fwd_pe)}x</span></div>
        <div>📈 <span style="color:#e2e8f0">EPS CAGR</span> = ({fmt_num(eps.get('eps_next'))}/{fmt_num(eps.get('eps_current'))}-1) = <span class="{'down' if cagr and cagr<0 else 'up'}">{fmt_num(cagr)}%</span></div>
        <div>⚖️ <span style="color:#e2e8f0">PEG</span> = {fmt_num(fwd_pe)}x / ({fmt_num(cagr)}×100) = <span class="{'neutral' if peg is None else ''}">{fmt_num(peg) if peg else 'N/A'}</span></div>
        <div>⏱️ <span style="color:#e2e8f0">PE消化至30x</span> = {'已低于30x，无需消化' if digest==0 else f'{digest}年'}</div>"""

    # ── 资金面状态条 ──
    if ff.get("error"):
        ff_status = f'<div style="color:#fbbf24;font-size:12px;margin-bottom:8px">⚠ 主力资金流API(push2his)被网络代理拦截，以下使用<span style="color:#e2e8f0">融资余额日变化</span>作为资金面替代指标</div>'
    else:
        ff_20 = ff.get("recent_20_sum_yi", 0)
        ff_up = ff.get("recent_20_days_up", 0)
        ff_down = ff.get("recent_20_days_down", 0)
        ff_status = f'<div style="color:#94a3b8;font-size:12px;margin-bottom:8px">近20日主力资金净流入: <span style="color:{color_up_down(ff_20)};font-weight:600">{ff_20:+.2f}亿</span> | 净流入{ff_up}日 / 净流出{ff_down}日</div>'

    margin_summary = f"""<div style="margin-top:8px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px">
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">近20日累计</div><div style="color:{color_up_down(mb_20_sum)};font-family:monospace;font-weight:700;font-size:16px">{mb_20_sum/1e8:+.2f}亿</div></div>
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">净流入天数</div><div style="color:#ef4444;font-family:monospace;font-weight:700;font-size:16px">{mb_20_up}日</div></div>
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">净流出天数</div><div style="color:#22c55e;font-family:monospace;font-weight:700;font-size:16px">{mb_20_down}日</div></div>
      </div>"""

    margin_trend_summary = f"""<div style="margin-top:8px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px">
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">最新融资余额</div><div style="color:#818cf8;font-family:monospace;font-weight:700;font-size:16px">¥{margin.get('latest_rzye_yi',0):.2f}亿</div></div>
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">区间变化</div><div style="color:{color_up_down(margin.get('change_yi',0))};font-family:monospace;font-weight:700;font-size:16px">{margin.get('change_yi',0):+.2f}亿</div></div>
        <div style="background:#1a1a2e;padding:8px;border-radius:4px;text-align:center"><div style="color:#64748b">最新融券余额</div><div style="color:#94a3b8;font-family:monospace;font-weight:700;font-size:16px">¥{(margin_daily[0].get('rqye',0)/1e8) if margin_daily else 0:.2f}亿</div></div>
      </div>"""

    # ── 股东户数 ──
    holder_html = '<div style="color:#888;padding:20px;text-align:center">股东户数数据不可用</div>'
    holder_detail_html = '<div style="color:#888;padding:8px">股东户数数据不可用</div>'
    conc_color = "#fbbf24"
    if holders and isinstance(holders, list) and len(holders) > 0:
        h = holders[0]
        holder_num = h.get("holder_num", 0)
        change_ratio = h.get("change_ratio", 0)
        change_num = h.get("change_num", 0)
        concentration = "筹码集中" if change_ratio < -5 else ("筹码分散" if change_ratio > 5 else "筹码稳定")
        conc_color = "#ef4444" if change_ratio < -5 else ("#22c55e" if change_ratio > 5 else "#fbbf24")
        holder_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:8px">
      <div style="background:#0f172a;padding:12px;border-radius:6px;text-align:center"><div style="color:#64748b;font-size:11px">最新股东户数</div><div style="color:#e2e8f0;font-size:20px;font-family:monospace;font-weight:700;margin-top:4px">{holder_num:,}</div></div>
      <div style="background:#0f172a;padding:12px;border-radius:6px;text-align:center"><div style="color:#64748b;font-size:11px">环比变化</div><div style="color:{conc_color};font-size:20px;font-family:monospace;font-weight:700;margin-top:4px">{change_ratio:+.2f}%</div></div>
      <div style="background:#0f172a;padding:12px;border-radius:6px;text-align:center"><div style="color:#64748b;font-size:11px">变化户数</div><div style="color:{conc_color};font-size:20px;font-family:monospace;font-weight:700;margin-top:4px">{change_num:+,}</div></div>
      <div style="background:#0f172a;padding:12px;border-radius:6px;text-align:center"><div style="color:#64748b;font-size:11px">筹码判断</div><div style="color:{conc_color};font-size:20px;font-weight:700;margin-top:4px">{concentration}</div></div>
    </div>"""
        holder_detail_html = f"""<div style="margin-top:12px;padding:10px;background:#1a1a2e;border-radius:4px;font-size:12px;color:#94a3b8;line-height:1.8">
        <div>📋 股东户数环比 <span style="color:{conc_color};font-weight:600">{change_ratio:+.2f}%</span> → 筹码{'集中(主力吸筹)' if change_ratio < -5 else '分散(主力派发)' if change_ratio > 5 else '稳定'}</div>
        <div>💡 户数减少=筹码向大户集中=潜在利好；户数增加=筹码分散=潜在利空</div>
      </div>"""

    # ── 研报表 ──
    def rating_badge(rating):
        c = RATING_COLOR.get(rating, "#888")
        return f'<span style="color:{c};font-size:11px;padding:2px 8px;border:1px solid {c}40;border-radius:3px">{rating or "N/A"}</span>'

    report_rows = "".join(f"""<tr>
      <td style="text-align:center;color:#94a3b8;font-family:monospace;font-size:12px;white-space:nowrap">{r['date']}</td>
      <td style="color:#cbd5e1;font-size:12px">{r['org']}</td>
      <td style="text-align:center">{rating_badge(r.get('rating',''))}</td>
      <td style="color:#e2e8f0;font-size:12px">{r['title'][:55]}{'...' if len(r['title'])>55 else ''}</td></tr>""" for r in reports[:8])

    # ── 分红表 ──
    div_rows = ""
    for dv in dividends[:10]:
        per10 = dv.get("bonus_rmb_per_10", 0) or 0
        per_share = dv.get("bonus_rmb_per_share", 0) or 0
        transfer = dv.get("transfer_ratio", 0) or 0
        bonus = dv.get("bonus_ratio", 0) or 0
        desc_parts = []
        if per10 > 0:
            desc_parts.append(f"派{per10:.1f}元")
        if transfer > 0:
            desc_parts.append(f"转增{transfer:.1f}股")
        if bonus and bonus > 0:
            desc_parts.append(f"送{bonus:.1f}股")
        desc = "+".join(desc_parts) if desc_parts else "—"
        div_rows += f"""<tr>
      <td style="text-align:center;color:#94a3b8;font-family:monospace;font-size:12px">{dv['date']}</td>
      <td style="text-align:center;color:#fbbf24;font-family:monospace">每10股{desc}</td>
      <td style="text-align:center;color:#e2e8f0;font-family:monospace">¥{per_share:.4f}</td>
      <td style="text-align:center;color:#94a3b8;font-size:12px">{dv['plan']}</td></tr>"""

    # ── 综合判断 ──
    if pe_ttm and pe_ttm < 15:
        val_judge, val_color = "显著低估", "#22c55e"
        val_detail = f"PE(TTM)={pe_ttm}x，远低于A股均值；前向PE={fwd_pe}x，PB={pb}x接近净资产。"
    elif pe_ttm and pe_ttm < 25:
        val_judge, val_color = "估值合理", "#fbbf24"
        val_detail = f"PE(TTM)={pe_ttm}x，处于合理区间。"
    else:
        val_judge, val_color = "估值偏高", "#ef4444"
        val_detail = f"PE(TTM)={pe_ttm}x，估值偏高。"
    if dy and dy > 5:
        val_detail += f" TTM股息率{dy}%，高股息特征显著。"
    eps_trend = "下滑" if cagr and cagr < 0 else ("增长" if cagr and cagr > 0 else "持平")
    if cagr and cagr < 0:
        val_detail += f" 注意：机构一致预期EPS呈{eps_trend}趋势(CAGR={cagr}%)，属周期股景气下行特征。"

    margin_trend = "净流出" if mb_20_sum < 0 else "净流入"
    chip_color = "#22c55e" if mb_20_sum < 0 else "#ef4444"
    holder_conc = "集中" if holders and holders[0].get("change_ratio", 0) < -5 else "分散"
    chip_detail = f"近20日融资{margin_trend}¥{abs(mb_20_sum)/1e8:.2f}亿，融资余额趋势{'下行' if mb_20_sum < 0 else '上行'}。"
    if holders and isinstance(holders, list) and len(holders) > 0:
        cr = holders[0].get("change_ratio", 0)
        chip_detail += f" 股东户数环比{cr:+.2f}%，筹码{'集中' if cr < -5 else '分散'}。"

    if pe_ttm and pe_ttm < 15 and dy and dy > 5:
        hold_judge, hold_color = "可持有/逢低布局", "#22c55e"
        hold_detail = "低估值+高股息+周期底部特征，适合价值型投资者中长期持有。"
        if cagr and cagr < 0:
            hold_detail += " 但需警惕盈利下滑风险，建议控制仓位。"
    elif pe_ttm and pe_ttm < 25:
        hold_judge, hold_color = "观望为主", "#fbbf24"
        hold_detail = "估值合理但缺乏安全边际，建议等待更好的入场时机。"
    else:
        hold_judge, hold_color = "谨慎规避", "#ef4444"
        hold_detail = "估值偏高，性价比不足。"

    judgment = f"""<div class="judgment-box">
    <div class="card-title" style="border-bottom:2px solid #1e293b">⚖️ 综合判断 <span class="badge" style="background:#7c2d12;color:#fbbf24">非投资建议</span></div>
    <div class="judge-item"><div class="judge-label"><span class="judge-dot" style="background:{val_color}"></span>贵不贵</div><div class="judge-content"><div class="judge-verdict" style="color:{val_color}">{val_judge}</div><div class="judge-detail">{val_detail}</div></div></div>
    <div class="judge-item"><div class="judge-label"><span class="judge-dot" style="background:{chip_color}"></span>筹码稳不稳</div><div class="judge-content"><div class="judge-verdict" style="color:{chip_color}">筹码{holder_conc}，杠杆资金{margin_trend}</div><div class="judge-detail">{chip_detail}</div></div></div>
    <div class="judge-item"><div class="judge-label"><span class="judge-dot" style="background:{hold_color}"></span>能不能拿</div><div class="judge-content"><div class="judge-verdict" style="color:{hold_color}">{hold_judge}</div><div class="judge-detail">{hold_detail}</div></div></div>
  </div>"""

    price_svg = gen_price_svg(klines)
    margin_bar_svg = gen_margin_bar_svg(mb_chart_data)
    margin_trend_svg = gen_margin_trend_svg(margin_rev)

    # ── 分享卡片数据（供前端 canvas 现画手机版图片）──
    holder_change = holders[0].get("change_ratio", 0) if (holders and isinstance(holders, list) and len(holders) > 0) else None
    share_data = {
        "name": name, "code": D.get("code", ""), "prefix": prefix_upper, "sector": sector,
        "data_date": data_date,
        "price": f"¥{price:.2f}", "price_color": chg_color,
        "change_amt": f"{q.get('change_amt', 0):+.2f}", "change_pct": f"{q.get('change_pct', 0):+.2f}%",
        "pe_ttm": fmt_num(pe_ttm), "pb": fmt_num(pb),
        "mcap": f"¥{mcap:.0f}亿", "dy": fmt_num(dy),
        "fwd_pe": fmt_num(fwd_pe), "peg": fmt_num(peg) if peg is not None else "N/A",
        "val_judge": val_judge, "val_color": val_color,
        "chip_judge": f"筹码{holder_conc}·杠杆资金{margin_trend}", "chip_color": chip_color,
        "hold_judge": hold_judge, "hold_color": hold_color,
        "holder_change": holder_change,
        "data_source": "腾讯财经 / 东方财富 / 同花顺",
    }

    tokens = {
        "NAME": name, "PREFIX_UPPER": prefix_upper, "CODE": D.get("code", ""),
        "SECTOR": sector, "DATA_DATE": data_date,
        "PRICE": f"¥{price:.2f}", "PRICE_COLOR": chg_color,
        "CHANGE_AMT": f"{q.get('change_amt',0):+.2f}", "CHANGE_PCT": f"{q.get('change_pct',0):+.2f}",
        "REALTIME_METRICS": realtime_metrics, "VALUATION_METRICS": valuation_metrics,
        "PRICE_SVG": price_svg, "PRICE_SVG_COUNT": str(len(klines) if isinstance(klines, list) else 0),
        "EPS_TABLE": eps_rows, "EPS_FORMULAS": eps_formulas,
        "FUND_FLOW_STATUS": ff_status, "MARGIN_BAR_SVG": margin_bar_svg, "MARGIN_SUMMARY": margin_summary,
        "MARGIN_TREND_SVG": margin_trend_svg, "MARGIN_TREND_COUNT": str(margin.get("count", 0)),
        "MARGIN_TREND_SUMMARY": margin_trend_summary,
        "HOLDER_HTML": holder_html, "HOLDER_DETAIL": holder_detail_html,
        "REPORT_TABLE": report_rows, "REPORT_COUNT": str(len(reports)),
        "DIVIDEND_TABLE": div_rows, "DIVIDEND_COUNT": str(len(dividends)),
        "DIVIDEND_YIELD": fmt_num(dy),
        "JUDGMENT": judgment,
        "SHARE_DATA": json.dumps(share_data, ensure_ascii=False),
        "FETCH_TIME": fetch_time, "GEN_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    html = _load_template()
    for k, v in tokens.items():
        html = html.replace(f"[[{k}]]", str(v))
    # 安全校验：不应残留未替换的 token
    import re
    leftover = re.findall(r"\[\[[A-Z_]+\]\]", html)
    if leftover:
        print(f"  ⚠️ 报告模板存在未替换 token: {set(leftover)}")
    return html
