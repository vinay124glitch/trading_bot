import re

class ValidationError(Exception):
    """Exception raised when input validation fails."""
    pass

def validate_symbol(symbol: str) -> str:
    """
    Validates the trading symbol (e.g. BTCUSDT, ETHUSDT).
    Must be alphanumeric, uppercase, and between 3 to 15 characters.
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    
    symbol_clean = symbol.strip().upper()
    # Binance symbols are uppercase alphanumeric strings, e.g., BTCUSDT, 1000LUNCUSDT
    if not re.match(r"^[A-Z0-9]{3,15}$", symbol_clean):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Symbol must be uppercase alphanumeric (e.g., BTCUSDT, ETHUSDT)."
        )
    return symbol_clean

def validate_side(side: str) -> str:
    """
    Validates the order side. Must be 'BUY' or 'SELL'.
    """
    if not side:
        raise ValidationError("Order side cannot be empty.")
    
    side_clean = side.strip().upper()
    if side_clean not in ("BUY", "SELL"):
        raise ValidationError(f"Invalid side: '{side}'. Must be 'BUY' or 'SELL'.")
    return side_clean

def validate_order_type(order_type: str) -> str:
    """
    Validates the order type. Must be 'MARKET', 'LIMIT', or 'STOP_MARKET'.
    """
    if not order_type:
        raise ValidationError("Order type cannot be empty.")
    
    type_clean = order_type.strip().upper()
    valid_types = ("MARKET", "LIMIT", "STOP_MARKET")
    if type_clean not in valid_types:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Supported types are: {', '.join(valid_types)}."
        )
    return type_clean

def validate_quantity(quantity: str) -> float:
    """
    Validates the order quantity. Must be a positive number.
    """
    if not quantity:
        raise ValidationError("Quantity cannot be empty.")
    
    try:
        qty_val = float(quantity)
    except ValueError:
        raise ValidationError(f"Invalid quantity: '{quantity}'. Must be a valid number.")
    
    if qty_val <= 0:
        raise ValidationError(f"Quantity must be a positive number (got {qty_val}).")
    
    return qty_val

def validate_price(price: str, order_type: str) -> float:
    """
    Validates the order price.
    - Required if order_type is LIMIT or STOP_MARKET.
    - Must be a positive number.
    """
    order_type_clean = order_type.strip().upper()
    
    if order_type_clean in ("LIMIT", "STOP_MARKET"):
        if not price:
            raise ValidationError(f"Price is required for '{order_type_clean}' orders.")
        
        try:
            price_val = float(price)
        except ValueError:
            raise ValidationError(f"Invalid price: '{price}'. Must be a valid number.")
        
        if price_val <= 0:
            raise ValidationError(f"Price must be a positive number (got {price_val}).")
        
        return price_val
    else:
        # For MARKET orders, price is not needed, but if provided, validate it or return None
        if price:
            try:
                price_val = float(price)
                if price_val <= 0:
                    raise ValidationError(f"Price must be a positive number (got {price_val}).")
                return price_val
            except ValueError:
                raise ValidationError(f"Invalid price: '{price}'. Must be a valid number.")
        return None
