"""Polygon API Wrapper."""

import os
from typing import Optional, Dict, Any
import requests


class PolygonApi:
    """Simple wrapper around the Polygon.io REST API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the client with an API key.

        If *api_key* is not supplied it will be read from the ``POLYGON_API_KEY``
        environment variable.
        """
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("Polygon API key not provided and POLYGON_API_KEY env var not set")

        self.base_url = "https://api.polygon.io"

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Internal helper for GET requests."""
        url = f"{self.base_url}{path}"
        params = params or {}
        params["apiKey"] = self.api_key
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_market_status(self) -> Dict[str, Any]:
        """Return the current market status."""
        return self._get("/v1/marketstatus/now")

    def get_historical_data(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        from_date: str,
        to_date: str,
        **params: Any,
    ) -> Dict[str, Any]:
        """Fetch aggregated historical data for a ticker.

        Parameters are passed straight through to Polygon. ``from_date`` and
        ``to_date`` should be ``YYYY-MM-DD`` strings.
        """
        path = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        return self._get(path, params)

    def get_last_trade(self, ticker: str) -> Dict[str, Any]:
        """Return the last trade for *ticker*."""
        return self._get(f"/v2/last/trade/{ticker}")
