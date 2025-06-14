# Philosopher Stone API

This repository contains API wrappers for accessing and interacting with stock data.

1. API wrapper for `ib_insync`
2. API wrapper for `ib_api`
3. API wrapper for `polygon_api`

## Examples

Example scripts demonstrating how to use the two wrappers are available in the
`examples` directory. They expect that the Interactive Brokers Trader Workstation
(TWS) or IB Gateway is running on `localhost` (paper account works fine).

Install dependencies:

```bash
pip install ib_insync ibapi pandas requests
```

Run the examples:

```bash
python examples/example_ib_insync.py
python examples/example_ibkr_api.py
python examples/example_polygon_api.py
```

The `PolygonApi` example expects an API key set in the environment variable
`POLYGON_API_KEY`.

## Running tests

Execute the unit tests with:

```bash
pytest -q
```
