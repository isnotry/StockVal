"""东方财富数据源：融资融券 / 股东户数 / 研报 / 分红送转。

统一走 datacenter-web 接口 + reportapi，并带全局节流避免被风控。
"""
import time
import random
import urllib.parse

import requests

from ..config import UA, EM_MIN_INTERVAL

DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
REPORT_API = "https://reportapi.eastmoney.com/report/list"

# ── 全局节流 + 会话复用 ──
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": UA})
_last_call = [0.0]


def em_get(url, params=None, headers=None, timeout=15, **kwargs):
    wait = EM_MIN_INTERVAL - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.05, 0.3))
    try:
        return _SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _last_call[0] = time.time()


def datacenter(report_name, columns="ALL", filter_str="", page_size=50,
               sort_columns="", sort_types="-1"):
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = em_get(DATACENTER_URL, params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


def fetch_margin(CODE):
    """融资融券明细 + 用日变化(净买入)作为资金面替代指标。"""
    margin_data = []
    try:
        data = datacenter("RPTA_WEB_RZRQ_GGMX", filter_str=f'(SCODE="{CODE}")',
                           page_size=60, sort_columns="DATE", sort_types="-1")
        for row in data:
            margin_data.append({
                "date": str(row.get("DATE", ""))[:10],
                "rzye": row.get("RZYE", 0), "rzmre": row.get("RZMRE", 0),
                "rqye": row.get("RQYE", 0), "rzrqye": row.get("RZRQYE", 0),
                "rzche": row.get("RZCHE", 0) or 0,
            })
        result = {
            "daily": margin_data,
            "latest_rzye_yi": round(margin_data[0]["rzye"] / 1e8, 2) if margin_data else 0,
            "count": len(margin_data),
        }
        if len(margin_data) >= 2:
            first_rzye = margin_data[-1]["rzye"]
            last_rzye = margin_data[0]["rzye"]
            result["change_yi"] = round((last_rzye - first_rzye) / 1e8, 2)
        # 融资净买入（日变化）作为资金面替代
        netbuy = []
        for d in margin_data:
            rzmre = d.get("rzmre", 0) or 0
            rzche = d.get("rzche", 0) or 0
            net = rzmre - rzche
            netbuy.append({"date": d["date"], "net_buy": net, "rzye": d["rzye"]})
        netbuy.reverse()
        result["netbuy_daily"] = netbuy
        recent_20 = netbuy[-20:] if len(netbuy) >= 20 else netbuy
        result["recent_20_netbuy_yi"] = round(sum(d["net_buy"] for d in recent_20) / 1e8, 2)
        return result
    except Exception as e:
        return {"error": str(e)}


def fetch_holders(CODE):
    holder_data = []
    try:
        data = datacenter("RPT_HOLDERNUMLATEST", filter_str=f'(SECURITY_CODE="{CODE}")',
                           page_size=10, sort_columns="END_DATE", sort_types="-1")
        for row in data:
            holder_data.append({
                "date": str(row.get("END_DATE", ""))[:10],
                "holder_num": row.get("HOLDER_NUM", 0),
                "change_num": row.get("HOLDER_NUM_CHANGE", 0),
                "change_ratio": row.get("HOLDER_NUM_RATIO", 0),
                "avg_shares": row.get("AVG_FREE_SHARES", 0),
            })
        return holder_data
    except Exception as e:
        return {"error": str(e)}


def fetch_reports(CODE, limit=8):
    reports_list = []
    try:
        params = {
            "industryCode": "*", "pageSize": "100", "industry": "*", "rating": "*",
            "ratingChange": "*", "beginTime": "2000-01-01", "endTime": "2030-01-01",
            "pageNo": "1", "fields": "", "qType": "0", "orgCode": "", "code": CODE,
            "rcode": "", "p": "1", "pageNum": "1", "pageNumber": "1",
        }
        r = em_get(REPORT_API, params=params,
                   headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)
        d = r.json()
        rows = d.get("data") or []
        for rec in rows[:limit]:
            reports_list.append({
                "date": str(rec.get("publishDate", ""))[:10],
                "org": rec.get("orgSName", ""),
                "title": rec.get("title", ""),
                "rating": rec.get("emRatingName", ""),
                "eps_this_year": rec.get("predictThisYearEps"),
                "eps_next_year": rec.get("predictNextYearEps"),
                "eps_year3": rec.get("predictNextTwoYearEps"),
            })
        return reports_list
    except Exception as e:
        return {"error": str(e)}


def fetch_dividends(CODE):
    """分红送转历史。注意：东财 PRETAX_BONUS_RMB 字段实际是『每10股派息』，需 /10。"""
    from datetime import datetime, timedelta
    dividend_data = []
    try:
        data = datacenter("RPT_SHAREBONUS_DET", filter_str=f'(SECURITY_CODE="{CODE}")',
                           page_size=20, sort_columns="EX_DIVIDEND_DATE", sort_types="-1")
        for row in data:
            raw_bonus = row.get("PRETAX_BONUS_RMB", 0) or 0  # 每10股派息(税前)
            dividend_data.append({
                "date": str(row.get("EX_DIVIDEND_DATE", ""))[:10],
                "bonus_rmb_per_share": round(raw_bonus / 10, 4),
                "bonus_rmb_per_10": raw_bonus,
                "transfer_ratio": row.get("TRANSFER_RATIO", 0),
                "bonus_ratio": row.get("BONUS_RATIO", 0),
                "plan": row.get("ASSIGN_PROGRESS", ""),
            })
        cutoff = datetime.now() - timedelta(days=365)
        ttm_total = 0
        period_count = 0
        for dv in dividend_data:
            ex_date = dv.get("date", "")
            if not ex_date:
                continue
            try:
                if datetime.strptime(ex_date[:10], "%Y-%m-%d") >= cutoff:
                    ttm_total += dv.get("bonus_rmb_per_share", 0) or 0
                    period_count += 1
            except ValueError:
                pass
        return {"rows": dividend_data, "ttm_total": ttm_total, "period_count": period_count}
    except Exception as e:
        return {"error": str(e)}
