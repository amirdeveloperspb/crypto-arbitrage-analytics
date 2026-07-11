# app/exchanges/base.py
import asyncio
import json
import logging
import ssl
import websockets
from abc import ABC, abstractmethod

import certifi

from app.core.market_data import MarketDataState, MarketSnapshot


logger = logging.getLogger(__name__)


class BaseExchangeWebSocket(ABC):
    """
    Базовый класс для всех биржевых websocket.
    Содержит общую логику: connect, reconnect, stop.
    """

    # Переопределяется в наследниках
    WS_URL: str = ""
    EXCHANGE_NAME: str = ""
    MAX_SIZE: int = 2048  # лимит размера сообщения

    def __init__(self, state: MarketDataState, symbols: tuple[str, ...] = ("SOLUSDT",)):
        self.state = state
        self.symbols = symbols
        self.running = False
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def start(self):
        """Главный цикл: подключаемся, слушаем, переподключаемся."""
        self.running = True

        while self.running:
            try:
                logger.info("%s connecting", self.EXCHANGE_NAME)
                async with websockets.connect(
                        self.WS_URL,
                        max_size=self.MAX_SIZE,
                        ping_interval=30,
                        ping_timeout=10,
                        ssl=self._ssl_context
                ) as ws:
                    logger.info("%s connected", self.EXCHANGE_NAME)

                    # Отправляем подписку (если нужна)
                    await self._subscribe(ws)

                    # Слушаем сообщения
                    while self.running:
                        message = await ws.recv()
                        await self._handle_raw_message(message)

            except Exception as e:
                logger.warning("%s error: %s: %s", self.EXCHANGE_NAME, type(e).__name__, e)
                logger.info("%s reconnecting in 5s", self.EXCHANGE_NAME)
                await asyncio.sleep(5)

    async def _subscribe(self, ws):
        """
        Отправить сообщение подписки. Переопределяется если нужно.
        По умолчанию ничего не делает (Binance не требует подписки).
        """
        pass

    async def _handle_raw_message(self, raw: str):
        """Парсим JSON и передаём в _parse_message."""
        try:
            data = json.loads(raw)
            parsed = self._parse_message(data)
            if parsed is None:
                return

            snapshots = parsed if isinstance(parsed, list) else [parsed]
            for snapshot in snapshots:
                self.state.update(snapshot)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            pass  # silent skip

    @abstractmethod
    def _parse_message(self, data: dict) -> MarketSnapshot | list[MarketSnapshot] | None:
        """
        Извлечь MarketSnapshot из сообщения биржи.
        Каждая биржа реализует по-своему.
        """
        pass

    def stop(self):
        self.running = False
