import yfinance as yf
import pandas as pd
import numpy as np

def generate_mock_stock_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """
    Generates high-quality mock stock data for fallback when yfinance is offline or rate-limited.
    """
    end_dt = pd.Timestamp.now().normalize()
    start_dt = end_dt - pd.Timedelta(days=days)
    date_range = pd.date_range(start=start_dt, end=end_dt, freq="B") # Business days only
    
    # Generate a realistic random walk with drift
    np.random.seed(42 + len(ticker)) # Ticker-specific stable seed
    start_price = 150.0 if ticker == "AMD" else 100.0 if ticker == "NVDA" else 80.0
    returns = np.random.normal(loc=0.0006, scale=0.018, size=len(date_range))
    price_path = start_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame(index=date_range)
    df['Close'] = price_path
    df['Open'] = df['Close'] * (1 + np.random.normal(0, 0.006, len(df)))
    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.009, len(df))))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.009, len(df))))
    df['Volume'] = np.random.randint(1000000, 10000000, size=len(df))
    
    # Add attribute flag for offline mock indicator
    df.attrs['is_mock'] = True
    return df

def fetch_stock_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical stock data using yfinance. Falls back to mock data if offline/unreachable.
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No yfinance data returned for ticker '{ticker}'")
        # Remove timezone offset if present to prevent tz-aware comparison error
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.attrs['is_mock'] = False
        return df
    except Exception as e:
        print(f"yfinance failed to fetch '{ticker}' (period={period}): {str(e)}. Falling back to generated mock data.")
        days = 730 if "2y" in period else 365
        df = generate_mock_stock_data(ticker, days=days)
        return df

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add baseline technical indicators (Simple Moving Averages, RSI, MACD) to the DataFrame.
    """
    df = df.copy()
    
    # Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # MACD (Moving Average Convergence Divergence)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    return df
