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
        # Conection parameters
        self.host = host
        self.port = port
        self.clientId = clientId

        # Request and Order IDs
        self.reqId = 10000
        self.orderId = 1

        # Variables for storing temporary data
        self.contract_list =   []
        self.hist_data_temp =  []
        self.conDetTemp =      None
        self.serverTime =      None
        self.accountDataTemp = []
       
    def connect(self):
        return super().connect(self.host, self.port, self.clientId)

    def modifySession(self, host, port, clientId):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()
    
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

    def create_contract(self, symbol, sec_type, exchange, currency) -> Contract:
        """
        Create trade contract for corresponded symbol
        Args:
        symbol:   str, e.g. "AAPL"
        sec_type:  str, e.g. "STK" for stock, "FUT" for futures
        exchange: str, e.g. "SMART" for smart routing, "NYSE" for New York Stock Exchange
        currency: str, e.g. "USD" for US Dollar, "EUR" for Euro

        Returns:
        contract: Contract object with specified parameters
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        self.contract_list.append(contract)

        return contract

    #! [bracket]
    def BracketOrder(self, parentOrderId:int, action:str, quantity:float, 
                     limitPrice:float, takeProfitLimitPrice:float, 
                     stopLossPrice:float):
        """ 
        Args:   
        parentOrderId:        generated from api.get_order_id()
        action:               BUY or SELL
        quantity:             number of positions 
        limitPrice:           float
        takeProfitLimitPrice: float
        stopLossPrice:        float
           
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

    def isRegTradingHour(self, contract) -> bool:
        """
        Check if current time is within regular trading hours for the contract.

        Note that tradingHours format:
        "%Y%m%d:%H%M-%Y%m%d:%H%M;%Y%m%d:%H%M-%Y%m%d:%H%M:%Y%m%d:%H%M:CLOSED" 
        Format length last for a week, It is being dissected as below
        """
        reqId = self.get_req_id()
        self.reqContractDetails(reqId, contract)
        systime.sleep(3)
        contractDetail = self.conDetTemp
        tradingHours = contractDetail.tradingHours.split(';')

        for tradingRange in tradingHours:
            closedKeyword = False

            if len(tradingRange) == 0:
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
        # Example: ukOffset = datetime.timedelta(hours=0)  # UK is UTC+0
        usEasternOffset = datetime.timedelta(hours=-4)     # US/Eastern is UTC-4
        self.serverTime = datetime.datetime.fromtimestamp(time) + (usEasternOffset - localOffsetHr)
        self.serverTime = self.serverTime.strftime("%Y%m%d %H:%M:%S US/Eastern")

    def get_historical_data(self, contract, period, duration):
        """
        Get Historical Data function by calling reqHistorical api
        Args:
            contract: Contract object for the symbol
            period: str, e.g. "5m", "1h", "1d"
            duration: str, e.g. "1 D", "1 W", "1 M"
        Returns:
            hist_data_temp: list of historical data bars
        """
        self.reset_hist_data_temp()
        rth = self.isRegTradingHour(contract)
        reqId = self.get_req_id()
        self.reqHistoricalData(reqId, contract, self.serverTime, duration, IBKR_PERIOD_MAPPING[period], 'BID', rth, 1, False, [])
        systime.sleep(5)

        return self.hist_data_temp

    def reset_hist_data_temp(self) -> None:
        self.hist_data_temp = []

    def historicalData(self, reqId: int, bar: BarData):
        """
        Call back function from reqHistoricalData(), User should not call this function directly.
        """
        self.hist_data_temp.append({
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

    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        """
        Portfolio viewing API
        """
        try:
            super().updatePortfolio(
                contract,
                position,
                marketPrice,
                marketValue,
                averageCost,
                unrealizedPNL,
                realizedPNL,
                accountName,
            )
            print(
                "UpdatePortfolio.",
                "Symbol:",
                contract.symbol,
                "SecType:",
                contract.secType,
                "Exchange:",
                contract.exchange,
                "Position:",
                position,
                "MarketPrice:",
                marketPrice,
                "MarketValue:",
                marketValue,
                "AverageCost:",
                averageCost,
                "UnrealizedPNL:",
                unrealizedPNL,
                "RealizedPNL:",
                realizedPNL,
                "AccountName:",
                accountName,
            )
        except Exception as e:
            print(e)
            return []

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

    def run(self):
        super().run()
        systime.sleep(3)
