import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from ibkr_api import IbkrApi


def test_get_order_id_wraps_to_one():
    api = IbkrApi(host='dummy', port=0, clientId=0)
    for _ in range(10000):
        api.get_order_id()
    assert api.get_order_id() == 1
