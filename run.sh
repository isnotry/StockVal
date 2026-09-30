#!/bin/sh
# StockVal 便捷运行脚本 —— 免去手敲 python -m stockval
# 用法：./run.sh <子命令> [参数...]
#   例：./run.sh list
#        ./run.sh add 600519
#        ./run.sh refresh
# 想固定某个解释器时用环境变量覆盖：STOCKVAL_PY=/path/to/python ./run.sh list
cd "$(dirname "$0")" || exit 1

if [ -n "$STOCKVAL_PY" ] && [ -x "$STOCKVAL_PY" ]; then
  exec "$STOCKVAL_PY" -B -m stockval "$@"
fi
# 优先仓库内的虚拟环境，其次系统 python3
for cand in .venv/bin/python3 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    exec "$cand" -B -m stockval "$@"
  fi
done
echo "未找到可用的 python3，请先安装 Python 3.10+ 或设置 STOCKVAL_PY" >&2
exit 1
