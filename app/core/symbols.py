def normalize_symbol(symbol: str) -> str:
    return symbol.replace("-", "").replace("_", "").upper()


def to_okx_spot_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if normalized.endswith("USDT"):
        return f"{normalized[:-4]}-USDT"
    return normalized


def to_okx_swap_symbol(symbol: str) -> str:
    return f"{to_okx_spot_symbol(symbol)}-SWAP"


def to_lower_stream_symbol(symbol: str) -> str:
    return normalize_symbol(symbol).lower()


def to_gate_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if normalized.endswith("USDT"):
        return f"{normalized[:-4]}_USDT"
    return normalized
