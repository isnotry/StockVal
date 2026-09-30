"""全局配置：路径、常量、UA。"""
import os
from pathlib import Path

# 代码所在目录：模板等随发布分发的资源只跟代码走，不受 STOCKVAL_ROOT 影响
CODE_ROOT = Path(__file__).resolve().parents[1]

# 数据根目录（注册表与产物）：可用 STOCKVAL_ROOT 指到别处，与代码分开存放
PROJECT_ROOT = CODE_ROOT
_env_root = os.environ.get("STOCKVAL_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root).resolve()

REGISTRY_PATH = PROJECT_ROOT / "registry.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = CODE_ROOT / "stockval" / "render" / "templates"

# 缓存：fetch 默认跳过 24h 内的新鲜缓存，refresh 强制重抓
CACHE_MAX_AGE_HOURS = 24

# 东财接口全局节流（秒），避免被风控
EM_MIN_INTERVAL = 1.0

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 主资金流(push2his)在本机/部分网络被代理封锁，默认走融资净买入替代
# 可选: "margin"(默认, 静默降级) / "strict"(报错, 不降级)
DEFAULT_FUND_FALLBACK = "margin"
