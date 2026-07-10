import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

def predict_future_prices(df: pd.DataFrame, forecast_days: int = 15) -> pd.DataFrame:
    """
    Train a simple Linear Regression model on historical Close prices
    to predict price direction for the next N days.
    """
    if len(df) < forecast_days:
        raise ValueError("Insufficient data points to perform reliable forecasting.")
        
    df_clean = df.dropna(subset=['Close'])
    
    # Feature matrix: Indices as time-steps
    X = np.arange(len(df_clean)).reshape(-1, 1)
    y = df_clean['Close'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Project into the future
    future_X = np.arange(len(df_clean), len(df_clean) + forecast_days).reshape(-1, 1)
    future_preds = model.predict(future_X)
    
    # Generate future dates
    last_date = df_clean.index[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    
    # Create prediction dataframe
    pred_df = pd.DataFrame(index=future_dates)
    pred_df['Predicted_Close'] = future_preds
    
    # Simple confidence bands
    residuals = y - model.predict(X)
    std_error = np.std(residuals)
    pred_df['Conf_Lower'] = future_preds - (1.96 * std_error)
    pred_df['Conf_Upper'] = future_preds + (1.96 * std_error)
    
    return pred_df
