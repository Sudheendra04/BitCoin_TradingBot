from datetime import datetime
from tensorflow.keras.models import Sequential
import json
import numpy as np

# region imports
from AlgorithmImports import *
# endregion

class SquareYellowFalcon(QCAlgorithm):

    def Initialize(self):
        # Set Start Date to January 1, 2022
        self.SetStartDate(2022, 1, 1)

        # Set End Date to today's date
        end_date = datetime.now()
        self.SetEndDate(end_date.year, end_date.month, end_date.day)

        # Get model
        model_key = 'bitcoin_price_predictor'
        if self.ObjectStore.ContainsKey(model_key):
            model_str = self.ObjectStore.Read(model_key)
            config = json.loads(model_str)['config']
            self.model = Sequential.from_config(config)

        self.SetBrokerageModel(BrokerageName.Bitfinex, AccountType.Margin)  # Crypto brokerage
        self.SetCash(100000)  # Set Strategy Cash
        self.symbol = self.AddCrypto("BTCUSD", Resolution.Daily).Symbol
        self.SetBenchmark(self.symbol)

        # Arbitrage parameters
        self.arbitrage_symbol = self.AddCrypto("ETHUSD", Resolution.Daily).Symbol  # Arbitrage with ETHUSD
        self.arbitrage_allocation = 0.2  # Allocate 20% of total cash for arbitrage

        # Stop-loss parameters
        self.max_loss_pct = 0.05  # Max loss percentage to stop trading (5%)
        self.current_loss_pct = 0.0


    def OnData(self, data):
        if self.IsTradingAllowed():
            if self.GetPrediction() == "Up":
                self.SetHoldings(self.symbol, 1)
            else:
                self.SetHoldings(self.symbol, -0.5)

        # Perform arbitrage trading
        self.PerformArbitrage()

    def GetPrediction(self):
        # Get historical price data for BTCUSD
        history = self.History(self.symbol, 40).loc[self.symbol]

        if len(history) < 30:
            return "NotEnoughData"  # Return an appropriate value when there isn't enough data for prediction

        # Calculate price changes as features for the model
        history['close_change'] = history['close'].pct_change().fillna(0)
        history['volume_change'] = history['volume'].pct_change().fillna(0)

        # Prepare model input
        model_input = history[['close_change', 'volume_change']].tail(30).to_numpy().reshape((1, 30, 2))

        # Make prediction using the model
        prediction = self.model.predict(model_input)

        if prediction[0][0] > 0.5:
            return "Up"
        else:
            return "Down"

        def IsTradingAllowed(self):
            def IsTradingAllowed(self):
        # Check if trading is allowed based on stop-loss condition
                if self.current_loss_pct > self.max_loss_pct:
                 self.Liquidate()  # Stop trading when losses exceed the threshold
            return False
        return True

        def PerformArbitrage(self):
        # Check if there's enough cash to perform arbitrage
         if self.Portfolio.Cash < self.arbitrage_allocation * self.Portfolio.TotalPortfolioValue:
            return  # Not enough cash for arbitrage

        # Get the last available prices for BTCUSD and ETHUSD
        btc_usd_price = self.Securities[self.symbol].Price
        eth_usd_price = self.Securities[self.arbitrage_symbol].Price

        # Calculate the arbitrage percentage
        arbitrage_pct = (eth_usd_price - btc_usd_price) / btc_usd_price

        # Arbitrage Buy: Convert BTC to ETH when arbitrage percentage is positive
        if arbitrage_pct > 0:
            btc_to_sell = self.Portfolio[self.symbol].Quantity  # Sell all BTC
            eth_to_buy = btc_to_sell / btc_usd_price
            self.SetHoldings(self.symbol, 0)
            self.SetHoldings(self.arbitrage_symbol, self.arbitrage_allocation)
            self.Log(f"Arbitrage Buy: BTC -> ETH, Quantity: {btc_to_sell}, ETH to buy: {eth_to_buy}")

        # Arbitrage Sell: Convert ETH to BTC when arbitrage percentage is negative
        elif arbitrage_pct < 0:
            eth_to_sell = self.Portfolio[self.arbitrage_symbol].Quantity  # Sell all ETH
            btc_to_buy = eth_to_sell * btc_usd_price
            self.SetHoldings(self.arbitrage_symbol, 0)
            self.SetHoldings(self.symbol, -0.5)
            self.Log(f"Arbitrage Sell: ETH -> BTC, Quantity: {eth_to_sell}, BTC to buy: {btc_to_buy}")

        # Update stop-loss percentage
        self.current_loss_pct = (self.Portfolio.TotalUnrealizedProfit - self.Portfolio.TotalProfit) / self.Portfolio.TotalPortfolioValue

   
      
        def OnEndOfDay(self):
        # Rebalance the portfolio at the end of the day
         if self.IsTradingAllowed():
          self.SetHoldings(self.symbol, 0)  # Close all positions for the day