# ⚡ AI Quant-Coder

> **AMD Developer Hackathon: ACT II Submission**

An end-to-end **Financial Market Predictor** and **Retrieval-Augmented Generation (RAG) Coding Assistant** powered by open-source LLMs on AMD Developer Cloud GPUs.

AI Quant-Coder bridges the gap between financial time-series forecasts and algorithmic trading script generation — combining a statistical prediction engine with a full in-browser coding assistant that generates, explains, and structures quantitative trading bots in real-time.

---

## 🖥️ Live Application Pages

| Page | Description |
|---|---|
| 📈 **Market Predictor** | Live stock charts with technical indicators (SMA, EMA, RSI) and 30-day ARIMA price forecasts. Includes an embedded code assistant chat. |
| 💬 **AI Code Assistant** | Full-screen Gemini-style coding assistant with multi-session chat history, hamburger sidebar toggle, and RAG DB manager. |
| ⚙️ **System Configuration** | Configure local Ollama or AMD Developer Cloud vLLM API endpoints and model identifiers. Run live connection diagnostics. |
| ℹ️ **About Project** | Detailed project architecture cards, module deep dives, and core hackathon innovation feature highlights. |

---

## 🚀 Key Features

### 📈 Market Predictor Engine
- Fetches up to **10 years of historical stock data** from Yahoo Finance API
- Computes rolling technical indicators:
  - **SMA 20 / SMA 50** — Moving Average Crossover detection
  - **EMA 20 / EMA 50** — Exponential Moving Averages
  - **RSI (14-day)** — Relative Strength Index (Overbought/Oversold)
- **ARIMA(1,1,0) Forecasting** — Statistical 30-day close price projection
- **Interactive Plotly Charts** — Dark-mode, zoom-enabled candlestick/line layouts
- **Swappable Panel Layouts** — Swap graph and chat positions inline on the page

### 💬 RAG Coding Assistant
- **TF-IDF Vector Database** — Indexes local open-source trading script templates
- **Semantic Code Retrieval** — Finds relevant Python code templates using cosine similarity matching
- **Predictor Context Injection** — Automatically appends live RSI, SMA trend, current close, and 30-day ARIMA forecast into every LLM request
- **Multi-Session Chat History** — Persistent JSON-backed session store with named conversations
- **Thread-Isolated Background Streaming** — LLM generation runs on background worker threads; UI never freezes
- **Active Session Indicator** — Active chat highlighted with bright green gradient and `🟢` marker

### 🔌 AMD ROCm / vLLM Ready
- Configurable API endpoint routing for:
  - **Local Ollama** — `http://localhost:11434/v1`
  - **AMD Developer Cloud vLLM** — Any remote OpenAI-compatible endpoint
- Live connection diagnostic panel to verify endpoint/model health

---
 
 
---

## ⚙️ Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/Hack-tn.git
cd Hack-tn
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Create environment
python -m venv venv

# Activate — Windows
.\venv\Scripts\activate

# Activate — Linux / macOS
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### 3. Set Up LLM Backend

#### Option A: Local Ollama (Recommended for quick testing)
```bash
# Install Ollama from https://ollama.com
ollama pull llama3.2

# Ollama auto-serves at: http://localhost:11434/v1
```

#### Option B: AMD Developer Cloud (vLLM + ROCm)
```bash
# On your AMD GPU Ubuntu server:
source venv/bin/activate
pip install vllm  # ROCm-compatible build

# Serve model with vLLM
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --port 8000

# Update the endpoint in the app: http://<server-ip>:8000/v1
```

### 4. Run the Application
```bash
streamlit run app.py
```
Opens at **http://localhost:8501** in your browser.

---

## 🧠 How the RAG Pipeline Works

```
User Prompt
    │
    ▼
TF-IDF Search (rag_module.py)
    │  Finds top-k matching code template chunks
    ▼
Predictor Context Compiler
    │  Appends live stock stats: RSI, SMA trend, close price, ARIMA forecast
    ▼
Augmented Prompt Builder
    │  Merges code templates + financial data into structured LLM instruction
    ▼
LLM Streaming Client (llm_client.py)
    │  Sends augmented prompt via background thread
    ▼
Script Output (Streamed to chat in real-time)
```

---

  
## 📄 License

This project is submitted as an open-source hackathon entry. Free to use and extend for educational and research purposes.

---

## 👥 Authors

| Name | Role |
|---|---|
| **Agha Essa Khan** | Team Leader & AI Architect |
| **Misbah Ramzan** | Quantitative & Python Developer |

*Submitted for the **AMD Developer Hackathon: ACT II***

