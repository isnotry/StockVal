"""抓取编排：把各数据源拼成统一的 result dict，并落盘到缓存。

result 结构（与模板渲染所需的字段一致）：
  code, name, sector, prefix, fetch_time, data_date
  quote{}  eps_forecast{}  fund_flow{}  margin{}  holders[]
  reports[]  dividends{rows,ttm_total,period_count}  dividend_yield_ttm{}
  klines[]
"""
import math
from datetime import datetime

from . import tencent, eastmoney, eps as eps_mod, funds
from ..cache import save, is_fresh
from ..config import DEFAULT_FUND_FALLBACK


def _safe_date(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.min


def fetch_stock(code, name="", sector="", force=False, fallback=DEFAULT_FUND_FALLBACK):
    """抓取单只股票全维数据。force=True 忽略缓存直接重抓。"""
    if not force and is_fresh(code):
        from ..cache import load
        cached = load(code)
        if cached:
            print(f"  ✅ {cached.get('name', code)}({code}) 缓存新鲜(<24h)，跳过抓取")
            return cached

    print(f"\n{'=' * 60}\n>>> 抓取 {name or code}({code}) [{sector}]\n{'=' * 60}")
    result = {
        "code": code, "name": name, "sector": sector,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": datetime.now().strftime("%Y-%m-%d"),
    }

    # 1) 腾讯实时行情
    print("[1/7] 腾讯财经实时行情...")
    quote = tencent.fetch_quote(code)
    if "error" in quote:
        print(f"  行情异常: {quote['error']}")
    else:
        result["prefix"] = quote.get("prefix", "sh" if code.startswith("6") else "sz")
        result["name"] = quote.get("name") or name
        print(f"  {quote.get('name')} 现价={quote.get('price')} "
              f"PE(TTM)={quote.get('pe_ttm')} PB={quote.get('pb')} 市值={quote.get('mcap_yi')}亿")
    result["quote"] = quote

    # 2) 同花顺机构一致预期 EPS
    print("[2/7] 同花顺机构一致预期EPS...")
    eps_data = eps_mod.fetch_eps(code)
    price = quote.get("price", 0) if "error" not in quote else 0
    if eps_data.get("parsed_years") and len(eps_data["parsed_years"]) >= 2 and price > 0:
        eps_cur = eps_data.get("eps_current", 0)
        eps_next = eps_data.get("eps_next", 0)
        if eps_cur > 0:
            forward_pe = price / eps_cur
            cagr = (eps_next / eps_cur - 1) if eps_next > 0 else 0
            peg = forward_pe / (cagr * 100) if cagr > 0 else None
            digest = 0 if forward_pe <= 30 else math.log(forward_pe / 30) / math.log(1 + cagr) if cagr > 0 else None
            eps_data["forward_pe"] = round(forward_pe, 2)
            eps_data["cagr_pct"] = round(cagr * 100, 1)
            eps_data["peg"] = round(peg, 2) if peg else None
            eps_data["digest_years"] = round(digest, 1) if digest is not None else None
    print(f"  机构数={eps_data.get('analyst_count',0)} 前向PE={eps_data.get('forward_pe')} "
          f"PEG={eps_data.get('peg')} 消化={eps_data.get('digest_years')}年")
    result["eps_forecast"] = eps_data

    # 3) 主力资金流（尝试 push2his，失败按 fallback 降级）
    print("[3/7] 东财主力资金流(尝试 push2his)...")
    ff = funds.fetch_fund_flow(code, fallback=fallback)
    if ff.get("error"):
        print(f"  不可用(预期): 将用融资净买入替代")
    else:
        print(f"  共{len(ff.get('daily', []))}日 近20日主力净流入={ff.get('recent_20_sum_yi')}亿")
    result["fund_flow"] = ff

    # 4) 融资融券 + 净买入替代
    print("[4/7] 融资融券明细...")
    margin = eastmoney.fetch_margin(code)
    if "error" in margin:
        print(f"  融资融券异常: {margin['error']}")
    else:
        print(f"  {margin.get('count')}条 最新融资余额={margin.get('latest_rzye_yi')}亿")
    result["margin"] = margin

    # 5) 股东户数
    print("[5/7] 股东户数变化...")
    holders = eastmoney.fetch_holders(code)
    if isinstance(holders, dict) and "error" in holders:
        print(f"  股东户数异常: {holders['error']}")
        holders = []
    result["holders"] = holders
    if holders:
        print(f"  {len(holders)}期 最新股东数={holders[0]['holder_num']} 环比={holders[0]['change_ratio']}%")

    # 6) 研报
    print("[6/7] 东财研报列表...")
    reports = eastmoney.fetch_reports(code)
    if isinstance(reports, dict) and "error" in reports:
        print(f"  研报异常: {reports['error']}")
        reports = []
    result["reports"] = reports
    print(f"  取最近{len(reports)}篇")

    # 7) 分红送转 + TTM 股息率
    print("[7/7] 分红送转历史...")
    div = eastmoney.fetch_dividends(code)
    if "error" in div:
        print(f"  分红异常: {div['error']}")
        result["dividends"] = []
        result["dividend_yield_ttm"] = {"yield_pct": 0, "ttm_dividend_per_share": 0, "period_count": 0}
    else:
        result["dividends"] = div["rows"]
        ttm_yield = round(div["ttm_total"] / price * 100, 2) if price > 0 else 0
        result["dividend_yield_ttm"] = {
            "ttm_dividend_per_share": round(div["ttm_total"], 4),
            "yield_pct": ttm_yield,
            "period_count": div["period_count"],
        }
        print(f"  {len(div['rows'])}条 TTM股息率={ttm_yield}%")

    # 8) 腾讯K线
    print("[8/8] 腾讯K线数据...")
    klines = tencent.fetch_kline(code)
    if isinstance(klines, dict) and "error" in klines:
        print(f"  K线异常: {klines['error']}")
        klines = []
    result["klines"] = klines
    print(f"  {len(klines)}根日K线")

    save(code, result)
    print(f"  ✅ 已保存 {code}_data.json")
    return result
