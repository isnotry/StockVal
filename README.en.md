# StockVal · A-Share Valuation Checkup CLI

[简体中文](README.md) | **English**

![Seven dimensions](https://img.shields.io/badge/dimensions-7-brightgreen)
![No frontend deps](https://img.shields.io/badge/frontend%20deps-0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-lightgrey)
![Offline report](https://img.shields.io/badge/report-offline-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

> Give it a ticker, get seven dimensions of real data and a valuation report you can open offline or forward on WeChat.

![Dashboard screenshot](https://cdn.jsdelivr.net/gh/isnotry/StockVal@main/docs/screenshot.png)

**[Live preview](https://kingsir.work/StockVal/)**

---

## What it is

Hand it a stock code. It collects what is scattered across three data sources, turns it into a verdict, and writes a single-page report you can open offline.

- **Shape**: a Python CLI. Fetch, cache to disk, render HTML — no database, no server.
- **Output**: one self-contained HTML per stock (all styles and charts inlined, double-click to open), plus a card-grid dashboard sorted by PE(TTM), with a click into each report.
- **Verdict**: the report answers three questions — *is it expensive*, *is the shareholder base stable*, *can I hold it* — instead of dumping raw numbers.
- **Sources**: public endpoints of Tencent Finance, Eastmoney and 10jqka. Research reference only, not investment advice.

## Features

- **Seven dimensions in one pass** — live quote, forward-adjusted daily candles, analyst consensus, main-capital flow, margin trading, shareholder count, research reports and dividends.
- **Zero frontend dependencies** — every chart in the report is an inline SVG computed at render time; no ECharts, no external requests.
- **Phone share card** — one button in the report draws an upright card on canvas, ready to save as an image or copy to the clipboard.
- **Two-level interactive menu** — run with no arguments to get a menu; `remove` asks you to pick a stock and then confirm with `y/N`.
- **Name resolution** — type `贵州茅台` or just `茅台`; a built-in table covers common tickers and falls back to an Eastmoney search.
- **Caching and graceful degradation** — nothing is refetched within 24 hours, and a dead source degrades instead of crashing (main-capital flow falls back to net margin buying, and the report says so).

## Quick start

### Online preview

Open the **[live preview](https://kingsir.work/StockVal/)** to see the finished report without installing anything.

### Run it locally

```bash
pip install requests
git clone https://github.com/isnotry/StockVal.git
cd stockval

python -m stockval add 600519      # add one stock (fetch + render + rebuild dashboard)
python -m stockval refresh         # refresh every tracked stock
python -m stockval open            # open the dashboard
```

Install it as a command with `pip install -e .` and call `stockval` directly; `./run.sh` in the repo is a shortcut that needs no install.

## Commands

| Command | What it does |
|---|---|
| `stockval add <code\|name> [sector]` | Add one stock: fetch + render + rebuild dashboard |
| `stockval remove <code>` | Drop a stock from the registry and delete its report |
| `stockval list` | List the registry; in a terminal this opens a picker, Enter opens a report |
| `stockval fetch [code\|all] [-f]` | Fetch data, skipping cache newer than 24h; `-f` forces a refetch |
| `stockval report [code\|all]` | Render from cache only, no network |
| `stockval refresh [code]` | One-shot update: refetch + render + rebuild dashboard |
| `stockval build` | Rebuild the dashboard `index.html` only |
| `stockval open` | Open the dashboard in your default browser |
| `stockval menu` | Enter the two-level interactive menu (same as running with no arguments) |
| `stockval init [--from DIR]` | Migrate an existing report directory, or start an empty project |

## Screens and keys

The report is a dark single page: quote card, price chart, analyst consensus, main-capital flow, margin balance trend, shareholder count, recent reports, dividends, and the verdict box.

![Single stock report](https://cdn.jsdelivr.net/gh/isnotry/StockVal@main/docs/screenshot-report.png)

| Where | Element | What it does |
|---|---|---|
| Report, top right | Share card | Opens the upright card; save as image or copy to clipboard |
| Dashboard, top | Four metric tiles | Click to filter by all / PE<15 / dividend>5% / up today |
| Dashboard, cards | One card per stock | Price, PE, PB, dividend yield, market cap and two verdict tags |
| Dashboard, footer | GitHub repository | Links back to this repository |

Keys for the menus and pickers (`list`, `menu`, `remove` all share them):

| Key | Action |
|---|---|
| `↑` `↓` or `k` `j` | Move the cursor |
| `Enter` or space | Enter a command / pick the current item |
| `q` `Q` `Ctrl-C` | Quit |
| 5 seconds idle | Falls back to plain text output, pipeline and CI friendly |

The share card in the top right corner of a report is drawn locally in the browser and makes no external requests:

![Phone share card](https://cdn.jsdelivr.net/gh/isnotry/StockVal@main/docs/screenshot-share.png)

## The seven dimensions

| Dimension | Source | Contents |
|---|---|---|
| Live quote | Tencent `qt.gtimg.cn` | Price, change, PE(TTM), PB, market cap, turnover, 52-week range |
| Forward-adjusted candles | Tencent `ifzq.gtimg.cn` | 80 trading days by default, used for the price chart |
| Analyst consensus | 10jqka `worth` page | Number of analysts, average EPS per year, forward PE, PEG, years to digest |
| Main-capital flow | Eastmoney `push2his` | 120 days of net inflow, plus a 20-day summary |
| Margin trading | Eastmoney `RPTA_WEB_RZRQ_GGMX` | 60 daily margin balances, range change and net margin buying |
| Shareholder count | Eastmoney `RPT_HOLDERNUMLATEST` | Latest holder count and change ratio, used to read the shareholder base |
| Reports and dividends | Eastmoney `reportapi` / `RPT_SHAREBONUS_DET` | Latest 8 research reports; dividend history and TTM yield |

## How the verdict is computed

The valuation bucket depends only on PE(TTM):

```text
PE(TTM) < 15          → cheap      (green  #22c55e)
15 ≤ PE(TTM) < 25     → fair       (amber  #fbbf24)
PE(TTM) ≥ 25          → expensive  (red    #ef4444)
```

- **Is it expensive**: the buckets above; a TTM dividend yield above 5% adds a high-yield note, and negative consensus EPS growth flags a downcycle.
- **Is the base stable**: a quarter-on-quarter holder change below -5% reads *concentrating* (accumulation), above +5% reads *dispersing* (distribution), anything between is *stable*; the 20-day margin flow direction is shown alongside.
- **Can I hold it**: PE < 15 with yield > 5% gives *hold / accumulate on dips*; PE < 25 gives *wait and see*; otherwise *stay away*.

Up and down follow the A-share convention: **red for up, green for down**. All of the above are mechanical rules, not investment advice.

## Data and privacy

Fetched data and generated reports stay in the local `output/` directory and never touch a server; the report itself makes no external requests, opens offline, and draws its share card locally in the browser.

| Path | Contents | Committed |
|---|---|---|
| `registry.json` | Your watchlist (code / name / sector) | No, excluded by `.gitignore` |
| `output/<code>_data.json` | Raw fetched data plus a fetch timestamp | No |
| `output/<code>_valuation_report.html` | Per-stock report | No |
| `output/index.html` | Dashboard | No |

- Caching: `fetch` skips cache younger than 24 hours, `refresh` forces a refetch.
- The `STOCKVAL_ROOT` environment variable moves the project root elsewhere, so code and data can live apart.

## Project layout

```text
stockval/
├── registry.json              # watchlist (generated locally, not committed)
├── registry.example.json      # example registry
├── run.sh                     # shortcut that needs no install
├── docs/                      # screenshots used by the README
├── demo/                      # static sample reports for the live preview
└── stockval/
    ├── __main__.py            # python -m stockval entry point
    ├── cli.py                 # argparse subcommand dispatch
    ├── ui.py                  # two-level interactive menu
    ├── menu.py                # cursor picker and report opener
    ├── config.py              # paths, constants, user agent, throttle interval
    ├── registry.py            # registry read/write
    ├── resolver.py            # name → code resolution
    ├── cache.py               # per-stock cache (JSON on disk + timestamp)
    ├── fetcher/               # data sources, split by source, swappable
    │   ├── tencent.py         #   live quote + forward-adjusted candles
    │   ├── eastmoney.py       #   margin / holders / reports / dividends
    │   ├── eps.py             #   10jqka analyst consensus
    │   ├── funds.py           #   main-capital flow + fallback strategy
    │   └── core.py            #   orchestration: assemble one result, save it
    └── render/                # rendering layer, templates kept separate
        ├── report.py          #   per-stock report + inline SVG charts
        ├── index.py           #   dashboard card grid + click filtering
        ├── utils.py           #   colour and amount formatting
        └── templates/         #   plain HTML templates
```

## Development notes

- **Adding a source**: write a module under `stockval/fetcher/` that returns a plain dict, then hook it into `fetcher/core.py`. On failure return `{"error": ...}` and the renderer will print "data unavailable".
- **Changing the look**: `render/templates/` holds plain HTML with `[[TOKEN]]` placeholders; the substitution lives in `render/report.py` and `render/index.py`, and renders warn if any token is left unreplaced.
- **Throttling**: Eastmoney calls are throttled globally via `config.EM_MIN_INTERVAL` (1 second by default); route new Eastmoney requests through `eastmoney.em_get`.
- **One dependency**: `requests`. HTML tables are parsed with the standard-library `html.parser` — please do not add pandas or lxml.
- **Debugging**: `python -m stockval report` reads cache only and never touches the network, which makes it the fast loop when working on the renderer.
- The run script passes `-B` to skip bytecode caching, so a stale `__pycache__` can never shadow updated source.

## Known limitations

- **Main-capital flow**: Eastmoney's `push2his` is blocked on some networks (for example behind a transparent proxy). It then falls back to net margin buying and says so in the report. Set `config.DEFAULT_FUND_FALLBACK` to `strict` to fail loudly instead.
- **Shareholder count**: the Eastmoney endpoint occasionally returns empty; the report marks the section as unavailable.
- **Unofficial endpoints**: none of the three sources offer a supported API, so fields and URLs can change without notice.
- **Dividend units**: Eastmoney returns dividend per 10 shares; the code divides by 10 to get per-share figures.
- A-share only. Beijing Stock Exchange codes work, but quote fields are less complete than on the Shanghai and Shenzhen main boards.

## License

[MIT](LICENSE) © 2026 isnotry
