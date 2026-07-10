# Moving Average Crossover Strategy
# Standard quantitative trading strategy using short-term and long-term moving averages.

import yfinance as yf
import pandas as pd
import numpy as np

def run_ma_crossover_strategy(ticker, short_window=20, long_window=50, period="1y"):
    """
    Downloads historical data and runs a simple moving average crossover strategy.
    Returns the dataframe with signal markings and backtested returns.
    """
    # Fetch historical data
    df = yf.Ticker(ticker).history(period=period)
    if df.empty:
        return df
        
    # Calculate Simple Moving Averages (SMA)
    df['SMA_Short'] = df['Close'].rolling(window=short_window).mean()
    df['SMA_Long'] = df['Close'].rolling(window=long_window).mean()
    
    # Generate signals: 1 is buy, -1 is sell, 0 is hold
    df['Signal'] = 0
    df['Signal'] = np.where(df['SMA_Short'] > df['SMA_Long'], 1, -1)
    
    # Calculate daily returns and strategy returns
    df['Market_Return'] = df['Close'].pct_change()
    df['Strategy_Return'] = df['Signal'].shift(1) * df['Market_Return']
    
    # Calculate cumulative returns
    df['Cum_Market_Return'] = (1 + df['Market_Return'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Return'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() - 1
    
    return df
