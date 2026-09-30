"""stockval CLI 入口。

子命令（单行，仍可直接使用，兼容现有脚本 / run.sh）：
  init                迁移已有报告 / 初始化空项目
  add <代码|名称> [行业]   解析并新增一只股票（抓取+渲染+重建导航）
  remove <代码>       移除一只股票
  list                列出注册表中的股票
  fetch [代码|all]    抓取数据（默认跳过24h内缓存，--force 强制）
  report [代码|all]   用缓存数据渲染报告（不联网）
  build               仅重建引导页 index.html
  refresh [代码]      一键更新：抓取(强制)+渲染+重建导航（默认全部）
  open                在默认浏览器打开导航页 index.html
  menu                进入两层交互菜单（等同无参运行 `stockval`）

两层交互菜单（`stockval` 无参 或 `stockval menu`）：
  顶层列出全部指令与功能介绍，↑/↓/j/k 移动，Enter 进入对应流程，q 退出。
  其中 remove 接入「选股票 → 二次确认」流程：先选股票，再 y/N 确认才删除。
"""
import argparse
import sys
import shutil
from pathlib import Path

from . import registry, cache
from . import resolver
from .fetcher import core
from .render import report as report_mod
from .render import index as index_mod
from .config import OUTPUT_DIR, REGISTRY_PATH

# 迁移时可选的源目录默认值。留空：不带 --from 运行时直接初始化一个空项目。
DEFAULT_INIT_SRC = ""


def _render_one(code):
    D = cache.load(code)
    if not D:
        print(f"  ⚠️ {code} 无缓存数据，请先 fetch")
        return
    html = report_mod.build_report_html(D)
    out = cache.report_path(code)
    out.write_text(html, encoding="utf-8")
    print(f"  ✅ 报告已生成: {out} ({len(html)/1024:.1f} KB)")


def _render_all():
    for code in registry.codes():
        _render_one(code)


def _resolve_targets(code):
    if code is None or code == "all":
        return registry.codes()
    return [resolver.resolve(code)]


def cmd_init(args):
    src = Path(args.from_path) if args.from_path else (Path(DEFAULT_INIT_SRC) if DEFAULT_INIT_SRC else None)
    if src is None:
        print("未指定源目录，创建空项目")
        registry.save([])
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("   用 `stockval add <代码|名称>` 添加第一只股票；已有旧报告可用 init --from <目录> 迁移")
        return
    if not src.exists():
        print(f"源目录不存在：{src}，创建空项目")
        registry.save([])
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return
    stocks = []
    for fp in sorted(src.glob("*_data.json")):
        d = __import__("json").loads(fp.read_text(encoding="utf-8"))
        stocks.append({
            "code": d.get("code"),
            "name": d.get("name", d.get("code")),
            "sector": d.get("sector", ""),
        })
    registry.save(stocks)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for pat in ("*_data.json", "*_valuation_report.html"):
        for fp in src.glob(pat):
            shutil.copy(fp, OUTPUT_DIR / fp.name)
            copied += 1
    if (src / "index.html").exists():
        shutil.copy(src / "index.html", OUTPUT_DIR / "index.html")
        copied += 1
    print(f"✅ 已迁移 {len(stocks)} 只股票到 {OUTPUT_DIR}（{copied} 个文件）")
    print("   运行 `stockval refresh` 可一键更新全部数据")


def cmd_add(args):
    code = resolver.resolve(args.token)
    if registry.get(code):
        print(f"⚠️ {code} 已在注册表，跳过添加（如需更新请运行 refresh {code}）")
    else:
        data = core.fetch_stock(code, name="", sector=args.sector or "")
        name = data.get("name") or args.token
        registry.add(code, name, args.sector or "")
        print(f"✅ 已添加 {name}({code}) 到注册表")
    _render_one(code)
    index_html = index_mod.build_index()
    if index_html:
        cache.index_path().write_text(index_html, encoding="utf-8")
        print(f"✅ 导航页已重建: {cache.index_path()}")


def cmd_remove(args):
    code = resolver.resolve(args.code)
    if not registry.get(code):
        print(f"⚠️ {code} 不在注册表")
        return
    registry.remove(code)
    cache.delete(code)
    print(f"✅ 已移除 {code} 及其报告")
    index_html = index_mod.build_index()
    if index_html:
        cache.index_path().write_text(index_html, encoding="utf-8")
        print(f"✅ 导航页已重建: {cache.index_path()}")


def cmd_list(args):
    stocks = registry.load()
    if not stocks:
        print("注册表为空，使用 `stockval add <代码|名称>` 添加")
        return
    # 排序与导航页(index.html)一致：PE(TTM) 升序，PE 缺失/为 0 排最后
    cards = []
    for s in stocks:
        D = cache.load(s["code"]) or {}
        pe = D.get("quote", {}).get("pe_ttm", 0)
        cards.append({
            "code": s["code"],
            "name": s["name"],
            "sector": s.get("sector", ""),
            "file": str(cache.report_path(s["code"])),
            "_pe": pe if pe else float("inf"),
        })
    cards.sort(key=lambda c: c["_pe"])
    # 非 TTY（管道/重定向）或显式 --plain → 纯文本，脚本友好
    if args.plain or not sys.stdin.isatty():
        print(f"注册表共 {len(cards)} 只（按 PE(TTM) 升序）：")
        for i, c in enumerate(cards, 1):
            print(f"  {i}. {c['name']} {c['code']}  · {c.get('sector', '')}")
        return
    # 交互式菜单：上下移动光标，Enter 直接打开网页
    from . import menu
    menu.run_menu(cards, dry_run=args.dry_run)


def cmd_fetch(args):
    targets = _resolve_targets(args.code)
    if not targets:
        print("注册表为空，先 add 或 init")
        return
    for code in targets:
        core.fetch_stock(code, name="", sector="", force=args.force)


def cmd_report(args):
    targets = _resolve_targets(args.code) if args.code else registry.codes()
    if not targets:
        print("注册表为空")
        return
    for code in targets:
        _render_one(code)
    print(f"\n🎉 已渲染 {len(targets)} 份报告")


def cmd_build(args):
    index_html = index_mod.build_index()
    if index_html:
        cache.index_path().write_text(index_html, encoding="utf-8")
        print(f"✅ 导航页已重建: {cache.index_path()}")


def cmd_open(args):
    """在默认浏览器打开导航页 index.html。"""
    idx = cache.index_path()
    if not idx.exists():
        print(f"⚠️ 导航页不存在：{idx}")
        print("   请先运行 `stockval build` 或 `stockval refresh` 生成导航页")
        return
    print(f" 打开导航页: {idx}")
    if args.dry_run:
        print(" [dry-run] 未真正打开浏览器")
        return
    from . import menu
    menu.open_report(str(idx))


def cmd_refresh(args):
    """一键更新：抓取(强制)+渲染+重建导航。"""
    targets = _resolve_targets(args.code)
    if not targets:
        print("注册表为空，先 add 或 init")
        return
    print(f"🔄 一键更新：共 {len(targets)} 只")
    for code in targets:
        # 用注册表里的名称/行业回填，让行情 name 覆盖
        info = registry.get(code) or {}
        core.fetch_stock(code, name=info.get("name", ""), sector=info.get("sector", ""), force=True)
    for code in targets:
        _render_one(code)
    index_html = index_mod.build_index()
    if index_html:
        cache.index_path().write_text(index_html, encoding="utf-8")
        print(f"✅ 导航页已重建: {cache.index_path()}")
    print("\n🎉 全部更新完成")


def cmd_menu(args):
    """进入两层交互菜单（等同无参运行 `stockval`）。"""
    from . import ui
    ui.run_main_menu()


def main():
    parser = argparse.ArgumentParser(
        prog="stockval",
        description="A股全维估值体检 CLI — 七维数据透视 + 暗色科技风单页报告",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="迁移已有报告 / 初始化空项目")
    p_init.add_argument("--from", dest="from_path", help="旧报告目录（含 *_data.json）")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="新增一只股票（解析+抓取+渲染）")
    p_add.add_argument("token", help="6位代码 或 股票名称")
    p_add.add_argument("sector", nargs="?", default="", help="行业（可选）")
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser("remove", help="移除一只股票")
    p_rm.add_argument("code", help="6位代码")
    p_rm.set_defaults(func=cmd_remove)

    p_list = sub.add_parser("list", help="列出注册表（TTY 下进入交互菜单，可选中直接打开报告）")
    p_list.add_argument("-p", "--plain", action="store_true", help="纯文本输出（不进入交互菜单）")
    p_list.add_argument("--dry-run", action="store_true", help="菜单选中后只打印路径，不真正打开浏览器")
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="抓取数据（默认跳过新鲜缓存）")
    p_fetch.add_argument("code", nargs="?", default=None, help="代码/all，省略=全部")
    p_fetch.add_argument("-f", "--force", action="store_true", help="强制重抓（忽略缓存）")
    p_fetch.set_defaults(func=cmd_fetch)

    p_report = sub.add_parser("report", help="用缓存渲染报告（不联网）")
    p_report.add_argument("code", nargs="?", default=None, help="代码/all，省略=全部")
    p_report.set_defaults(func=cmd_report)

    p_build = sub.add_parser("build", help="仅重建引导页")
    p_build.set_defaults(func=cmd_build)

    p_refresh = sub.add_parser("refresh", help="一键更新全部（抓取+渲染+导航）")
    p_refresh.add_argument("code", nargs="?", default=None, help="指定代码；省略=全部")
    p_refresh.set_defaults(func=cmd_refresh)

    p_open = sub.add_parser("open", help="在默认浏览器打开导航页 index.html")
    p_open.add_argument("--dry-run", action="store_true", help="只打印路径，不真正打开浏览器")
    p_open.set_defaults(func=cmd_open)

    p_menu = sub.add_parser("menu", help="进入两层交互菜单（等同无参运行 stockval）")
    p_menu.set_defaults(func=cmd_menu)

    args = parser.parse_args()
    if not args.cmd:
        from . import ui
        ui.run_main_menu()
        return
    args.func(args)


if __name__ == "__main__":
    main()
