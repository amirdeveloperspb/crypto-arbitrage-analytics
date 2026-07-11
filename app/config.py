import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()

def _get_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw_value!r}") from exc


def _get_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw_value!r}") from exc


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    trading_symbol: str
    trading_symbols: tuple[str, ...]
    trading_budget: float
    taker_fee_rate: float
    max_price_age_seconds: float
    web_host: str
    web_port: int
    home_server_mode: bool
    history_db_path: str
    history_flush_interval_seconds: float
    demo_mode: bool
    min_spread_pct: float
    telegram_commands_enabled: bool
    telegram_alert_min_score: float
    telegram_alert_cooldown_seconds: int


def _get_symbols() -> tuple[str, ...]:
    raw_symbols = os.getenv("TRADING_SYMBOLS", "")
    if not raw_symbols:
        default_symbols = ("SOLUSDT", "BTCUSDT", "ETHUSDT")
        single_symbol = os.getenv("TRADING_SYMBOL")
        if single_symbol and single_symbol.strip().upper() not in default_symbols:
            return (single_symbol.strip().upper(), *default_symbols)
        return default_symbols

    symbols = tuple(
        symbol.strip().upper()
        for symbol in raw_symbols.split(",")
        if symbol.strip()
    )
    return symbols or ("SOLUSDT",)


def _get_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    symbols = _get_symbols()
    default_symbol = os.getenv("DEFAULT_SYMBOL", os.getenv("TRADING_SYMBOL", symbols[0])).upper()
    if default_symbol not in symbols:
        symbols = (default_symbol, *symbols)

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        trading_symbol=default_symbol,
        trading_symbols=symbols,
        trading_budget=_get_float("TRADING_BUDGET", 500.0),
        taker_fee_rate=_get_float("TAKER_FEE_RATE", 0.001),
        max_price_age_seconds=_get_float("MAX_PRICE_AGE_SECONDS", 2.0),
        home_server_mode=_get_bool("HOME_SERVER_MODE", False),
        web_host="0.0.0.0" if _get_bool("HOME_SERVER_MODE", False) else os.getenv("WEB_HOST", "localhost"),
        web_port=_get_int("WEB_PORT", 8080),
        history_db_path=os.getenv("HISTORY_DB_PATH", "data/market_history.sqlite3"),
        history_flush_interval_seconds=_get_float("HISTORY_FLUSH_INTERVAL_SECONDS", 5.0),
        demo_mode=_get_bool("DEMO_MODE", False),
        min_spread_pct=_get_float("MIN_SPREAD_PCT", 0.0),
        telegram_commands_enabled=_get_bool("TELEGRAM_COMMANDS_ENABLED", False),
        telegram_alert_min_score=_get_float("TELEGRAM_ALERT_MIN_SCORE", 70.0),
        telegram_alert_cooldown_seconds=_get_int("TELEGRAM_ALERT_COOLDOWN_SECONDS", 180),
    )


settings = load_settings()

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = settings.telegram_chat_id

# Торговые настройки
TRADING_SYMBOL = settings.trading_symbol
TRADING_SYMBOLS = settings.trading_symbols
TRADING_BUDGET = settings.trading_budget
TAKER_FEE_RATE = settings.taker_fee_rate
MAX_PRICE_AGE_SECONDS = settings.max_price_age_seconds
WEB_HOST = settings.web_host
WEB_PORT = settings.web_port
HOME_SERVER_MODE = settings.home_server_mode
HISTORY_DB_PATH = settings.history_db_path
HISTORY_FLUSH_INTERVAL_SECONDS = settings.history_flush_interval_seconds
DEMO_MODE = settings.demo_mode
MIN_SPREAD_PCT = settings.min_spread_pct
TELEGRAM_COMMANDS_ENABLED = settings.telegram_commands_enabled
TELEGRAM_ALERT_MIN_SCORE = settings.telegram_alert_min_score
TELEGRAM_ALERT_COOLDOWN_SECONDS = settings.telegram_alert_cooldown_seconds
