import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import Ridge

# Try importing statsmodels ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

def fetch_ten_years_data(ticker: str) -> pd.DataFrame:
    """
    Downloads historical stock/crypto daily data for the last 10 years.
    Falls back to mock data if offline/unreachable.
    """
    try:
        # 10 years timeframe calculations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10 * 365)
        
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            raise ValueError(f"No yfinance data returned for ticker '{ticker}'")
            
        # Clean timezone offset to prevent naive/aware comparison issues
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.attrs['is_mock'] = False
        return df
    except Exception as e:
        print(f"yfinance failed to fetch 10-year data for '{ticker}': {str(e)}. Falling back to generated mock data.")
        try:
            from src.predictor.data_loader import generate_mock_stock_data
            df = generate_mock_stock_data(ticker, days=10 * 365)
            return df
        except Exception:
            # Full inline fallback in case of import issues
            end_dt = pd.Timestamp.now().normalize()
            start_dt = end_dt - pd.Timedelta(days=10 * 365)
            date_range = pd.date_range(start=start_dt, end=end_dt, freq="B")
            np.random.seed(42 + len(ticker))
            start_price = 150.0 if ticker == "AMD" else 100.0
            returns = np.random.normal(loc=0.0006, scale=0.018, size=len(date_range))
            price_path = start_price * np.exp(np.cumsum(returns))
            df = pd.DataFrame(index=date_range)
            df['Close'] = price_path
            df['Open'] = df['Close'] * (1 + np.random.normal(0, 0.006, len(df)))
            df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.009, len(df))))
            df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.009, len(df))))
            df['Volume'] = np.random.randint(1000000, 10000000, size=len(df))
            df.attrs['is_mock'] = True
            return df

def train_arima_forecast(df: pd.DataFrame, forecast_days: int = 30) -> pd.DataFrame:
    """
    Train ARIMA time-series model on Closing price. 
    Falls back to a lag-based Ridge Regression model if statsmodels is missing or fails to fit.
    """
    if len(df) < 50:
        raise ValueError("Insufficient data points. Minimum 50 records required for time-series forecasting.")

    series = df['Close'].dropna()
    last_date = series.index[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    
    forecast_df = pd.DataFrame(index=future_dates)
    
    # 1. Try fitting ARIMA model
    if HAS_STATSMODELS:
        try:
            # ARIMA(1, 1, 1) is a fast, robust baseline for daily financial close series
            model = ARIMA(series.values, order=(1, 1, 1))
            fit_model = model.fit()
            
            # Predict
            forecast_res = fit_model.get_forecast(steps=forecast_days)
            forecast_mean = forecast_res.predicted_mean
            conf_int = forecast_res.conf_int(alpha=0.05) # 95% confidence interval
            
            forecast_df['Predicted_Close'] = forecast_mean
            forecast_df['Conf_Lower'] = conf_int[:, 0]
            forecast_df['Conf_Upper'] = conf_int[:, 1]
            forecast_df['Forecast_Engine'] = "ARIMA(1,1,1)"
            
            return forecast_df
        except Exception as e:
            # If ARIMA fails to converge, fall through to fallback regressor
            pass

    # 2. Fallback / Alternative: Lag-based Ridge Regression
    # Create lag features (past 5 days closes)
    lags = 5
    lagged_df = pd.DataFrame(index=series.index)
    lagged_df['y'] = series
    for i in range(1, lags + 1):
        lagged_df[f'lag_{i}'] = series.shift(i)
        
    lagged_df = lagged_df.dropna()
    
    X = lagged_df[[f'lag_{i}' for i in range(1, lags + 1)]].values
    y = lagged_df['y'].values
    
    # Train Ridge Regressor
    reg = Ridge(alpha=1.0)
    reg.fit(X, y)
    
    # Predict iteratively (auto-regressive step prediction)
    predictions = []
    last_window = list(series.values[-lags:])
    
    for _ in range(forecast_days):
        features = np.array(last_window[-lags:]).reshape(1, -1)
        pred = reg.predict(features)[0]
        predictions.append(pred)
        last_window.append(pred)
        
    forecast_df['Predicted_Close'] = predictions
    
    # Generate simple confidence band based on variance of residuals
    residuals = y - reg.predict(X)
    std_error = np.std(residuals)
    
    # Project widening confidence bands
    multiplier = np.sqrt(np.arange(1, forecast_days + 1))
    forecast_df['Conf_Lower'] = predictions - (1.96 * std_error * multiplier)
    forecast_df['Conf_Upper'] = predictions + (1.96 * std_error * multiplier)
    forecast_df['Forecast_Engine'] = "Ridge Regression (Lag-based)"
    
    return forecast_df

if __name__ == "__main__":
    # Quick standalone test verification
    print("Running standalone test for finance_module...")
    try:
        print("Fetching AMD stock data (last 10 years)...")
        data = fetch_ten_years_data("AMD")
        print(f"Data Loaded: {len(data)} rows.")
        
        print("Fitting forecasting model...")
        predictions = train_arima_forecast(data, forecast_days=30)
        print("\n30-Day Forecast Predictions:")
        print(predictions.head(10))
        print("SUCCESS: forecasting run completed.")
    except Exception as e:
        print(f"FAILED: Standalone test failed with error: {str(e)}")
