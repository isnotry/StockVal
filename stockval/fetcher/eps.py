"""同花顺机构一致预期 EPS（basic.10jqka.com.cn 的 worth 页面表格）。

只依赖标准库：表格用 html.parser 自己解析，不引入 pandas / lxml，
以免为读一张表背上几十 MB 的依赖。
"""
import requests
from html.parser import HTMLParser

from ..config import UA

_CELL_TAGS = ("td", "th")
_YEAR_TOKENS = ("2024", "2025", "2026", "2027", "2028", "2029")


class _TableCollector(HTMLParser):
    """把页面里的 <table> 收集成 `tables[i][行][列] = 单元格文本`。

    支持嵌套表格：进出 <table> 用深度计数，只有在表格内部才开始收单元格。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self._depth = 0
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
            self._depth += 1
        elif self._depth and tag == "tr":
            if self.tables:
                self._row = []
        elif self._depth and tag in _CELL_TAGS and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._depth:
            self._depth -= 1
        elif tag in _CELL_TAGS and self._cell is not None:
            if self._row is not None:
                self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self.tables:
                self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _collect_tables(html):
    parser = _TableCollector()
    parser.feed(html)
    parser.close()
    return parser.tables


def _as_float(v):
    """转成 float，失败返回 None。'nan' 之类也走 float()，与原先 pandas 的行为一致。"""
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_eps_table(tables):
    """找出含「每股收益/均值」的表，解析出各年度的机构家数与一致预期 EPS。"""
    for rows in tables:
        if not rows:
            continue
        cols = rows[0]
        if not any("每股收益" in c or "均值" in c for c in cols):
            continue
        parsed_years = []
        analyst_count = 0
        for row_vals in rows[1:]:
            first_val = row_vals[0].strip() if row_vals else ""
            if not first_val or first_val == "nan":
                continue
            if not any(y in first_val for y in _YEAR_TOKENS):
                continue
            nums = []
            for v in row_vals[1:]:
                f = _as_float(v)
                if f is not None:
                    nums.append(f)
            if len(nums) >= 2:
                # nums = [机构家数, 预测区间/最大值, 均值, ...]
                ac = int(nums[0]) if 0 < nums[0] < 1000 else 0
                avg_eps = nums[2] if len(nums) >= 3 else nums[1]
                parsed_years.append({"year": first_val, "analyst_count": ac, "avg_eps": avg_eps})
                if ac > analyst_count:
                    analyst_count = ac
        return parsed_years, analyst_count
    return [], 0


def fetch_eps(CODE):
    eps_data = {"years": [], "analyst_count": 0, "forward_pe": None, "cagr_pct": None,
                "peg": None, "digest_years": None, "error": None}
    try:
        url = f"https://basic.10jqka.com.cn/new/{CODE}/worth.html"
        headers = {"User-Agent": UA, "Referer": "https://basic.10jqka.com.cn/"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "gbk"
        parsed_years, analyst_count = _parse_eps_table(_collect_tables(r.text))
        eps_data["parsed_years"] = parsed_years
        eps_data["analyst_count"] = analyst_count
        if len(parsed_years) >= 2 and parsed_years[0]["avg_eps"] > 0:
            # forward_pe / cagr / peg 依赖现价，由 fetcher.core 回填
            eps_data["eps_current"] = parsed_years[0]["avg_eps"]
            eps_data["eps_next"] = parsed_years[1]["avg_eps"]
    except Exception as e:
        eps_data["error"] = str(e)
    return eps_data
