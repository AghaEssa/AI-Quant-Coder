import os
import requests
import json
from .prompts import SYSTEM_PROMPT

class LLMClient:
    def __init__(self, api_url: str = None, api_key: str = None, model: str = None):
        # Allow reading from environment or explicit arguments
        self.api_url = api_url or os.environ.get("LLM_API_URL", "http://localhost:11434/v1") # Default local Ollama OpenAI-compat
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "no-key-required")
        self.model = model or os.environ.get("LLM_MODEL", "llama3")

    def generate_response(self, prompt: str, chat_history: list = None) -> str:
        """
        Sends request to the OpenAI-compatible LLM endpoint (Ollama, vLLM on AMD Cloud, etc.).
        If the server is unreachable, falls back to a smart mock response with instructions.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Prepare messages in chat format
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        try:
            url = f"{self.api_url.rstrip('/')}/chat/completions"
            print(f"DEBUG LLMClient: Sending POST to {url} with model={self.model}")
            # Increase timeout (e.g. 60s) to allow Ollama to load model weights into RAM/VRAM on first run
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            print(f"DEBUG LLMClient: Status code = {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            return f"### ⚠️ Connection Error\nFailed to connect to Ollama/LLM server:\n- **Error Type:** `{type(e).__name__}`\n- **Error Details:** `{str(e)}`\n\n**Please check:**\n1. Is Ollama running in the background (check system tray)?\n2. Run `ollama run {self.model}` in a terminal to confirm it is downloaded.\n3. Verify the API URL `{self.api_url}` matches your server."

    def generate_stream(self, prompt: str, chat_history: list = None):
        """
        Yields chunks of generated text in real-time from the local/cloud LLM server.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Prepare messages in chat format
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            # Filter out any error messages from system history to avoid pollution
            filtered_history = [m for m in chat_history if "⚠️ Connection Error" not in m.get("content", "")]
            messages.extend(filtered_history)
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
            "stream": True
        }
        
        url = f"{self.api_url.rstrip('/')}/chat/completions"
        
        try:
            # Timeout is for establishing connection, not full response download
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                json_data = json.loads(data_str)
                                content = json_data['choices'][0]['delta'].get('content', '')
                                if content:
                                    yield content
                            except Exception:
                                pass
            else:
                yield f"Error from LLM Server (Status {response.status_code}): {response.text}"
        except Exception as e:
            yield f"### ⚠️ Connection Error\nFailed to connect to Ollama/LLM server:\n- **Error Type:** `{type(e).__name__}`\n- **Error Details:** `{str(e)}`"

    def _mock_fallback_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        # Build interactive guides depending on user request
        if "strategy" in prompt_lower or "rsi" in prompt_lower or "macd" in prompt_lower:
            return """### 🤖 Local Mock Mode (LLM Server Offline)
It looks like your local LLM engine (Ollama or AMD Developer Cloud endpoint) is not connected. Here is a baseline **RSI Trading Strategy** code for your testing:

```python
import yfinance as yf
import pandas as pd

def rsi_trading_strategy(ticker, rsi_period=14, buy_threshold=30, sell_threshold=70):
    # Fetch stock history
    df = yf.Ticker(ticker).history(period="1y")
    
    # Calculate RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Signals
    df['Signal'] = 0 # 0 = Hold, 1 = Buy, -1 = Sell
    df.loc[df['RSI'] < buy_threshold, 'Signal'] = 1
    df.loc[df['RSI'] > sell_threshold, 'Signal'] = -1
    
    return df[['Close', 'RSI', 'Signal']]

# Example execution
data = rsi_trading_strategy("AMD")
print(data.tail(10))
```

> **How to Connect your AI Backend:**
> 1. **Ollama (Local laptop):** Run `ollama run llama3` or `ollama run mistral` and point standard URL to `http://localhost:11434/v1`.
> 2. **AMD Developer Cloud (Production):** Once you host your model container on AMD GPUs, update the configuration URL in the sidebar.
"""
        elif "backtest" in prompt_lower:
            return """### 🤖 Local Mock Mode (LLM Server Offline)
Here is a baseline backtester code structure using vectorization:

```python
import numpy as np

def run_vectorized_backtest(df):
    # Assumes signal: 1 (Buy), -1 (Sell), 0 (Hold)
    df['Daily_Return'] = df['Close'].pct_change()
    df['Position'] = df['Signal'].shift(1).fillna(0)
    df['Strategy_Return'] = df['Position'] * df['Daily_Return']
    
    cumulative_market = (1 + df['Daily_Return']).cumprod() - 1
    cumulative_strategy = (1 + df['Strategy_Return']).cumprod() - 1
    
    print(f"Total Market Return: {cumulative_market.iloc[-1]:.2%}")
    print(f"Total Strategy Return: {cumulative_strategy.iloc[-1]:.2%}")
```
"""
        else:
            return f"""### 🤖 Local Mock Mode (LLM Server Offline)
Received query: "{prompt}"

Currently, the Streamlit UI is running in local mockup mode because it couldn't connect to an LLM endpoint.

**To enable live LLM generation:**
1. Start Ollama locally on port `11434` or boot your AMD Developer Cloud instance.
2. In the Sidebar, enter your API URL (e.g., `http://localhost:11434/v1` or AMD instance host) and click **Update Settings**.
"""
