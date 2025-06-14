"""Usage example for PolygonApi."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
# Ensure repository root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from polygon_api import PolygonApi

# Path to your .env file
env_path = Path(__file__).parent / 'POLYGON_CONNECT.env'
load_dotenv(dotenv_path=env_path)

def main():
    api = PolygonApi()  # Reads API key from POLYGON_API_KEY
    status = api.get_market_status()
    print("Market status:", status)

    data = api.get_historical_data(
        ticker="AAPL",
        multiplier=1,
        timespan="day",
        from_date="2024-01-01",
        to_date="2024-01-07",
    )
    print("Historical bars count:", len(data.get("results", [])))


if __name__ == "__main__":
    main()

