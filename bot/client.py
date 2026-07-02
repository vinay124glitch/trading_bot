import hmac
import hashlib
import time
import urllib.parse
import requests
from typing import Dict, Any, Optional

from bot.logging_config import logger

class BinanceError(Exception):
    """Base exception for Binance API client errors."""
    pass

class BinanceNetworkError(BinanceError):
    """Raised when a network-level error occurs (timeout, DNS, connection refuse)."""
    pass

class BinanceAPIError(BinanceError):
    """
    Raised when the Binance API returns a non-2xx response.
    Contains the error code and error message returned by Binance.
    """
    def __init__(self, code: int, message: str, status_code: int):
        super().__init__(f"Binance API Error {code}: {message} (HTTP {status_code})")
        self.code = code
        self.error_message = message
        self.status_code = status_code

class BinanceClient:
    """
    REST API client wrapper for Binance Futures Testnet (USDT-M).
    Handles authentication, query signing, and robust error management.
    """
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://testnet.binancefuture.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        
        # Check credentials
        if not self.api_key or not self.api_secret:
            raise BinanceError("API Key and Secret Key must be provided.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MBX-APIKEY": self.api_key
        }

    def _sign_query(self, params: Dict[str, Any]) -> str:
        """
        Creates an HMAC-SHA256 signature for the given parameters.
        Returns the full query string with the signature appended at the end.
        """
        # Convert all parameters to strings and sort/format them
        # Note: We must ensure float values don't use scientific notation.
        query_parts = []
        for key, val in sorted(params.items()):
            if isinstance(val, float):
                # Format float to prevent scientific notation (e.g. 1e-05)
                val_str = f"{val:.8f}".rstrip("0").rstrip(".")
                if not val_str:
                    val_str = "0"
            else:
                val_str = str(val)
            query_parts.append(f"{key}={urllib.parse.quote(val_str)}")
        
        query_string = "&".join(query_parts)
        
        # Calculate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # Append signature to query string (Binance requires signature to be the last parameter)
        return f"{query_string}&signature={signature}"

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Dict[str, Any]:
        """
        Sends an HTTP request to the Binance Futures Testnet API.
        """
        url = f"{self.base_url}{path}"
        req_params = params.copy() if params else {}

        if signed:
            # Sync timestamp and sign
            req_params["timestamp"] = int(time.time() * 1000)
            if "recvWindow" not in req_params:
                req_params["recvWindow"] = 6000 # standard receive window
            
            # Construct signed query string
            query_string = self._sign_query(req_params)
            request_url = f"{url}?{query_string}"
        else:
            query_string = urllib.parse.urlencode(req_params)
            request_url = f"{url}?{query_string}" if query_string else url

        headers = self._get_headers()
        
        # Log request (masking sensitive API secrets or keys)
        # Note: Request url contains signature but not the API secret key. X-MBX-APIKEY is in headers.
        masked_headers = headers.copy()
        if "X-MBX-APIKEY" in masked_headers:
            key_val = masked_headers["X-MBX-APIKEY"]
            masked_headers["X-MBX-APIKEY"] = key_val[:6] + "..." + key_val[-6:] if len(key_val) > 12 else "***"
            
        logger.debug(f"Request: {method} {request_url} | Headers: {masked_headers}")

        try:
            response = requests.request(
                method=method,
                url=url if not signed else request_url,
                params=None if signed else req_params,
                headers=headers,
                timeout=15.0
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during request {method} {url}: {e}", exc_info=True)
            raise BinanceNetworkError(f"Network request failed: {e}")

        # Parse response
        status_code = response.status_code
        logger.debug(f"Response (HTTP {status_code}): {response.text}")

        try:
            data = response.json()
        except ValueError:
            logger.error(f"Malformed response (not JSON) from {path}. HTTP {status_code}: {response.text}")
            raise BinanceError(f"Malformed response from server: {response.text}")

        if 200 <= status_code < 300:
            return data
        else:
            # Binance errors contain 'code' and 'msg'
            err_code = data.get("code", -1)
            err_msg = data.get("msg", "Unknown API error")
            logger.error(f"Binance API Error | HTTP {status_code} | Code {err_code} | Msg: {err_msg}")
            raise BinanceAPIError(code=err_code, message=err_msg, status_code=status_code)

    def ping(self) -> Dict[str, Any]:
        """Test connectivity to the REST API."""
        return self._request("GET", "/fapi/v1/ping")

    def get_server_time(self) -> Dict[str, Any]:
        """Check server time and connectivity."""
        return self._request("GET", "/fapi/v1/time")

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None, stop_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Places a new order on Binance Futures Testnet.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }
        
        # Handle type-specific parameters
        if order_type == "LIMIT":
            if not price:
                raise BinanceError("Price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = "GTC"  # Good Till Cancel
            
        elif order_type == "STOP_MARKET":
            if not stop_price:
                raise BinanceError("Stop Price is required for STOP_MARKET orders.")
            params["stopPrice"] = stop_price
            
        logger.info(f"Placing {side} {order_type} order for {quantity} {symbol} (Price: {price}, StopPrice: {stop_price})")
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Queries status of an order.
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)
