"""主力资金流：尝试东财 push2his，失败按 fallback 策略处理。"""
import json
import urllib.request
import urllib.parse

from ..config import UA, DEFAULT_FUND_FALLBACK


def fetch_fund_flow(CODE, fallback=DEFAULT_FUND_FALLBACK):
    """尝试抓取 push2his 主力资金流日线。

    - 成功：返回 {daily:[...], recent_20_sum_yi, ...}
    - 失败且 fallback="margin"：返回 {error, daily:[], source:"...不可用(将用融资净买入替代)"}
      （资金面改由 eastmoney.fetch_margin 的净买入替代）
    - 失败且 fallback="strict"：直接抛错，不降级
    """
    market_code = 1 if CODE.startswith("6") else 0
    ff_url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    ff_params = {
        "secid": f"{market_code}.{CODE}", "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "lmt": "120",
    }
    full_url = f"{ff_url}?{urllib.parse.urlencode(ff_params)}"
    req = urllib.request.Request(full_url)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://quote.eastmoney.com/")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        ff_data = json.loads(resp.read().decode("utf-8"))
        klines = ff_data.get("data", {}).get("klines", [])
        fund_flow = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 7:
                fund_flow.append({
                    "date": parts[0],
                    "main_net": float(parts[1]) if parts[1] != "-" else 0,
                    "small_net": float(parts[2]) if parts[2] != "-" else 0,
                    "mid_net": float(parts[3]) if parts[3] != "-" else 0,
                    "large_net": float(parts[4]) if parts[4] != "-" else 0,
                    "super_net": float(parts[5]) if parts[5] != "-" else 0,
                })
        recent_20 = fund_flow[-20:] if len(fund_flow) >= 20 else fund_flow
        total_main_20 = sum(d["main_net"] for d in recent_20)
        return {
            "daily": fund_flow,
            "recent_20_sum_yi": round(total_main_20 / 1e8, 2),
            "recent_20_count": len(recent_20),
            "recent_20_days_up": sum(1 for d in recent_20 if d["main_net"] > 0),
            "recent_20_days_down": sum(1 for d in recent_20 if d["main_net"] < 0),
            "source": "东方财富 push2his",
        }
    except Exception as e:
        if fallback == "strict":
            raise
        return {
            "error": str(e), "daily": [],
            "source": "东方财富 push2his (不可用，已用融资净买入替代)",
        }
