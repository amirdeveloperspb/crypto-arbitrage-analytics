# app/notifiers/telegram.py
import asyncio
import logging
import ssl
from datetime import datetime

import aiohttp
import certifi


logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._last_alerts: dict[str, float] = {}
        self._update_offset = 0

    def _connector(self):
        return aiohttp.TCPConnector(ssl=self._ssl_context)

    async def send_message(self, text: str, reply_markup: dict | None = None) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.post(url, json=payload) as response:
                    ok = response.status == 200
                    if ok:
                        logger.info("telegram message sent")
                    else:
                        logger.warning("telegram send failed with status %s", response.status)
                    return ok
        except Exception as exc:
            logger.warning("telegram send failed: %s", exc)
            return False

    async def send_startup(self, symbols: tuple[str, ...] = ("SOLUSDT",), demo_mode: bool = False):
        message = (
            f"<b>Crypto Arbitrage Analytics started</b>\n"
            f"Mode: {'DEMO' if demo_mode else 'LIVE'}\n"
            f"Symbols: {', '.join(symbols)}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Use /menu for interactive controls."
        )
        return await self.send_message(message)

    async def send_menu(self, symbols: tuple[str, ...]) -> bool:
        symbol_rows = []
        for symbol in symbols:
            symbol_rows.extend([
                [
                    {"text": f"Prices {symbol}", "callback_data": f"prices:{symbol}"},
                    {"text": f"Opportunity {symbol}", "callback_data": f"opportunity:{symbol}"},
                ],
                [
                    {"text": f"Execution {symbol}", "callback_data": f"execution:{symbol}:10"},
                ],
            ])
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Status", "callback_data": "status"},
                    {"text": "Symbols", "callback_data": "symbols"},
                ],
                *symbol_rows,
                [
                    {"text": "Help", "callback_data": "help"},
                ],
            ]
        }
        return await self.send_message("<b>Control menu</b>\nChoose an action:", reply_markup=keyboard)

    async def answer_callback_query(self, callback_query_id: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                await session.post(url, json={"callback_query_id": callback_query_id})
        except Exception as exc:
            logger.warning("telegram answerCallbackQuery failed: %s", exc)

    async def alert_opportunity(
        self,
        opportunity: dict,
        quality: dict | None,
        min_score: float,
        cooldown_seconds: int,
    ) -> bool:
        if not opportunity:
            return False
        if opportunity["score"] < min_score:
            return False
        if not opportunity["is_positive_after_fees"]:
            return False

        key = f"{opportunity['symbol']}:{opportunity['buy_on']}:{opportunity['sell_on']}"
        now = datetime.now().timestamp()
        if now - self._last_alerts.get(key, 0) < cooldown_seconds:
            return False

        self._last_alerts[key] = now
        quality_label = quality["quality"] if quality else "unknown"
        message = (
            f"<b>Arbitrage opportunity</b>\n"
            f"Pair: <code>{opportunity['symbol']}</code>\n"
            f"Buy: {opportunity['buy_on']} @ ${opportunity['buy_price']:.4f}\n"
            f"Sell: {opportunity['sell_on']} @ ${opportunity['sell_price']:.4f}\n"
            f"Gross spread: {opportunity['spread_pct']:+.4f}%\n"
            f"Fees: ${opportunity['estimated_fees_usd']:.2f}\n"
            f"Net: ${opportunity['estimated_net_profit_usd']:+.2f}\n"
            f"Size estimate: {min(opportunity['buy_size'], opportunity['sell_size']):.4f}\n"
            f"Score: {opportunity['score']:.1f}/100 ({quality_label})\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return await self.send_message(message)

    async def get_updates(self) -> list[dict]:
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"timeout": 20, "offset": self._update_offset}
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning("telegram getUpdates failed with status %s", response.status)
                        return []
                    payload = await response.json()
        except Exception as exc:
            logger.warning("telegram getUpdates failed: %s", exc)
            return []

        updates = payload.get("result", [])
        if updates:
            self._update_offset = max(update["update_id"] for update in updates) + 1
        return updates


def _help_text() -> str:
    return (
        "<b>Commands</b>\n"
        "/menu - interactive buttons\n"
        "/status - service status\n"
        "/symbols - available symbols\n"
        "/prices SOLUSDT - current bid/ask\n"
        "/opportunity SOLUSDT - best top-of-book opportunity\n"
        "/execution SOLUSDT 10 - order-book execution estimate\n"
        "/help - command list"
    )


def _parse_update(update: dict, symbols: tuple[str, ...]) -> tuple[str, str, float, str]:
    default_symbol = symbols[0] if symbols else "SOLUSDT"
    callback = update.get("callback_query")
    if callback:
        data = callback.get("data", "")
        parts = data.split(":")
        command = "/" + parts[0]
        symbol = parts[1].upper() if len(parts) > 1 else default_symbol
        try:
            size = float(parts[2]) if len(parts) > 2 else 10.0
        except ValueError:
            size = 10.0
        chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
        return command, symbol, size, chat_id

    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    parts = text.split()
    command = parts[0].lower() if parts else ""
    symbol = parts[1].upper() if len(parts) > 1 else default_symbol
    try:
        size = float(parts[2]) if len(parts) > 2 else 10.0
    except ValueError:
        size = 10.0
    chat_id = str(message.get("chat", {}).get("id", ""))
    return command, symbol, size, chat_id


async def telegram_command_loop(
    notifier: TelegramNotifier,
    state,
    symbols: tuple[str, ...],
    analyzer,
    quality_model,
    demo_mode: bool,
    execution_analyzer=None,
) -> None:
    while True:
        updates = await notifier.get_updates()
        for update in updates:
            callback = update.get("callback_query")
            if callback:
                await notifier.answer_callback_query(callback["id"])

            command, symbol, size, chat_id = _parse_update(update, symbols)
            if chat_id != notifier.chat_id:
                continue
            if symbol not in symbols:
                symbol = symbols[0]

            if command == "/status":
                await notifier.send_message(
                    f"Status: running\nMode: {'DEMO' if demo_mode else 'LIVE'}\nSymbols: {', '.join(symbols)}"
                )
            elif command == "/menu":
                await notifier.send_menu(symbols)
            elif command == "/symbols":
                await notifier.send_message("Symbols: " + ", ".join(symbols))
            elif command == "/prices":
                snapshots = state.get_all_for_symbol(symbol)
                lines = [f"<b>{symbol} prices</b>"]
                for exchange, snapshot in sorted(snapshots.items()):
                    lines.append(f"{exchange}: bid ${snapshot.bid_price:.4f} / ask ${snapshot.ask_price:.4f}")
                await notifier.send_message("\n".join(lines) if len(lines) > 1 else f"No prices for {symbol}")
            elif command == "/opportunity":
                opportunity = analyzer.find_best(symbol, state.get_all_for_symbol(symbol))
                quality = quality_model.predict_quality(opportunity)
                if not opportunity:
                    await notifier.send_message(f"No fresh opportunity for {symbol}")
                else:
                    await notifier.send_message(
                        f"<b>{symbol} opportunity</b>\n"
                        f"Buy: {opportunity['buy_on']} @ ${opportunity['buy_price']:.4f}\n"
                        f"Sell: {opportunity['sell_on']} @ ${opportunity['sell_price']:.4f}\n"
                        f"Net: ${opportunity['estimated_net_profit_usd']:+.2f}\n"
                        f"Score: {opportunity['score']:.1f}/100\n"
                        f"Quality: {quality['quality']}"
                    )
            elif command == "/execution":
                if not execution_analyzer:
                    await notifier.send_message("Execution analyzer is not available")
                    continue
                result = execution_analyzer.find_best_executable(
                    symbol=symbol,
                    order_books=state.get_order_books_for_symbol(symbol),
                    target_size=size,
                )
                if not result:
                    await notifier.send_message(f"No executable order-book route for {symbol}")
                else:
                    await notifier.send_message(
                        f"<b>{symbol} execution estimate</b>\n"
                        f"Size: {result['target_size']:.4f}\n"
                        f"Route: {result['buy_on']} → {result['sell_on']}\n"
                        f"Raw spread: {result['raw_spread_pct']:+.4f}%\n"
                        f"VWAP spread: {result['executable_spread_pct']:+.4f}%\n"
                        f"Net: ${result['estimated_net_profit_usd']:+.2f}\n"
                        f"Slippage: {result['combined_slippage_pct']:.4f}%\n"
                        f"Max profitable size: {result['max_profitable_size']:.4f}\n"
                        f"Score: {result['score']:.1f}/100"
                    )
            elif command == "/help":
                await notifier.send_message(_help_text())
            elif command:
                await notifier.send_message("Unknown command. Send /menu or /help.")

        await asyncio.sleep(1)
