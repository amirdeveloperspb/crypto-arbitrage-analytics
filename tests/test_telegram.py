import unittest

from app.notifiers.telegram import _parse_update


class TelegramCommandParsingTests(unittest.TestCase):
    def test_parse_execution_text_command(self):
        update = {
            "message": {
                "chat": {"id": 123},
                "text": "/execution btcusdt 5",
            }
        }

        command, symbol, size, chat_id = _parse_update(update, ("SOLUSDT", "BTCUSDT"))

        self.assertEqual(command, "/execution")
        self.assertEqual(symbol, "BTCUSDT")
        self.assertEqual(size, 5.0)
        self.assertEqual(chat_id, "123")

    def test_parse_execution_callback(self):
        update = {
            "callback_query": {
                "data": "execution:SOLUSDT:10",
                "message": {"chat": {"id": 456}},
            }
        }

        command, symbol, size, chat_id = _parse_update(update, ("SOLUSDT", "BTCUSDT"))

        self.assertEqual(command, "/execution")
        self.assertEqual(symbol, "SOLUSDT")
        self.assertEqual(size, 10.0)
        self.assertEqual(chat_id, "456")

    def test_invalid_size_falls_back_to_default(self):
        update = {
            "message": {
                "chat": {"id": 123},
                "text": "/execution SOLUSDT wrong",
            }
        }

        _, _, size, _ = _parse_update(update, ("SOLUSDT",))

        self.assertEqual(size, 10.0)


if __name__ == "__main__":
    unittest.main()
