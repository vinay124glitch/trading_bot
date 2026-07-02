from typing import Dict, Any, Optional

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError, BinanceError
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price
)
from bot.logging_config import logger

def execute_order(
    api_key: str,
    api_secret: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates the order validation, client initialization, and execution.
    Returns a unified dictionary with execution details.
    """
    logger.info("Initializing order validation...")
    
    # 1. Input Validation
    try:
        valid_symbol = validate_symbol(symbol)
        valid_side = validate_side(side)
        valid_type = validate_order_type(order_type)
        valid_quantity = validate_quantity(quantity)
        valid_price = validate_price(price, valid_type)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise

    logger.info(
        f"Validation passed. Request Details: Symbol: {valid_symbol} | Side: {valid_side} | "
        f"Type: {valid_type} | Qty: {valid_quantity} | Price: {valid_price}"
    )

    # 2. Client Initialization
    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    # 3. Call API
    try:
        if valid_type == "LIMIT":
            response = client.place_order(
                symbol=valid_symbol,
                side=valid_side,
                order_type=valid_type,
                quantity=valid_quantity,
                price=valid_price
            )
        elif valid_type == "STOP_MARKET":
            # For STOP_MARKET, the provided price behaves as the activation stop price
            response = client.place_order(
                symbol=valid_symbol,
                side=valid_side,
                order_type=valid_type,
                quantity=valid_quantity,
                stop_price=valid_price
            )
        else: # MARKET
            response = client.place_order(
                symbol=valid_symbol,
                side=valid_side,
                order_type=valid_type,
                quantity=valid_quantity
            )
    except BinanceAPIError as e:
        logger.error(f"Binance API reported failure: {e}")
        raise
    except BinanceNetworkError as e:
        logger.error(f"Network error during execution: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing order: {e}")
        raise

    # 4. Extract Response Details
    # Binance response keys:
    # orderId: unique identifier
    # status: NEW, FILLED, CANCELED, REJECTED, etc.
    # executedQty: quantity that has been filled
    # avgPrice: average fill price (if filled, or may not exist if fully open, check avgPrice or price)
    
    order_id = response.get("orderId")
    status = response.get("status")
    executed_qty = response.get("executedQty")
    avg_price = response.get("avgPrice")
    
    # Fallback to order price if avgPrice is 0.0 or not present
    if not avg_price or float(avg_price) == 0.0:
        avg_price = response.get("price", "N/A")

    logger.info(
        f"Order executed successfully. ID: {order_id} | Status: {status} | "
        f"Executed Qty: {executed_qty} | Avg Price: {avg_price}"
    )

    return {
        "success": True,
        "orderId": order_id,
        "status": status,
        "executedQty": executed_qty,
        "avgPrice": avg_price,
        "raw_response": response
    }
