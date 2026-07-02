import unittest
from unittest.mock import patch, MagicMock
import urllib.parse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    ValidationError
)
from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError, BinanceError
from bot.orders import execute_order


class TestValidators(unittest.TestCase):
    def test_validate_symbol(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")
        self.assertEqual(validate_symbol("BTCUSDT"), "BTCUSDT")
        self.assertEqual(validate_symbol("1000luncusdt"), "1000LUNCUSDT")
        
        with self.assertRaises(ValidationError):
            validate_symbol("")
        with self.assertRaises(ValidationError):
            validate_symbol("BTC-USDT")  # special chars not allowed
        with self.assertRaises(ValidationError):
            validate_symbol("A")  # too short

    def test_validate_side(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")
        
        with self.assertRaises(ValidationError):
            validate_side("HOLD")
        with self.assertRaises(ValidationError):
            validate_side("")

    def test_validate_order_type(self):
        self.assertEqual(validate_order_type("market"), "MARKET")
        self.assertEqual(validate_order_type("LIMIT"), "LIMIT")
        self.assertEqual(validate_order_type("stop_market"), "STOP_MARKET")
        
        with self.assertRaises(ValidationError):
            validate_order_type("STOP_LIMIT")  # not in supported list
        with self.assertRaises(ValidationError):
            validate_order_type("")

    def test_validate_quantity(self):
        self.assertEqual(validate_quantity("0.001"), 0.001)
        self.assertEqual(validate_quantity("100"), 100.0)
        
        with self.assertRaises(ValidationError):
            validate_quantity("-1")
        with self.assertRaises(ValidationError):
            validate_quantity("0")
        with self.assertRaises(ValidationError):
            validate_quantity("abc")

    def test_validate_price(self):
        # LIMIT and STOP_MARKET orders require positive prices
        self.assertEqual(validate_price("3200.5", "LIMIT"), 3200.5)
        self.assertEqual(validate_price("150", "STOP_MARKET"), 150.0)
        
        with self.assertRaises(ValidationError):
            validate_price("", "LIMIT")
        with self.assertRaises(ValidationError):
            validate_price("-5", "STOP_MARKET")
        with self.assertRaises(ValidationError):
            validate_price("abc", "LIMIT")

        # MARKET orders do not require price, but if provided, must be valid
        self.assertIsNone(validate_price("", "MARKET"))
        self.assertEqual(validate_price("123", "MARKET"), 123.0)
        with self.assertRaises(ValidationError):
            validate_price("-10", "MARKET")


class TestBinanceClient(unittest.TestCase):
    def setUp(self):
        self.client = BinanceClient(api_key="test_key", api_secret="test_secret")

    def test_signature_generation(self):
        # Test signature generation with deterministic parameters
        params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": 0.001,
            "timestamp": 1691661059000
        }
        # The query string will be sorted: quantity=0.001&side=BUY&symbol=BTCUSDT&timestamp=1691661059000&type=LIMIT
        # Let's verify key-value format and signature structure
        signed_qs = self.client._sign_query(params)
        self.assertIn("signature=", signed_qs)
        self.assertTrue(signed_qs.endswith(signed_qs.split("signature=")[-1]))
        
        # Verify order of parameters (signature must be at the end)
        parts = signed_qs.split("&")
        self.assertTrue(parts[-1].startswith("signature="))

    @patch("requests.request")
    def test_ping_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response
        
        result = self.client.ping()
        self.assertEqual(result, {})
        mock_request.assert_called_once_with(
            method="GET",
            url="https://testnet.binancefuture.com/fapi/v1/ping",
            params={},
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-MBX-APIKEY": "test_key"},
            timeout=15.0
        )

    @patch("requests.request")
    def test_place_order_market_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "orderId": 123456,
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "62000.0"
        }
        mock_request.return_value = mock_response
        
        # Call client method
        res = self.client.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001
        )
        
        self.assertEqual(res["orderId"], 123456)
        self.assertEqual(res["status"], "FILLED")
        
        # The URL in mock_request call must have signature parameter
        args, kwargs = mock_request.call_args
        self.assertIn("https://testnet.binancefuture.com/fapi/v1/order", kwargs["url"])
        self.assertIn("signature=", kwargs["url"])

    @patch("requests.request")
    def test_api_error_handling(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": -1102,
            "msg": "Mandatory parameter 'signature' was not sent, was empty/null, or malformed."
        }
        mock_request.return_value = mock_response
        
        with self.assertRaises(BinanceAPIError) as context:
            self.client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001
            )
        self.assertEqual(context.exception.code, -1102)
        self.assertIn("Mandatory parameter", str(context.exception))

    @patch("requests.request")
    def test_network_error_handling(self, mock_request):
        import requests.exceptions
        mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with self.assertRaises(BinanceNetworkError):
            self.client.ping()


class TestOrdersOrchestrator(unittest.TestCase):
    @patch("bot.orders.BinanceClient")
    def test_execute_order_orchestrator(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.place_order.return_value = {
            "orderId": 78910,
            "status": "NEW",
            "executedQty": "0.0",
            "price": "3500.0"
        }
        mock_client_class.return_value = mock_client
        
        res = execute_order(
            api_key="test_key",
            api_secret="test_secret",
            symbol="ETHUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity="0.05",
            price="3500.0"
        )
        
        self.assertTrue(res["success"])
        self.assertEqual(res["orderId"], 78910)
        self.assertEqual(res["status"], "NEW")
        self.assertEqual(res["avgPrice"], "3500.0")
        
        # Verify validation inputs mapped to float
        mock_client.place_order.assert_called_once_with(
            symbol="ETHUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=0.05,
            price=3500.0
        )


if __name__ == "__main__":
    unittest.main()
