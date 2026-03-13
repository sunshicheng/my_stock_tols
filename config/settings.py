import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- AI API（统一：支持 DeepSeek / OpenAI / Claude / LiteLLM）----------
# 优先读 AI_*，仅当键未设置时回退到 DEEPSEEK_*；显式设为空字符串时不回退
def _env(key: str, legacy: str, default: str = "") -> str:
    val = os.getenv(key)
    if val is not None:
        return val
    return os.getenv(legacy, default)

AI_API_KEY = _env("AI_API_KEY", "DEEPSEEK_API_KEY", "")
AI_BASE_URL = _env("AI_BASE_URL", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
AI_MODEL = _env("AI_MODEL", "DEEPSEEK_MODEL", "deepseek-chat")

# ---------- Paths ----------
DB_PATH = BASE_DIR / "data" / "recommendations.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Schedule ----------
PREDICT_TIME = os.getenv("PREDICT_TIME", "08:30")
REVIEW_TIME = os.getenv("REVIEW_TIME", "16:30")

# ---------- 慢速拉取（减轻限流，宁可慢一点也要拉全）----------
SLOW_FETCH = os.getenv("SLOW_FETCH", "true").lower() in ("1", "true", "yes")
FETCH_INTERVAL_API = float(os.getenv("FETCH_INTERVAL_API", "1.0"))   # 任意接口之间最少间隔（秒）
FETCH_INTERVAL_STOCK = float(os.getenv("FETCH_INTERVAL_STOCK", "0.5"))  # 每只股票历史/新闻之间间隔
FETCH_INTERVAL_NEWS = float(os.getenv("FETCH_INTERVAL_NEWS", "1.2"))   # 每只股票新闻拉取后间隔

# ---------- Stock screening ----------
STOCK_CONFIG = {
    "min_price": 2.0,
    "max_price": 500.0,
    "min_market_cap": 20e8,
    "min_turnover": 5000e4,
    "min_turnover_rate": 1.0,
    "max_turnover_rate": 20.0,
    "history_days": 60,
    "candidate_count": 80,
    "recommend_count": 10,
}

# ---------- Fund screening ----------
FUND_CONFIG = {
    "etf_count": 6,
    "stock_fund_count": 4,
    "hybrid_fund_count": 4,
    "min_volume": 1000e4,
    "target_total": 14,   # 目标总只数（ETF 不足时用开放式基金补足）
}

# ---------- Risk allocation ----------
RISK_ALLOCATION = {
    "aggressive": 3,   # 激进型 30% → 3只
    "stable": 5,       # 稳健型 50% → 5只
    "moderate": 2,     # 适中型 20% → 2只
}
