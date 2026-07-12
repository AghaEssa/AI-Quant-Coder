🚀 Excited to share what we built for the **AMD Developer Hackathon: Act II**! 

I’m thrilled to introduce **AI Quant-Coder** 📈 – an end-to-end quantitative trading framework that integrates statistical price forecasting with a custom-engineered Retrieval-Augmented Generation (RAG) assistant to automatically generate and backtest customized trading scripts in real-time.

### 🔍 The Problem
Quantitative strategy formulation and backtesting usually require hours of manual script writing, parameter tuning, and data integration. We wanted to build a bridge that takes live stock data, predicts future trajectories, and immediately outputs production-ready backtesting code.

### 💡 What is AI Quant-Coder?
It is a dual-panel Streamlit dashboard built on a comprehensive financial-data pipeline:

1. **📊 Time-Series Market Predictor:** 
   - Dynamically pulls live stock records (e.g., AMD, NVIDIA, etc.) via `yfinance`.
   - Computes live rolling indicators: Relative Strength Index (RSI 14D) and Moving Average Crossovers (SMA 20/50).
   - Fits a statistical **ARIMA(1,1,1)** forecasting model to predict future 30-day asset closing trends.

2. **🤖 Code Assistant & RAG Pipeline:**
   - Feeds live forecast targets and moving averages crossover context directly into the system prompt.
   - Leverages a custom **TF-IDF Vector Search Index** (TradingRAG) to search and retrieve matching functional code templates.
   - Queries Ollama / vLLM / Groq API endpoints in real-time using isolated background threads (keeping the UI extremely fluid).
   - Generates fully-functional, vectorized Python backtest scripts.

3. **📥 Corporate-Ready Reports:**
   - Features a single-click download to export the entire conversation, live forecast parameters, and clean Consolas-formatted code blocks directly into a beautifully-styled **Microsoft Word (.docx)** report or Raw Markdown (.md) file!

### ⚡ Accelerated by AMD ROCm
To handle high-throughput LLM streaming and rapid vector database query resolution, the application is optimized for deployment on the **AMD Developer Cloud**, utilizing **AMD ROCm GPU hardware** for lightning-fast model inference.

### 👥 Team Credits
This project wouldn't have been possible without my incredibly talented teammate:
* **Misbah Ramzan** (Data Scientist & Quant Developer) – who engineered the time-series ARIMA prediction engine, technical indicators calculations, and strategy backtesting logic.
* **Agha Essa Khan** (Team Lead & Full-Stack Developer) – built the full-stack architecture, RAG vector index, thread synchronization, and export layout styling.

---
👉 **Try the Live App:** [ai-quant-coder.streamlit.app](https://ai-quant-coder-vuvupj7d8sxuhchg6anzdb.streamlit.app/)  
🐙 **Explore the Code:** [GitHub Repository](https://github.com/AghaEssa/AI-Quant-Coder)

We would love to hear your thoughts, feedback, or suggestions in the comments!

#AMDDeveloperHackathon #ROCm #QuantitativeTrading #FinTech #DataScience #MachineLearning #ARIMA #Streamlit #AI #LLM #RAG #OpenSource
