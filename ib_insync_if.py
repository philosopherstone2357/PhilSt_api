"""
Interative Broker API

Description: Interface class built from combination of ib_insync. 

Checkout IBKR API update:
https://interactivebrokers.github.io/tws-api
https://ib-insync.readthedocs.io/api.html
"""

from ib_insync import *
import pandas as pd
import datetime

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

        self.reqId = 10000
        self.orderId = 1
        self.prevSysTime = datetime.datetime.now(tz=datetime.timezone.utc)
        self.CurrTime = None

    def connect(self):
        return super().connect(self.host, self.port, self.clientId)

    def getCurrTime(self):
        """Get current time from IBKR server in US/Eastern timezone.
        TWS api has a limitation of no more than two requests per second.
        Hence, a time cache is used to prevent overloading the server.
        """
        # Current time is YYYY-MM-DD HH:mm:ss+zz:zz in datetime.datetime format
        if datetime.datetime.now(tz=datetime.timezone.utc) - self.prevSysTime > datetime.timedelta(seconds=1) or self.CurrTime is None:
            self.prevSysTime = datetime.datetime.now(tz=datetime.timezone.utc)
            self.CurrTime = self.reqCurrentTime()

        # Convert to our conventional US/Eastern trading time
        baseTimeZone = self.CurrTime.utcoffset()
        usTimeZone = datetime.timedelta(hours=-5)
        currTimeUs = self.CurrTime + usTimeZone - baseTimeZone
        currTimeUsStr = currTimeUs.strftime("%Y%m%d %H:%M:%S US/Eastern")

        return currTimeUsStr

    def modifySession(self, host, port, clientId):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()

    def createContract(self, symbol, secType, exchange, currency):
        '''
        !! DEPRECIATED function !! (We are no more creating contract using the api interface)
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
        contractDetail = super().reqContractDetails(contract)

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
                continue
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

    def getHistoricalData(self, period, duration, contract:Contract = None):
        '''
        Get Historical Data function by calling reqHistorical api

        Args:
            period      (candle stick pattern)
            duration    (Duration for the candle)
            contract    (symbol contract) - default to self.contract

        return
            Dataframe of the symbol historical data
        '''
        if contract is None:
            contract = self.contract
        rth = self.isRegTradingHour(contract)
        currTime = self.getCurrTime()
        bars = self.reqHistoricalData(contract, currTime, duration, IBKR_PERIOD_MAPPING[period], 'BID', rth, 1, False, [])
        dataframe = util.df(bars)

        if dataframe.empty:
            print("[Warning]: getHistoricalData() Historical dataframe is empty.")

        return dataframe

    def getAccountSummary(self) -> list:
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

    def getAccountSummaryDf(self) -> list:
        '''
        get account summary in dataframe
        '''
        accSum = self.getAccountSummary()
        # Convert AccountValue objects to dictionaries
        accSumDicts = [{'account': av.account,
                        'tag': av.tag,
                        'value': av.value,
                        'currency': av.currency,
                        'modelCode': av.modelCode} for av in accSum]
        accSumDf = pd.DataFrame(accSumDicts)
        assert accSumDf is not None, "accSumDf is empty"
        return accSumDf
    
    def getCashVal(self) -> float:
        '''
        get current cash value, how much available to buy
        '''
        accsum = self.getAccountSummary()
        cashValue = float(next((value for value in accsum if value.tag == 'AvailableFunds'), None).value)

        assert cashValue is not None, "Total Cash Value not found in the list."
        return cashValue

    def getTotalCashVal(self) -> float:
        '''
        get total portfolio value, how much we have
        '''
        # Finding AccountValue with tag equal to 'TotalCashValue'
        accsum = self.getAccountSummary()
        totalCashValue = float(next((value for value in accsum if value.tag == 'TotalCashValue'), None).value)

        assert totalCashValue is not None, "Total Cash Value not found in the list."
        return totalCashValue
    
    def bracketOrder(
            self, action: str, quantity: float,
            limitPrice: float, takeProfitPrice: float,
            stopLossPrice: float, transmit : bool, **kwargs) -> BracketOrder:
        """
        ###############################################
         Override parent class bracket order function 
        ###############################################
        Create a limit order that is bracketed by a take-profit order and
        a stop-loss order. Submit the bracket like:

        .. code-block:: python

            for o in bracket:
                ib.placeOrder(contract, o)

        https://interactivebrokers.github.io/tws-api/bracket_order.html

        Args:
            action: 'BUY' or 'SELL'.
            quantity: Size of order.
            limitPrice: Limit price of entry order.
            takeProfitPrice: Limit price of profit order.
            stopLossPrice: Stop price of loss order.
        """
        assert action in ('BUY', 'SELL')
        reverseAction = 'BUY' if action == 'SELL' else 'SELL'
        parent = LimitOrder(
            action, quantity, limitPrice,
            orderId=self.client.getReqId(),
            transmit=transmit,
            **kwargs)
        takeProfit = LimitOrder(
            reverseAction, quantity, takeProfitPrice,
            orderId=self.client.getReqId(),
            transmit=transmit,
            parentId=parent.orderId,
            **kwargs)
        stopLoss = StopOrder(
            reverseAction, quantity, stopLossPrice,
            orderId=self.client.getReqId(),
            transmit=transmit,
            parentId=parent.orderId,
            **kwargs)
        return BracketOrder(parent, takeProfit, stopLoss)