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
    "10m" : "10 mins",
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
        # self.reqId = ibkrApi.reqIds(-1) + 10000
        # self.orderId = ibkrApi.reqIds(-1) 
        self.reqId = 10000
        self.orderId = 1
        self.contract = None
        self.histDataTemp = []
        self.conDetTemp = Contract()
        self.serverTime = None
        self.accountDataTemp = []
       
    def connect(self):
        return super().connect(self.host, self.port, self.clientId)

    def modifySession(self, host, port, clientId):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()

    def resetHistDataTemp(self) -> None:
        self.histDataTemp = []
    
    def resetAccountDataTemp(self) -> None:
        print("reset account data temp")
        self.accountDataTemp = []

    def get_order_id(self):
        '''
        Segregation between reqId and orderId. Chances are you will only have 1M orderIds but unlimited reqIDs in your lifetime.
        Auto orderId generator that appends +1 every time it is being called. Could use .reqIds(-1) to verify.
        '''
        # if ibkrApi.reqIds(-1) relook into reset
        current_id = self.orderId
        self.orderId = (self.orderId + 1) % 10000  # Reset to 1 if it exceeds 9999
        return current_id

    def get_req_id(self):
        '''
        Segregation between reqId and orderId. Chances are you will only have 1M orderIds but unlimited reqIDsin your lifetime.
        Auto reqId generator that appends +1 every time it is being called. Could use .reqIds(-1) to verify.
        '''
        current_id = self.reqId
        self.reqId = (self.reqId + 1) % 20000  # Reset to 10000 if it exceeds 19999
        return current_id

    def createContract(self, symbol, secType, exchange, currency):
        self.contract = Contract()
        self.contract.symbol = symbol
        self.contract.secType = secType
        self.contract.exchange = exchange
        self.contract.currency = currency
        return self.contract

    #! [bracket]
    def BracketOrder(self, parentOrderId:int, action:str, quantity:float, 
                     limitPrice:float, takeProfitLimitPrice:float, 
                     stopLossPrice:float):
        """ 
        Args:   
        parentOrderId: generated from api.get_order_id()
        action: BUY or SELL
        quantity: number of positions 
        limitPrice: float
        takeProfitLimitPrice: float
        stopLossPrice: float
           
        Description: 
        #/ Bracket orders are designed to help limit your loss and lock in a profit by "bracketing" an order with two opposite-side orders. 
        #/ A BUY order is bracketed by a high-side sell limit order and a low-side sell stop order. A SELL order is bracketed by a high-side buy 
        #/ stop order and a low side buy limit order.
        #/ Products: CFD, BAG, FOP, CASH, FUT, OPT, STK, WAR

        Returns: bracketOrder: list of Order(s)
        """
        #This will be our main or "parent" order
        parent = Order()
        parent.orderId = parentOrderId
        print(1)
        parent.action = action
        parent.orderType = "LMT"
        parent.totalQuantity = quantity
        parent.lmtPrice = limitPrice
        #The parent and children orders will need this attribute set to False to prevent accidental executions.
        #The LAST CHILD will have it set to True, 
        parent.transmit = False

        takeProfit = Order()
        takeProfit.orderId = parentOrderId + 1
        takeProfit.action = "SELL" if action == "BUY" else "BUY"
        takeProfit.orderType = "LMT"
        takeProfit.totalQuantity = quantity
        takeProfit.lmtPrice = takeProfitLimitPrice
        takeProfit.parentId = parentOrderId
        takeProfit.transmit = False

        stopLoss = Order()
        stopLoss.orderId = parentOrderId + 2
        stopLoss.action = "SELL" if action == "BUY" else "BUY"
        stopLoss.orderType = "STP"
        #Stop trigger price
        stopLoss.auxPrice = stopLossPrice
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parentOrderId
        #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
        #to activate all its predecessors
        stopLoss.transmit = True
        bracketOrder = [parent, takeProfit, stopLoss]
        return bracketOrder

    def isRegTradingHour(self) -> bool:
        reqId = self.get_req_id()
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
        rth = self.isRegTradingHour()
        reqId = self.get_req_id()
        #reqId updated by XL need double check
        self.reqHistoricalData(reqId, self.contract, self.serverTime, duration, IBKR_PERIOD_MAPPING[period], 'BID', rth, 1, False, [])
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

# Added other portfolio viewing API
    def error(self, reqId, errorCode, errorString, errorHint):
        print("Error: ", reqId, " ", errorCode, " ", errorString, " ", errorHint)

    def getCashVal(self, tags:str):
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
            reqId = self.get_req_id()
            self.resetAccountDataTemp()
            self.reqAccountSummary(reqId, "All", tags)
            systime.sleep(1)  
            self.cancelAccountSummary(reqId)
            return self.accountDataTemp
        except Exception as e:
            print(e)
            return []

    # def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float,
    #                     averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        '''
        Portfolio viewing API
        '''
    #     try:
    #         super().updatePortfolio(contract, position, marketPrice, marketValue,
    #                                 averageCost, unrealizedPNL, realizedPNL, accountName)
    #         print("UpdatePortfolio.", "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:", contract.exchange,
    #           "Position:", position, "MarketPrice:", marketPrice, "MarketValue:", marketValue, "AverageCost:", averageCost,
    #           "UnrealizedPNL:", unrealizedPNL, "RealizedPNL:", realizedPNL, "AccountName:", accountName)
    #     except Exception as e:
    #         print(e)
    #         return []

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        '''
        Callback function
        '''
        super().accountSummary(reqId, account, tag, value, currency)
        self.accountDataTemp.append({
            "AccountSummary. ReqId": reqId,
            "Tag": tag,
            "Value": value, 
            "Currency": currency, 
            "AccountName": account 
        })

    def accountSummaryEnd(self, reqId: int):
        '''
        Callback function that terminate the .reqAccountSummarygicom request
        '''
        super().accountSummaryEnd(reqId)
        print("AccountSummaryEnd.Curr ReqId:", reqId)
        print("Next Valid ID:",reqId+1)

    def updateAccountTime(self, timeStamp: str):
        super().updateAccountTime(timeStamp)
        print("UpdateAccountTime. Time:", timeStamp)

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        print("AccountDownloadEnd. Account:", accountName)

    def runLoop(self):
            self.run()
       