import socket
import subprocess


def _is_private_lan_ip(ip: str) -> bool:
    return (
        ip.startswith("192.168.")
        or ip.startswith("10.")
        or ip.startswith("172.16.")
        or ip.startswith("172.17.")
        or ip.startswith("172.18.")
        or ip.startswith("172.19.")
        or ip.startswith("172.2")
        or ip.startswith("172.30.")
        or ip.startswith("172.31.")
    )


def _ipconfig_ip(interface: str) -> str | None:
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", interface],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    ip = result.stdout.strip()
    return ip if ip and _is_private_lan_ip(ip) else None


def get_lan_ip() -> str | None:
    for interface in ("en0", "en1"):
        ip = _ipconfig_ip(interface)
        if ip:
            return ip

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            return ip if _is_private_lan_ip(ip) else None
    except OSError:
        return None


def dashboard_urls(host: str, port: int) -> dict[str, str | None]:
    local_url = f"http://localhost:{port}"
    lan_ip = get_lan_ip()
    lan_url = f"http://{lan_ip}:{port}" if lan_ip else None
    bind_url = f"http://{host}:{port}"
    return {
        "local": local_url,
        "lan": lan_url,
        "bind": bind_url,
    }
