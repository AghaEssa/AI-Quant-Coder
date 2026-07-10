# MACD Trend Indicator Strategy
# Moving Average Convergence Divergence crossover signals with simple holding logic.

import yfinance as yf
import pandas as pd

def run_macd_strategy(ticker, fast_span=12, slow_span=26, signal_span=9, period="1y"):
    """
    Calculates MACD, Signal Line, and MACD Histogram.
    Signals buy (1) when MACD crosses above Signal Line, and sell (-1) when it crosses below.
    """
    df = yf.Ticker(ticker).history(period=period)
    if df.empty:
        return df
        
    # Calculate Exponential Moving Averages (EMA)
    df['EMA_Fast'] = df['Close'].ewm(span=fast_span, adjust=False).mean()
    df['EMA_Slow'] = df['Close'].ewm(span=slow_span, adjust=False).mean()
    
    # MACD Line and Signal Line
    df['MACD'] = df['EMA_Fast'] - df['EMA_Slow']
    df['Signal_Line'] = df['MACD'].ewm(span=signal_span, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
    
    # Signal Crossover
    df['Signal'] = 0
    df.loc[df['MACD'] > df['Signal_Line'], 'Signal'] = 1
    df.loc[df['MACD'] < df['Signal_Line'], 'Signal'] = -1
    
    # Calculate returns
    df['Market_Return'] = df['Close'].pct_change()
    df['Strategy_Return'] = df['Signal'].shift(1) * df['Market_Return']
    
    df['Cum_Market_Return'] = (1 + df['Market_Return'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Return'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() - 1
    
    return df
