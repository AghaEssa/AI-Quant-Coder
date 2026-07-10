# RSI Divergence Strategy
# Relative Strength Index (RSI) trading bot using oversold and overbought bounds.

import yfinance as yf
import pandas as pd

def run_rsi_strategy(ticker, rsi_period=14, buy_bound=30, sell_bound=70, period="1y"):
    """
    Runs an RSI trading strategy.
    Signals buy (1) when RSI falls below buy_bound, and sell (-1) when it exceeds sell_bound.
    """
    df = yf.Ticker(ticker).history(period=period)
    if df.empty:
        return df

    # Calculate price differences
    delta = df['Close'].diff()
    
    # Calculate gain and loss rolling averages
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    
    # Calculate Relative Strength (RS) and RSI
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Generate signals
    df['Signal'] = 0
    df.loc[df['RSI'] < buy_bound, 'Signal'] = 1
    df.loc[df['RSI'] > sell_bound, 'Signal'] = -1
    
    # Calculate returns
    df['Market_Return'] = df['Close'].pct_change()
    # Forward fill signals to simulate holding position
    df['Position'] = df['Signal'].replace(0, method='ffill').shift(1).fillna(0)
    df['Strategy_Return'] = df['Position'] * df['Market_Return']
    
    df['Cum_Market_Return'] = (1 + df['Market_Return'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Return'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() - 1
    
    return df
