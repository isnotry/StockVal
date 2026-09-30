"""交互式选择菜单 + 跨平台打开报告。

设计要点：
- `move_selection` 为纯函数，单独可测（不依赖终端）。
- `run_menu` 仅在 TTY 下进入全屏交互；非 TTY（管道/重定向）自动降级为纯文本列表。
- `open_report` 跨平台（macOS=open / linux=xdg-open / win=startfile），dry_run 模式只打印路径不真正打开。
"""
import os
import select
import shutil
import subprocess
import sys


def move_selection(sel, n, key):
    """纯函数：根据按键返回新的光标位置（环绕循环）。

    key 支持：上=ESC[A 或 k；下=ESC[B 或 j；其余键原样返回。
    """
    if n <= 0:
        return 0
    if key in ("\x1b[A", "k"):
        return (sel - 1) % n
    if key in ("\x1b[B", "j"):
        return (sel + 1) % n
    return sel


def open_report(path):
    """跨平台用默认程序打开本地 HTML 文件。"""
    path = os.path.abspath(path)
    plat = sys.platform
    try:
        if plat == "darwin":
            subprocess.run(["open", path], check=False)
        elif plat.startswith("linux"):
            subprocess.run(["xdg-open", path], check=False)
        elif plat == "win32":
            os.startfile(path)  # noqa: F821 (windows only)
        else:
            print(f" 未支持的平台，请手动打开: {path}")
    except Exception as e:  # 打开失败不应崩掉菜单
        print(f" 打开失败: {e}\n 路径: {path}")


def render_list_plain(stocks):
    print(f"注册表共 {len(stocks)} 只：")
    for s in stocks:
        print(f"  {s['code']}  {s['name']}  · {s.get('sector', '')}")


def _get_key():
    """读取单个按键（支持箭头转义序列）。

    返回：
      None  → 超时（1s 内无输入，调用方用于判定无人值守）
      '\\x04' → EOF（管道关闭，调用方降级纯文本）
    非 TTY 环境直接读一行首字符兜底。
    """
    if not sys.stdin.isatty():
        data = sys.stdin.read(1)
        return data if data else "\x04"
    # 延迟导入，避免在非 posix 平台模块加载即报错
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # select 超时保护：避免无人值守时永久阻塞
        r, _, _ = select.select([fd], [], [], 1.0)
        if not r:
            return None
        ch = sys.stdin.read(1)
        if not ch:  # EOF
            return "\x04"
        if ch == "\x1b":  # 方向键是 3 字节转义序列 ESC [ A/B
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            ch = ch + (ch2 or "") + (ch3 or "")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def run_menu(stocks, opener=None, dry_run=False):
    """交互式菜单：↑/↓ 移动光标，Enter 打开当前报告，q 退出。

    stocks: list of {"code","name","file"}；opener 默认 open_report。
    非 TTY 时降级为纯文本列表并返回 None。
    """
    if not stocks:
        print("注册表为空，先用 `stockval add <代码|名称>` 添加")
        return None
    if not sys.stdin.isatty():
        render_list_plain(stocks)
        return None
    if opener is None:
        opener = open_report

    sel = 0
    n = len(stocks)
    idle = 0  # 连续超时次数；连续 5 秒无输入判定无人值守 → 降级纯文本

    def draw():
        sys.stdout.write("\x1b[2J\x1b[H")  # 清屏 + 光标归位
        cols = shutil.get_terminal_size((80, 24)).columns
        bar = "─" * min(cols, 64)
        lines = [
            " A股估值体检 · 选择股票",
            " ↑/↓ 或 j/k 移动光标 · Enter 打开报告 · q 退出",
            bar,
        ]
        for i, s in enumerate(stocks, 1):
            if i - 1 == sel:
                lines.append(f" \x1b[7m▶ {i}. {s['name']} {s['code']}  · {s.get('sector', '')}\x1b[0m")  # 反显高亮
            else:
                lines.append(f"   {i}. {s['name']} {s['code']}  · {s.get('sector', '')}")
        lines.append(bar)
        lines.append(f" 共 {n} 只 · 当前: {stocks[sel]['name']}")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    try:
        draw()
        while True:
            k = _get_key()
            if k is None:  # 超时无输入
                idle += 1
                if idle >= 5:  # 连续 5 秒无人操作 → 自动降级，避免挂起
                    sys.stdout.write("\x1b[2J\x1b[H")
                    print(" 未检测到交互输入，已降级为纯文本列表：\n")
                    render_list_plain(stocks)
                    return None
                continue
            if k == "\x04":  # EOF
                sys.stdout.write("\x1b[2J\x1b[H")
                render_list_plain(stocks)
                return None
            idle = 0
            if k in ("\x1b[A", "\x1b[B", "k", "j"):
                sel = move_selection(sel, n, k)
                draw()
            elif k in ("\r", "\n", " "):  # Enter / 空格 确认
                s = stocks[sel]
                sys.stdout.write("\x1b[2J\x1b[H")
                print(f" 打开报告: {s['file']}")
                if dry_run:
                    print(" [dry-run] 未真正打开浏览器")
                else:
                    opener(s["file"])
                return s
            elif k in ("q", "Q", "\x03"):  # q / Ctrl-C
                sys.stdout.write("\x1b[2J\x1b[H")
                print(" 已退出菜单")
                return None
            # 其余键忽略
    except (EOFError, KeyboardInterrupt):
        sys.stdout.write("\x1b[2J\x1b[H")
        print(" 已退出菜单")
        return None
