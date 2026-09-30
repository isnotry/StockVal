# stockval · A股全维估值体检 CLI

**简体中文** | [English](README.en.md)

![七个数据维度](https://img.shields.io/badge/dimensions-7-brightgreen)
![前端零依赖](https://img.shields.io/badge/frontend%20deps-0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-lightgrey)
![报告离线可开](https://img.shields.io/badge/report-offline-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

> 选入股票，一键抓取七个维度的真实数据，生成能离线打开、能直接发微信的估值体检报告。

![界面截图](https://cdn.jsdelivr.net/gh/isnotry/stockval@main/docs/screenshot.png)

**[在线预览](https://isnotry.github.io/stockval/)**

---

## 它是什么

给它一个股票代码，它把散落在三个数据源上的信息抓齐、算成结论，输出一份可以离线打开的单页报告。

- **形态**：Python CLI。抓取 → 落盘缓存 → 渲染 HTML，全程不需要数据库、不需要服务器。
- **产物**：每只股票一份自包含 HTML（样式与图表全部内联，双击即开），外加一个卡片网格导航页，按 PE(TTM) 从低到高排列，点一下进详情。
- **结论**：报告顺着「贵不贵 / 筹码稳不稳 / 能不能拿」三个问题给出判断，而不是丢一堆原始数字。
- **数据源**：腾讯财经、东方财富、同花顺的公开接口。仅用于研究参考，不构成投资建议。

## 特性

- **七个维度一次抓完** —— 实时行情、前复权 K 线、机构一致预期、主力资金、融资融券、股东户数、研报与分红。
- **零前端依赖** —— 报告里的走势图、柱状图都是渲染时现算的内联 SVG，不需要 ECharts，不加载任何外部资源。
- **手机分享卡片** —— 报告右上角一键弹出竖版卡片，纯前端 canvas 现画，可保存图片或复制到剪贴板，直接发微信。
- **两层交互菜单** —— 无参运行进入菜单，方向键选指令；`remove` 带「选股票 → y/N 二次确认」，不会手滑删库。
- **名称直接解析** —— 输 `贵州茅台` 或 `茅台` 都行，内置常用标的表，表外的联网用东财搜索兜底。
- **缓存与降级** —— 24 小时内不重复抓取；单个数据源挂掉时按策略降级（如主力资金流不可用时改用融资净买入），并在报告里显式标注。

## 快速开始

### 在线预览

点击 **[在线预览](https://isnotry.github.io/stockval/)** 可以直接看到成品长什么样，无需安装。

### 本地使用

```bash
pip install requests
git clone https://github.com/isnotry/stockval.git
cd stockval

python -m stockval add 600519      # 添加一只（抓取 + 渲染 + 重建导航）
python -m stockval refresh         # 一键更新全部自选股
python -m stockval open            # 打开导航页
```

也可以装成命令：`pip install -e .` 之后直接用 `stockval`；仓库内的 `./run.sh` 是免安装的快捷入口。

## 命令一览

| 命令 | 作用 |
|---|---|
| `stockval add <代码\|名称> [行业]` | 新增一只，抓取 + 渲染 + 重建导航 |
| `stockval remove <代码>` | 从注册表移除并删除其报告 |
| `stockval list` | 列出注册表；终端里进菜单，回车直接打开报告 |
| `stockval fetch [代码\|all] [-f]` | 抓数据，默认跳过 24h 内的新鲜缓存，`-f` 强制重抓 |
| `stockval report [代码\|all]` | 只用缓存渲染报告，不联网 |
| `stockval refresh [代码]` | 一键更新：强制抓取 + 渲染 + 重建导航 |
| `stockval build` | 只重建导航页 `index.html` |
| `stockval open` | 用默认浏览器打开导航页 |
| `stockval menu` | 进入两层交互菜单（等同无参运行） |
| `stockval init [--from DIR]` | 迁移旧报告目录，或初始化一个空项目 |

## 界面与按键

报告是暗色单页，从上到下依次是：实时行情卡 → 价格走势 → 机构一致预期 → 主力资金 → 融资余额趋势 → 股东户数 → 最近研报 → 分红送转 → 综合判断。

![单只股票报告](https://cdn.jsdelivr.net/gh/isnotry/stockval@main/docs/screenshot-report.png)

| 位置 | 元素 | 作用 |
|---|---|---|
| 报告右上角 | 分享手机卡片 | 弹出竖版卡片，可保存为图片或复制到剪贴板 |
| 导航页顶部 | 四个指标卡 | 点击按「全部 / PE<15 / 股息率>5% / 当日上涨」筛选 |
| 导航页卡片 | 每只股票一张 | 显示现价、PE、PB、股息率、市值与两个判断标签 |
| 导航页页脚 | GitHub 开源仓库 | 跳回本仓库 |

菜单与列表的按键（`list`、`menu`、`remove` 通用）：

| 按键 | 作用 |
|---|---|
| `↑` `↓` 或 `k` `j` | 上下移动光标 |
| `Enter` 或空格 | 进入指令 / 选中当前项 |
| `q` `Q` `Ctrl-C` | 退出 |
| 5 秒无输入 | 自动降级为纯文本输出，兼容管道与 CI |

报告右上角的分享卡片由浏览器本地现画，不发任何外部请求：

![手机分享卡片](https://cdn.jsdelivr.net/gh/isnotry/stockval@main/docs/screenshot-share.png)

## 七个数据维度

| 维度 | 数据源 | 内容 |
|---|---|---|
| 实时行情 | 腾讯 `qt.gtimg.cn` | 现价、涨跌、PE(TTM)、PB、市值、换手率、52 周高低 |
| 前复权日 K 线 | 腾讯 `ifzq.gtimg.cn` | 默认 80 个交易日，用于走势图 |
| 机构一致预期 | 同花顺 `worth` 页 | 预测机构家数、各年度 EPS 均值、前向 PE、PEG、估值消化年数 |
| 主力资金流 | 东财 `push2his` | 120 日主力净流入，含近 20 日汇总 |
| 融资融券 | 东财 `RPTA_WEB_RZRQ_GGMX` | 60 条融资余额，含区间变化与融资净买入 |
| 股东户数 | 东财 `RPT_HOLDERNUMLATEST` | 最新股东户数与环比变化，用于判断筹码集中度 |
| 研报与分红 | 东财 `reportapi` / `RPT_SHAREBONUS_DET` | 最近 8 篇研报评级；分红送转历史与 TTM 股息率 |

## 结论是怎么算出来的

估值分档只看 PE(TTM)：

```text
PE(TTM) < 15          → 显著低估   （绿 #22c55e）
15 ≤ PE(TTM) < 25     → 估值合理   （黄 #fbbf24）
PE(TTM) ≥ 25          → 估值偏高   （红 #ef4444）
```

- **贵不贵**：按上表分档；TTM 股息率 > 5% 会补一句高股息特征，机构一致预期 EPS 为负增长时提示景气下行。
- **筹码稳不稳**：股东户数环比 < -5% 记为「集中」（主力吸筹），> +5% 记为「分散」（主力派发），其间为「稳定」；同时给出近 20 日融资净流入/净流出方向。
- **能不能拿**：PE < 15 且股息率 > 5% → 「可持有/逢低布局」；PE < 25 → 「观望为主」；否则「谨慎规避」。

涨跌颜色按 A 股习惯：**红涨绿跌**。以上全部为机械规则，不是投资建议。

## 数据与隐私

抓来的数据和生成的报告只落在本机 `output/` 目录，不经过任何服务器；报告本身零外部请求，断网也能打开，分享卡片由浏览器本地绘制。

| 位置 | 内容 | 是否入库 |
|---|---|---|
| `registry.json` | 自选股注册表（代码 / 名称 / 行业） | 否，已被 `.gitignore` 排除 |
| `output/<代码>_data.json` | 抓取的原始数据 + 抓取时间戳 | 否 |
| `output/<代码>_valuation_report.html` | 单股报告 | 否 |
| `output/index.html` | 导航页 | 否 |

- 缓存策略：`fetch` 跳过 24 小时内的新鲜缓存，`refresh` 强制重抓。
- 环境变量 `STOCKVAL_ROOT` 可以把项目根目录指到别处，让代码与数据分开存放。

## 目录结构

```text
stockval/
├── registry.json              # 自选股注册表（本地生成，不入库）
├── registry.example.json      # 注册表示例
├── run.sh                     # 免安装快捷入口
├── docs/                      # README 用的截图
├── demo/                      # 在线预览用的静态示例报告
└── stockval/
    ├── __main__.py            # python -m stockval 入口
    ├── cli.py                 # argparse 子命令分发
    ├── ui.py                  # 两层交互菜单
    ├── menu.py                # 列表光标选择与打开报告
    ├── config.py              # 路径、常量、UA、节流间隔
    ├── registry.py            # 注册表读写
    ├── resolver.py            # 名称 → 代码解析
    ├── cache.py               # 每只股票缓存（JSON 落盘 + 时间戳）
    ├── fetcher/               # 数据源，按源拆分，可单独替换或降级
    │   ├── tencent.py         #   实时行情 + 前复权 K 线
    │   ├── eastmoney.py       #   融资融券 / 股东户数 / 研报 / 分红
    │   ├── eps.py             #   同花顺机构一致预期
    │   ├── funds.py           #   主力资金流 + 降级策略
    │   └── core.py            #   编排：拼装统一结果并落盘
    └── render/                # 渲染层，模板与逻辑分离
        ├── report.py          #   单股报告 + 内联 SVG 图表
        ├── index.py           #   导航页卡片网格 + 点击筛选
        ├── utils.py           #   颜色与金额格式化
        └── templates/         #   纯 HTML 模板
```

## 开发说明

- **加数据源**：在 `stockval/fetcher/` 下照现有文件写一个模块，返回普通 dict，再在 `fetcher/core.py` 的编排里挂上；失败时返回 `{"error": ...}` 即可，渲染层会显示「数据不可用」。
- **改样式**：`render/templates/` 里是纯 HTML，用 `[[TOKEN]]` 占位；替换逻辑在 `render/report.py` 与 `render/index.py`，渲染时会自检是否有未替换的 token 并告警。
- **数据源节流**：东财接口在 `config.EM_MIN_INTERVAL` 上做了全局节流（默认 1 秒）避免被风控，新增东财请求请走 `eastmoney.em_get`。
- **依赖只有一个** `requests`。HTML 表格解析用标准库 `html.parser` 完成，不要再引入 pandas / lxml。
- **调试**：`python -m stockval report` 只读缓存不联网，改渲染逻辑时用它快速迭代。
- 运行脚本加了 `-B` 禁用字节码缓存，避免源码更新后仍跑旧的 `__pycache__`。

## 已知限制

- **主力资金流**：东财 `push2his` 在部分网络（如带透明代理的环境）会被封锁，此时自动降级为融资余额净买入，并在报告里标注。把 `config.DEFAULT_FUND_FALLBACK` 设为 `strict` 可让它直接报错而不降级。
- **股东户数**：东财该接口偶尔返回空，报告内会标注「数据不可用」。
- **接口非官方**：三个数据源都不提供公开 API 承诺，字段或地址随时可能变动，失效时以上游为准。
- **分红字段**：东财返回的是「每 10 股派息」，代码里已 `/10` 折算为每股。
- 仅面向 A 股；北交所代码可用，但行情字段覆盖不如沪深主板完整。

## 许可

[MIT](LICENSE) © 2026 isnotry
