"""Usage example for the :class:`IbInsyncApi` wrapper."""

import os
import sys

# Ensure the repository root is on the Python path when running directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ib_insync_if import IbInsyncApi
from ib_insync import Contract


def main():
    # Connect to TWS or IB Gateway running on localhost with paper trading port
    api = IbInsyncApi(host="127.0.0.1", port=7497, clientId=1)
    api.connect()

    # Build a contract object for AAPL stock traded on SMART in USD
    contract = api.createContract(symbol="AAPL", secType="STK", exchange="SMART", currency="USD")

    # Request one week of daily bars
    data = api.getHistoricalData(period="1d", duration="1 W", contract=contract)
    print(data)

    api.disconnect()


if __name__ == "__main__":
    main()