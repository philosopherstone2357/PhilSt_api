"""
Interative Broker API

Description: Interface class built from combination of ib_insync. 

Checkout IBKR API update:
https://interactivebrokers.github.io/tws-api
https://ib-insync.readthedocs.io/api.html
"""

from ib_insync import *

import time as systime
import datetime
import asyncio

IBKR_PERIOD_MAPPING = {
    "5m"  :  "5 mins",
    "10m" : "10 mins",
    "30m" : "30 mins",
    "1h"  :  "1 hour",
    "4h"  : "4 hours",
    "1d"  : "1 day"
}

class IbInsyncApi(IB):
    def __init__(self, host, port, clientId):
        IB.__init__(self)
        self.host = host
        self.port = port
        self.clientId = clientId

        self.contract = None

        self.reqId = 10000
        self.orderId = 1

    def connect(self):
        return super().connect(self.host, self.port, self.clientId)
    
    #def connect(self, timeout):
    #    return super().connect(self.host, self.port, self.clientId, timeout=timeout)

    def getCurrTime(self):
        # Current time is YYYY-MM-DD HH:mm:ss+zz:zz in datetime.datetime format
        currTime = super().reqCurrentTime()
        systime.sleep(1)

        # Convert to our conventional US/Eastern trading time
        baseTimeZone = currTime.utcoffset()
        usTimeZone = datetime.timedelta(hours=-5)
        currTimeUs = currTime + usTimeZone - baseTimeZone
        currTimeUsStr = currTimeUs.strftime("%Y%m%d %H:%M:%S US/Eastern")

        return currTimeUsStr

    def modifySession(self, host, port, clientId):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()

    def createContract(self, symbol, secType, exchange, currency):
        '''
        Create trade contract for corresponded symbol
        '''
        self.contract = Contract()
        self.contract.symbol = symbol
        self.contract.secType = secType
        self.contract.exchange = exchange
        self.contract.currency = currency
        return self.contract

    def isRegTradingHour(self, contract: Contract) -> int:
        '''
        Check if a contract under valid trading hour

        Args: Contract

        return: bool (Yes, No)
        '''
        # request for contract details
        contractDetail =  super().reqContractDetails(contract)

        # Note that tradingHours format:
        # "%Y%m%d:%H%M-%Y%m%d:%H%M;%Y%m%d:%H%M-%Y%m%d:%H%M:%Y%m%d:%H%M:CLOSED" Format length last for a week
        # It is being dissected as below
        tradingHours = contractDetail[0].tradingHours
        tradingRanges = tradingHours.split(';')

        # Convert serverTime string to datetime format
        currTime = self.getCurrTime()
        currTime = datetime.datetime.strptime(currTime, "%Y%m%d %H:%M:%S US/Eastern")

        for tradingRange in tradingRanges:
            closedKeyword = False

            if len(tradingRange) == 0: # string is empty
                pass
            if "CLOSED" in tradingRange:
                closedKeyword = True
            else:
                startTime, endTime = tradingRange.split('-')
                startTime = datetime.datetime.strptime(startTime, "%Y%m%d:%H%M")
                endTime = datetime.datetime.strptime(endTime, "%Y%m%d:%H%M")

                # Check if current time is within this trading range
                if not closedKeyword and startTime <= currTime <= endTime:
                    return 1
        return 0

    def getHistoricalData(self, contract:Contract, period, duration):
        '''
        Get Historical Data function by calling reqHistorical api

        Args:
            contract    (symbol contract)
            period      (candle stick pattern)
            duration    (Duration for the candle)

        return
            Dataframe of the symbol historical data
        '''
        rth = self.isRegTradingHour(contract)
        currTime = self.getCurrTime()
        bars = self.reqHistoricalData(contract, currTime, duration, IBKR_PERIOD_MAPPING[period], 'BID', rth, 1, False, [])
        dataframe = util.df(bars)
        systime.sleep(3)

        if dataframe.empty:
            print("[Warning]: getHistoricalData() Historical dataframe is empty.")

        return dataframe

    def getCashVal(self) -> list:
        '''
        Portfolio viewing API: get portfolio summary only using tags as input via .reqAccountSummary with 
        Parameters
        ------
        group	Default set to "All" to return account summary data for all accounts, or set to a specific Advisor Account Group name that has already been created in TWS Global Configuration.
        tags	a comma separated list with the desired tags:

        Return:
        run callback function self.accountDataTemp to get the account summary data
        '''
        try:
            accountName = self.managedAccounts()
            accSum = self.accountSummary(accountName[0])
        except Exception as e:
            print(e)
        return accSum