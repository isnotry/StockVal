"""腾讯财经数据源：实时行情 + 前复权日K线。"""
import urllib.request

from ..config import UA


def _prefix(CODE):
    if CODE.startswith(("6", "9")):
        return "sh"
    if CODE.startswith("8"):
        return "bj"
    return "sz"


def fetch_quote(CODE):
    """腾讯实时行情 qt.gtimg.cn。返回字段与字段索引对应原脚本。"""
    prefix = _prefix(CODE)
    try:
        url = f"https://qt.gtimg.cn/q={prefix}{CODE}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode("gbk")
        vals = raw.split('"')[1].split("~")
        return {
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "last_close": float(vals[4]) if vals[4] else 0,
            "open": float(vals[5]) if vals[5] else 0,
            "change_amt": float(vals[31]) if vals[31] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "high": float(vals[33]) if vals[33] else 0,
            "low": float(vals[34]) if vals[34] else 0,
            "amount_wan": float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "amplitude_pct": float(vals[43]) if vals[43] else 0,
            "mcap_yi": float(vals[44]) if vals[44] else 0,
            "float_mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb": float(vals[46]) if vals[46] else 0,
            "limit_up": float(vals[47]) if vals[47] else 0,
            "limit_down": float(vals[48]) if vals[48] else 0,
            "vol_ratio": float(vals[49]) if vals[49] else 0,
            "pe_static": float(vals[52]) if vals[52] else 0,
            "week52_high": float(vals[67]) if vals[67] else 0,
            "week52_low": float(vals[68]) if vals[68] else 0,
            "prefix": prefix, "prefix_upper": prefix.upper(),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_kline(CODE, count=80):
    prefix = _prefix(CODE)
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{CODE},day,,,{count},qfq"
        import requests
        from ..config import UA as U
        r = requests.get(url, headers={"User-Agent": U}, timeout=10)
        d = r.json()
        raw = d.get("data", {}).get(f"{prefix}{CODE}", {}).get("qfqday") or \
              d.get("data", {}).get(f"{prefix}{CODE}", {}).get("day", [])
        kline_list = []
        for kl in raw:
            kline_list.append({
                "date": kl[0], "open": round(float(kl[1]), 2), "close": round(float(kl[2]), 2),
                "high": round(float(kl[3]), 2), "low": round(float(kl[4]), 2),
                "vol": float(kl[5]) if len(kl) > 5 else 0,
            })
        return kline_list
    except Exception as e:
        return {"error": str(e)}
