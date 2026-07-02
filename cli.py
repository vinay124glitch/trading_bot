import os
import sys
import argparse
from typing import Optional
from dotenv import load_dotenv

# Add current directory to path to ensure imports work when executed from root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.logging_config import setup_logging
from bot.orders import execute_order
from bot.validators import ValidationError
from bot.client import BinanceError

# Initialize logging before any actions
logger = setup_logging()

def print_banner():
    """Prints a styled terminal banner for the trading bot."""
    banner = """
===================================================
     BINANCE FUTURES TESTNET TRADING BOT (USDT-M)
===================================================
    """
    print(banner)

def run_interactive() -> dict:
    """Runs an interactive wizard to prompt the user for order details."""
    print_banner()
    print("Interactive Order Wizard (Press Ctrl+C to cancel at any time)\n")
    
    # 1. Symbol
    symbol = input("Enter Trading Symbol [BTCUSDT]: ").strip().upper()
    if not symbol:
        symbol = "BTCUSDT"
        
    # 2. Side
    side = ""
    while side not in ("BUY", "SELL"):
        side_input = input("Enter Side (BUY/SELL): ").strip().upper()
        if side_input in ("BUY", "SELL"):
            side = side_input
        else:
            print("Error: Side must be either BUY or SELL.")

    # 3. Order Type
    order_type = ""
    valid_types = ("MARKET", "LIMIT", "STOP_MARKET")
    while order_type not in valid_types:
        type_input = input(f"Enter Order Type ({'/'.join(valid_types)}): ").strip().upper()
        if type_input in valid_types:
            order_type = type_input
        else:
            print(f"Error: Order type must be one of: {', '.join(valid_types)}")

    # 4. Quantity
    quantity = ""
    while not quantity:
        qty_input = input("Enter Quantity: ").strip()
        if qty_input:
            quantity = qty_input
        else:
            print("Error: Quantity cannot be empty.")

    # 5. Price (only if LIMIT or STOP_MARKET)
    price = None
    if order_type in ("LIMIT", "STOP_MARKET"):
        price_label = "Limit Price" if order_type == "LIMIT" else "Stop Price (Activation)"
        while not price:
            price_input = input(f"Enter {price_label}: ").strip()
            if price_input:
                price = price_input
            else:
                print(f"Error: {price_label} is required for {order_type} orders.")

    print("\n--- Order Summary to Submit ---")
    print(f"Symbol:     {symbol}")
    print(f"Side:       {side}")
    print(f"Type:       {order_type}")
    print(f"Quantity:   {quantity}")
    if price:
        print(f"Price:      {price}")
    print("-------------------------------")

    confirm = input("Confirm order placement? (y/n) [n]: ").strip().lower()
    if confirm != "y":
        print("Order cancelled by user.")
        sys.exit(0)

    return {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "price": price
    }

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Retrieve API Credentials
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    # Command line argument parser
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet (USDT-M) Trading Bot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Market Buy
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
  
  # Limit Sell
  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3200.50
  
  # Stop-Market Buy (Activation Price)
  python cli.py --symbol SOLUSDT --side BUY --type STOP_MARKET --quantity 1.0 --price 145.00
  
  # Interactive mode (wizard)
  python cli.py
        """
    )
    parser.add_argument("--symbol", help="Trading Symbol (e.g. BTCUSDT)")
    parser.add_argument("--side", choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP_MARKET"], help="Order type")
    parser.add_argument("--quantity", help="Order quantity")
    parser.add_argument("--price", help="Order price (Required for LIMIT and STOP_MARKET)")

    args = parser.parse_args()

    # Determine whether to run interactive mode
    is_interactive = not any([args.symbol, args.side, args.type, args.quantity])

    # If credentials are not set, stop immediately
    if not api_key or not api_secret:
        print("Error: Missing API Credentials.", file=sys.stderr)
        print("Please set BINANCE_API_KEY and BINANCE_API_SECRET in your environment or a .env file.", file=sys.stderr)
        logger.error("API credentials missing. Execution aborted.")
        sys.exit(1)

    try:
        if is_interactive:
            order_params = run_interactive()
        else:
            # Validate command-line parameters presence
            if not args.symbol or not args.side or not args.type or not args.quantity:
                parser.print_usage()
                print("\nError: --symbol, --side, --type, and --quantity are all required for non-interactive mode.", file=sys.stderr)
                sys.exit(1)
                
            order_params = {
                "symbol": args.symbol,
                "side": args.side,
                "type": args.type,
                "quantity": args.quantity,
                "price": args.price
            }

        # Format Request Summary Output
        print("\n>>> Submitting Order Request...")
        print(f"    Symbol:    {order_params['symbol']}")
        print(f"    Side:      {order_params['side']}")
        print(f"    Type:      {order_params['type']}")
        print(f"    Quantity:  {order_params['quantity']}")
        if order_params['price']:
            price_label = "Stop Price" if order_params['type'] == "STOP_MARKET" else "Limit Price"
            print(f"    {price_label}: {order_params['price']}")
        print("-" * 40)

        # Execute
        result = execute_order(
            api_key=api_key,
            api_secret=api_secret,
            symbol=order_params["symbol"],
            side=order_params["side"],
            order_type=order_params["type"],
            quantity=order_params["quantity"],
            price=order_params["price"]
        )

        # Format Success Response Output
        print("\n>>> Order Placed Successfully!")
        print(f"    Order ID:     {result['orderId']}")
        print(f"    Status:       {result['status']}")
        print(f"    Executed Qty: {result['executedQty']}")
        print(f"    Average Price: {result['avgPrice']}")
        print("=" * 40)

    except ValidationError as e:
        print(f"\n[Validation Error] {e}", file=sys.stderr)
        logger.error(f"Execution failed due to validation: {e}")
        sys.exit(1)
    except BinanceError as e:
        print(f"\n[Binance API Error] {e}", file=sys.stderr)
        logger.error(f"Execution failed due to API/Network error: {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Unexpected Error] {e}", file=sys.stderr)
        logger.error(f"Execution failed due to unexpected error: {e}", exc_info=True)
        sys.exit(3)

if __name__ == "__main__":
    main()
