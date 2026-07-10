# ARIMA Price Forecasting Strategy
# Autoregressive Integrated Moving Average predictive trading script.

import yfinance as yf
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

def run_arima_trading_bot(ticker, train_period="6mo", test_days=30):
    """
    Performs sliding-window ARIMA forecasts and generates daily signals:
    1 (Buy) if the next day forecasted close is higher than current, else -1 (Sell).
    """
    # Fetch historical daily data
    df = yf.Ticker(ticker).history(period=train_period)
    if len(df) < 50:
        return df
        
    df['Signal'] = 0
    close_prices = df['Close'].tolist()
    signals = [0] * len(df)
    
    # Running predictive model for the last test_days window
    for i in range(len(df) - test_days, len(df)):
        train_series = close_prices[:i]
        try:
            # Fit a simple ARIMA(1,1,0) model
            model = ARIMA(train_series, order=(1, 1, 0))
            model_fit = model.fit()
            
            # Predict 1 step ahead
            forecast = model_fit.forecast(steps=1)[0]
            current = train_series[-1]
            
            # Signal based on prediction direction
            signals[i] = 1 if forecast > current else -1
        except Exception:
            # Fallback to hold
            signals[i] = 0
            
    df['Signal'] = signals
    df['Market_Return'] = df['Close'].pct_change()
    df['Strategy_Return'] = df['Signal'].shift(1) * df['Market_Return']
    
    df['Cum_Market_Return'] = (1 + df['Market_Return'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Return'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() - 1
    
    return df
