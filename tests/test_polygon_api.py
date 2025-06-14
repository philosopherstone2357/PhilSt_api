import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from polygon_api import PolygonApi


def test_init_raises_without_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    with pytest.raises(ValueError):
        PolygonApi()
