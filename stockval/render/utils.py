"""渲染辅助：颜色与金额/数字格式化（涨红跌绿，¥ + 亿/万）。"""


def color_up_down(val):
    if val is None:
        return "#888"
    return "#ef4444" if val >= 0 else "#22c55e"


def fmt_yi(val):
    if val is None:
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 10000:
        return f"¥{val / 10000:.2f}万亿"
    elif abs_val >= 1:
        return f"¥{val:.2f}亿"
    else:
        return f"¥{val * 10000:.0f}万"


def fmt_wan(val):
    if val is None:
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 10000:
        return f"¥{val / 10000:.2f}亿"
    else:
        return f"¥{val:.0f}万"


def fmt_num(val, decimals=2):
    if val is None or val == "N/A":
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except Exception:
        return str(val)
