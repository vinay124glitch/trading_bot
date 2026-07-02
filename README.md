# Binance Futures Testnet Trading Bot (USDT-M)

A production-grade Python CLI trading bot designed to interact with the Binance Futures Testnet (USDT-M) environment. Built with robust input validation, clean exception handling, and hierarchical logging.

## Features
- **Market Orders**: Place buy/sell market orders instantly.
- **Limit Orders**: Place buy/sell limit orders (Good Till Cancel - GTC).
- **Stop-Market Orders (Bonus)**: Place stop-market orders triggered by an activation stop price.
- **CLI Modes**:
  - Command-line arguments: Run directly with script parameters.
  - Interactive Wizard: Run without parameters to launch a guided setup.
- **Input Validation**: Strict client-side validation of symbols, sides, order types, quantities, and prices before submitting requests to the API.
- **Dual Logging**: Clean output printed to console, while full payload/response and exception debug trace details are logged to a rolling file `trading_bot.log`.

---

## Directory Structure

```
trading_bot/
  bot/
    __init__.py
    client.py           # Binance Futures REST API wrapper
    orders.py           # Core order execution & mapping orchestrator
    validators.py       # Client-side input validation functions
    logging_config.py   # Dual-handler (file & console) logging setup
  cli.py                # Command-line interface & interactive wizard
  requirements.txt      # Project dependencies
  README.md             # Setup & usage guide
```

---

## Prerequisites

1. **Python**: Python 3.8 or higher.
2. **Binance Futures Testnet Account**:
   - Go to [Binance Futures Testnet website](https://testnet.binancefuture.com/).
   - Register or log in with your account.
   - Activate your Futures Account (virtual USDT funds will be allocated).
   - Under the "API Key" section at the bottom, click "Register API Key" or "Create API Key" to generate a Testnet `API Key` and `Secret Key`.

---

## Setup & Installation

1. Navigate to the `trading_bot` directory:
   ```bash
   cd trading_bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows (Command Prompt)**:
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell)**:
     ```powershell
     venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```

4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure credentials:
   Create a `.env` file in the root of the `trading_bot` directory and add your API credentials:
   ```env
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_API_SECRET=your_testnet_secret_key_here
   ```

---

## How to Run

### 1. Interactive Mode (Wizard)
If you run the CLI without any arguments, it will launch an interactive wizard:
```bash
python cli.py
```
*The wizard will guide you through entering the symbol, side, order type, quantity, price, and ask for confirmation before placing the order.*

### 2. Command-Line Arguments Mode
You can specify the order parameters directly via CLI flags.

#### **Market Buy Order**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

#### **Limit Sell Order**
```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.02 --price 3300.00
```

#### **Stop-Market Buy Order**
```bash
python cli.py --symbol SOLUSDT --side BUY --type STOP_MARKET --quantity 1.0 --price 140.00
```

---

## Logs and Auditing

- **Console Output**: Simple and user-friendly success/error notifications.
- **Log File (`trading_bot.log`)**: Located in the current working directory. It captures timestamps, log levels, file and line information, request parameters, response JSONs, and full exception stack traces for any API, network, or validation failures.

---

## Assumptions & Design Decisions

1. **HMAC-SHA256 Request Signing**: Implemented manually to avoid bloated library dependencies (like `python-binance`), allowing complete control over request timeouts, retries, and headers.
2. **Strict Client-Side Validation**: Minimizes unnecessary API calls by checking formats, choices, and positive bounds prior to submission.
3. **Query Parameter Order Constraint**: The signature must be the last query parameter in the request url, so it is concatenated explicitly as a trailing query component.
4. **Float Formatting**: Numbers are formatted using standard `.8f` and trimmed to prevent potential scientific notation issues during API URL construction.
