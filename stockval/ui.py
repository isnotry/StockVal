"""两层交互式界面（顶层主菜单 + remove 二级确认流程）。

设计：
- 顶层主菜单：列出全部指令与功能介绍，↑/↓/j/k 移动光标，Enter 进入对应流程，q 退出。
  进入后执行完会回到主菜单，形成真正的两层 shell。
- remove 接入「选股票 → 二次确认」的两层流程：先在列表中选中股票，再 y/N 确认才删除。
- 其余指令从菜单进入后按默认（全部）执行，保持单行命令的语义一致。
- 非 TTY（管道/重定向）时自动降级为打印指令清单，兼容脚本与 CI。

复用 menu 模块的底层交互原语（_get_key / move_selection / render_list_plain），
保持与 list 菜单一致的终端行为（超时降级、EOF 降级、Ctrl-C 退出）。
"""
import shutil
import sys
from types import SimpleNamespace

from . import registry, cache
from . import menu
from .render import index as index_mod
from .cli import (
    cmd_add, cmd_remove, cmd_list, cmd_fetch, cmd_report,
    cmd_build, cmd_refresh, cmd_open, cmd_init,
)


# 主菜单指令清单：key, 标题, 功能介绍
COMMANDS = [
    ("add",     "添加股票",   "解析代码/名称并抓取+渲染"),
    ("remove",  "移除股票",   "选中股票后二次确认再删除（两层）"),
    ("list",    "列出股票",   "交互菜单，Enter 直接打开报告"),
    ("fetch",   "抓取数据",   "默认全部，可指定代码"),
    ("report",  "渲染报告",   "用缓存渲染报告，不联网"),
    ("refresh", "一键更新",   "抓取+渲染+重建导航（全部）"),
    ("build",   "重建导航",   "仅重建 index.html"),
    ("open",    "打开导航页", "在默认浏览器打开 index.html"),
    ("init",    "初始化",     "迁移已有报告 / 初始化空项目"),
]


def _clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def _read_line(prompt):
    """在 cooked 模式下读取一行（菜单交互中临时用于输入代码/名称）。"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def _dispatch(name):
    """从主菜单进入某条指令。remove 走二级确认流程，其余按默认（全部）执行。"""
    if name == "remove":
        run_remove_flow()
        return
    if name == "add":
        token = _read_line("输入代码或名称（可加空格跟行业）: ").strip()
        if not token:
            print("  已取消")
            return
        parts = token.split(None, 1)
        code_token = parts[0]
        sector = parts[1] if len(parts) > 1 else ""
        cmd_add(SimpleNamespace(token=code_token, sector=sector))
        return
    if name == "init":
        src = _read_line("源目录（留空用默认）: ").strip()
        cmd_init(SimpleNamespace(from_path=src or None))
        return
    if name == "list":
        cmd_list(SimpleNamespace(plain=False, dry_run=False))
        return
    if name == "fetch":
        cmd_fetch(SimpleNamespace(code=None, force=False))
        return
    if name == "report":
        cmd_report(SimpleNamespace(code=None))
        return
    if name == "refresh":
        cmd_refresh(SimpleNamespace(code=None))
        return
    if name == "build":
        cmd_build(SimpleNamespace())
        return
    if name == "open":
        cmd_open(SimpleNamespace(dry_run=False))
        return


def pick_stock(cards, title, hint):
    """通用股票选择器：返回选中的 card 或 None（q / 超时降级）。"""
    if not cards:
        print("注册表为空，先用 add 添加")
        return None
    if not sys.stdin.isatty():
        menu.render_list_plain(cards)
        return None
    sel = 0
    n = len(cards)

    def draw():
        _clear()
        cols = shutil.get_terminal_size((80, 24)).columns
        bar = "─" * min(cols, 64)
        lines = [f" {title}", f" {hint}", bar]
        for i, c in enumerate(cards, 1):
            if i - 1 == sel:
                lines.append(f" \x1b[7m▶ {i}. {c['name']} {c['code']}  · {c.get('sector', '')}\x1b[0m")
            else:
                lines.append(f"   {i}. {c['name']} {c['code']}  · {c.get('sector', '')}")
        lines.append(bar)
        lines.append(f" 共 {n} 只 · 当前: {cards[sel]['name']}")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    draw()
    idle = 0
    while True:
        k = menu._get_key()
        if k is None:  # 超时无输入
            idle += 1
            if idle >= 5:  # 连续 5 秒无人操作 → 降级纯文本
                _clear()
                print(" 未检测到交互输入，已降级为纯文本列表：\n")
                menu.render_list_plain(cards)
                return None
            continue
        if k == "\x04":  # EOF
            _clear()
            menu.render_list_plain(cards)
            return None
        idle = 0
        if k in ("\x1b[A", "\x1b[B", "k", "j"):
            sel = menu.move_selection(sel, n, k)
            draw()
        elif k in ("\r", "\n", " "):  # Enter / 空格 选中
            return cards[sel]
        elif k in ("q", "Q", "\x03"):  # q / Ctrl-C
            return None


def run_remove_flow():
    """remove 的二级流程：股票列表 → 选中 → y/N 二次确认 → 执行删除。"""
    stocks = registry.load()
    if not stocks:
        print("注册表为空，无股票可移除")
        return
    cards = []
    for s in stocks:
        D = cache.load(s["code"]) or {}
        pe = D.get("quote", {}).get("pe_ttm", 0)
        cards.append({
            "code": s["code"],
            "name": s["name"],
            "sector": s.get("sector", ""),
            "_pe": pe if pe else float("inf"),
        })
    cards.sort(key=lambda c: c["_pe"])

    sel = pick_stock(cards, "移除股票 · 选择", "Enter 选中 → 二次确认 · q 退出")
    if not sel:
        _clear()
        print(" 已取消")
        return

    code = sel["code"]
    name = sel["name"]
    _clear()
    ans = _read_line(
        f"确认移除 {name}({code}) 及其报告？此操作不可恢复 [y/N]: "
    ).strip().lower()
    if ans in ("y", "yes"):
        registry.remove(code)
        cache.delete(code)
        index_html = index_mod.build_index()
        if index_html:
            cache.index_path().write_text(index_html, encoding="utf-8")
            print(f"✅ 已移除 {name}({code}) 并重建导航页")
        else:
            print(f"✅ 已移除 {name}({code})")
    else:
        print(" 已取消，未做任何改动")


def run_main_menu():
    """顶层主菜单：列出全部指令与功能介绍，↑/↓/j/k 移动，Enter 进入，q 退出。"""
    if not sys.stdin.isatty():
        # 非交互：打印清单，兼容脚本 / CI / 管道
        print("StockVal 指令一览：")
        for key, title, desc in COMMANDS:
            print(f"  {key:<8} {title} — {desc}")
        print("\n直接运行 `stockval <指令> [参数]` 可执行对应命令；")
        print("在交互终端运行 `stockval`（无参数）可进入两层菜单。")
        return

    sel = 0
    n = len(COMMANDS)

    def draw():
        _clear()
        cols = shutil.get_terminal_size((80, 24)).columns
        bar = "─" * min(cols, 64)
        lines = [
            " StockVal · A股估值体检",
            " ↑/↓ 或 j/k 移动 · Enter 进入指令 · q 退出",
            bar,
        ]
        for i, (key, title, desc) in enumerate(COMMANDS, 1):
            if i - 1 == sel:
                lines.append(f" \x1b[7m▶ {i}. {key:<8} {title} — {desc}\x1b[0m")
            else:
                lines.append(f"   {i}. {key:<8} {title} — {desc}")
        lines.append(bar)
        lines.append(f" 共 {n} 条指令 · 当前: {COMMANDS[sel][0]}")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    draw()
    idle = 0
    while True:
        k = menu._get_key()
        if k is None:  # 超时无输入
            idle += 1
            if idle >= 5:
                _clear()
                print(" 未检测到交互输入，已退出菜单")
                return
            continue
        if k == "\x04":  # EOF
            _clear()
            return
        idle = 0
        if k in ("\x1b[A", "\x1b[B", "k", "j"):
            sel = menu.move_selection(sel, n, k)
            draw()
        elif k in ("\r", "\n", " "):  # Enter / 空格 进入指令
            name = COMMANDS[sel][0]
            _clear()
            _dispatch(name)
            # 指令执行完 → 等待任意键，回到主菜单
            print("\n— 按任意键返回主菜单 —")
            while True:
                kk = menu._get_key()
                if kk == "\x04":
                    _clear()
                    return
                if kk is not None:
                    break
            _clear()
            draw()
            idle = 0
        elif k in ("q", "Q", "\x03"):  # q / Ctrl-C
            _clear()
            print(" 已退出")
            return
