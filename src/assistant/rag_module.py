import os
import re
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Default templates to write if the directory is empty
TEMPLATES = {
    "moving_average_crossover.py": '''# Moving Average Crossover Strategy
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
''',

    "rsi_divergence_bot.py": '''# RSI Divergence Strategy
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
''',

    "macd_trend_crossover.py": '''# MACD Trend Indicator Strategy
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
''',

    "arima_forecast_trader.py": '''# ARIMA Price Forecasting Strategy
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
'''
}

class TradingRAG:
    def __init__(self, scripts_dir="data/trading_scripts", cache_file="data/vector_db_cache.pkl"):
        self.scripts_dir = scripts_dir
        self.cache_file = cache_file
        self.chunks = []       # List of dict: {"file": filename, "content": code_chunk}
        self.vectorizer = None
        self.tfidf_matrix = None
        
        # Ensure workspace environment is configured
        os.makedirs(self.scripts_dir, exist_ok=True)
        self.ensure_default_templates()
        self.load_index()

    def ensure_default_templates(self):
        """
        Populate the directory with default sample templates if empty.
        """
        existing_files = [f for f in os.listdir(self.scripts_dir) if f.endswith(".py")]
        if not existing_files:
            print("Populating RAG with default trading templates...")
            for filename, content in TEMPLATES.items():
                filepath = os.path.join(self.scripts_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

    def get_indexed_files(self):
        """
        Returns a list of all files in the scripts folder.
        """
        try:
            return [f for f in os.listdir(self.scripts_dir) if f.endswith(".py")]
        except Exception:
            return []

    def chunk_file(self, filename, content):
        """
        Splits Python file content into chunks based on class/def declarations
        or falls back to overlapping line-based chunking.
        """
        chunks = []
        lines = content.splitlines()
        
        # Method 1: Split by def/class blocks
        pattern = re.compile(r'^(def |class )\w+')
        block_indices = [idx for idx, line in enumerate(lines) if pattern.match(line)]
        
        if len(block_indices) >= 2:
            # We have multiple functions/classes. Segment by declaration boundaries
            block_indices.append(len(lines))  # Add final line index
            for start_idx, end_idx in zip(block_indices[:-1], block_indices[1:]):
                chunk_lines = lines[start_idx:end_idx]
                chunk_text = "\n".join(chunk_lines).strip()
                if chunk_text:
                    chunks.append({"file": filename, "content": chunk_text})
        else:
            # Method 2: Sliding window of 25 lines with 5 lines overlap
            window_size = 25
            overlap = 5
            for i in range(0, len(lines), window_size - overlap):
                chunk_lines = lines[i:i + window_size]
                chunk_text = "\n".join(chunk_lines).strip()
                if chunk_text:
                    chunks.append({"file": filename, "content": chunk_text})
                    
        return chunks

    def build_index(self):
        """
        Parses python files, chunks them, and builds a TF-IDF index for semantic search.
        """
        self.chunks = []
        files = self.get_indexed_files()
        
        for filename in files:
            filepath = os.path.join(self.scripts_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_chunks = self.chunk_file(filename, content)
                self.chunks.extend(file_chunks)
            except Exception as e:
                print(f"Error reading file {filename} for indexing: {e}")
        
        if not self.chunks:
            # Empty fallback chunk
            self.chunks.append({"file": "empty.py", "content": "# No trading templates loaded."})
            
        # Build TF-IDF representation
        texts = [c["content"] for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w+\b')
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        # Save cache
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_file, "wb") as f:
                pickle.dump({
                    "chunks": self.chunks,
                    "vectorizer": self.vectorizer,
                    "tfidf_matrix": self.tfidf_matrix
                }, f)
            print("Successfully built and cached the RAG database index.")
        except Exception as e:
            print(f"Error writing vector index cache: {e}")

    def load_index(self):
        """
        Loads cached vector index, or builds a new one if missing.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    data = pickle.load(f)
                self.chunks = data["chunks"]
                self.vectorizer = data["vectorizer"]
                self.tfidf_matrix = data["tfidf_matrix"]
                print(f"Successfully loaded vector index with {len(self.chunks)} chunks.")
                return
            except Exception as e:
                print(f"Error loading cached RAG index: {e}. Rebuilding...")
        
        self.build_index()

    def search(self, query, top_k=2):
        """
        Performs similarity search against the chunk index and returns the top_k hits.
        Returns a list of tuples: (score, chunk_dict)
        """
        if self.vectorizer is None or self.tfidf_matrix is None or not self.chunks:
            return []
            
        try:
            query_vec = self.vectorizer.transform([query])
            # Calculate Cosine Similarities (dense dot product on sparse representation)
            similarities = (self.tfidf_matrix * query_vec.T).toarray().flatten()
            
            # Get indices sorted by similarity score descending
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                results.append((score, self.chunks[idx]))
            return results
        except Exception as e:
            print(f"Search execution failed: {e}")
            return []

    def augment_prompt(self, query, top_k=2, prediction_context=None):
        """
        Searches the DB for context and generates the RAG augmented prompt.
        Returns a tuple: (augmented_prompt, list_of_sources)
        """
        results = self.search(query, top_k=top_k)
        
        # Build context string
        context_blocks = []
        sources = []
        
        for score, chunk in results:
            if score > 0.05:  # Relevance threshold
                filename = chunk["file"]
                content = chunk["content"]
                sources.append({"file": filename, "score": score, "code": content})
                context_blocks.append(f"--- START TEMPLATE FROM FILE: {filename} (Similarity Score: {score:.2f}) ---\n{content}\n--- END TEMPLATE ---")
        
        context_str = "\n\n".join(context_blocks) if context_blocks else "# No matching templates found in database."
        
        prediction_str = ""
        if prediction_context:
            prediction_str = f"\n\n--- REAL-TIME FINANCIAL PREDICTOR DATA ---\n{prediction_context.strip()}\n--- END FINANCIAL PREDICTOR DATA ---\n"
            
        augmented_prompt = f"""Use the following relevant open-source trading code templates and real-time market forecast context to draft the requested quantitative script:

--- CODE TEMPLATES ---
{context_str}
--- END CODE TEMPLATES ---
{prediction_str}
Instruction:
Based on the code templates and real-time forecast data, write the trading script requested by the user:
"{query}"
"""
        return augmented_prompt, sources
