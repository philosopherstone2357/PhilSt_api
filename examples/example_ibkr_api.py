"""Usage example for the :class:`IbkrApi` wrapper."""

import os
import sys

# Ensure the repository root is on the Python path when running directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ibkr_api import IbkrApi
import threading

def main():
    # Connect to TWS or IB Gateway running on localhost with paper trading port
    api = IbkrApi(host="127.0.0.1", port=7497, clientId=1)
    api.connect()

    thread = threading.Thread(target=api.run, daemon=True)
    thread.start()

    # Build a contract object for AAPL stock traded on SMART in USD
    contract = api.create_contract(symbol="AAPL", sec_type="STK", exchange="SMART", currency="USD")

    # Required to initialize server time before requesting historical data
    api.reqCurrentTime()
    api.getCurrTime()

    # Request one week of daily bars
    bars = api.get_historical_data(contract=contract, period="1d", duration="1 W")
    print(bars)

    api.disconnect()
    thread.join()


if __name__ == "__main__":
    main()