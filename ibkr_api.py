"""
Interative Broker API

Checkout IBKR API update:
https://interactivebrokers.github.io/tws-api
"""

from ibapi.client import EClient
from ibapi.common import BarData
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

import time as systime
import datetime

IBKR_PERIOD_MAPPING = {
    "5m"  :  "5 mins",
    "30m" : "30 mins",
    "1h"  :  "1 hour",
    "4h"  : "4 hours",
    "1d"  : "1 day"
}

class IbkrApi(EWrapper, EClient):
    def __init__(self, host, port, clientId):
        EClient.__init__(self, self)
        self.host = host
        self.port = port
        self.clientId = clientId

        # List of temporary variables
        self.requestId = 2000
        self.contract = None
        self.histDataTemp = []
        self.conDetTemp = Contract()
        self.serverTime = None

    def connect(self):
        return super().connect(self.host, self.port, self.clientId)

    def modifySession(self, host, port, clientId):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()

    def resetHistDataTemp(self) -> None:
        self.histDataTemp = []

    # Pending Xian Li verify this, I probably wrong with request ID
    def updateReqId(self) -> None:
        self.requestId += 1
        if self.requestId > 9999:
            self.requestId = 2000

    def createContract(self, symbol, secType, exchange, currency):
        self.contract = Contract()
        self.contract.symbol = symbol
        self.contract.secType = secType
        self.contract.exchange = exchange
        self.contract.currency = currency

    def isRegTradingHour(self, reqId) -> bool:

        # request for contract details
        self.reqContractDetails(reqId, self.contract)

        # time allow API to get data 
        systime.sleep(3)

        contractDetail = self.conDetTemp

        # Note that tradingHours format:
        # "%Y%m%d:%H%M-%Y%m%d:%H%M;%Y%m%d:%H%M-%Y%m%d:%H%M:%Y%m%d:%H%M:CLOSED" Format length last for a week
        # It is being dissected as below

        tradingHours = contractDetail.tradingHours
        tradingRanges = tradingHours.split(';')

        for tradingRange in tradingRanges:
            closedKeyword = False

            if len(tradingRange) == 0: # string is empty
                pass 

            elif "CLOSED" in tradingRange:
                closedKeyword = True

            else:
                startTime, endTime = tradingRange.split('-')
                startTime = datetime.datetime.strptime(startTime, "%Y%m%d:%H%M")
                endTime = datetime.datetime.strptime(endTime, "%Y%m%d:%H%M")

                # Check if current time is within this trading range
                currTime = self.getCurrTime()
                # Convert serverTime string to datetime format
                currTime = datetime.datetime.strptime(currTime, "%Y%m%d %H:%M:%S US/Eastern")

                if not closedKeyword and startTime <= currTime <= endTime:
                    return 1

        return 0

    def contractDetails(self, reqId, contractDetails):
        """
        Call back function from reqContractDetails()
        """
        self.conDetTemp = contractDetails

    def getCurrTime(self):

        self.reqCurrentTime()
        systime.sleep(0.1)

        """
        Output is string format: "%Y%m%d %H:%M:%S US/Eastern"
        You might need to convert to datetime format if required:
        currTime = datetime.datetime.strptime(currTime, "%Y%m%d %H:%M:%S US/Eastern")
        """
        return self.serverTime

    def currentTime(self, time):
        """
        Call back function from api: reqCurrentTime()
        """
        # Get the local time offset
        currentSysTime = systime.time()
        localTime = systime.localtime(currentSysTime)
        localOffsetSec = systime.mktime(localTime) - currentSysTime

        # Calculate the offset in hours
        localOffsetHr = datetime.timedelta(hours=round(localOffsetSec / 3600))

        #ukOffset = datetime.timedelta(hours=0)  # UK is UTC+0
        usEasternOffset = datetime.timedelta(hours=-4)  # US/Eastern is UTC-4

        self.serverTime = datetime.datetime.fromtimestamp(time) + (usEasternOffset - localOffsetHr)
        self.serverTime = self.serverTime.strftime("%Y%m%d %H:%M:%S US/Eastern")

    def getHistoricalData(self, period, duration):

        self.resetHistDataTemp()
        rth = self.isRegTradingHour(1000)

        self.reqHistoricalData(self.requestId, self.contract, self.serverTime, duration, IBKR_PERIOD_MAPPING[period], 'BID', rth, 1, False, [])
        systime.sleep(5)

        return self.histDataTemp

    def historicalData(self, reqId: int, bar: BarData):
        self.histDataTemp.append({
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low" : bar.low,
            "close": bar.close,
            "volume": bar.volume
        })

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        print('The next valid order id is: ', self.nextorderId)

    def orderStatus(self, orderId, status, filled, remaining, avgFullPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print('orderStatus - orderid:', orderId, 'status:', status, 'filled', filled, 'remaining', remaining, 'lastFillPrice', lastFillPrice)

    def openOrder(self, orderId, contract, order, orderState):
        print('openOrder id:', orderId, contract.symbol, contract.secType, '@', contract.exchange, ':', order.action, order.orderType, order.totalQuantity, orderState.status)

    def execDetails(self, reqId, contract, execution):
        print('Order Executed: ', reqId, contract.symbol, contract.secType, contract.currency, execution.execId, execution.orderId, execution.shares, execution.lastLiquidity)

    def runLoop(self):
        self.run()