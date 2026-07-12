import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

from src.utils.helpers import inject_custom_css
from src.predictor.data_loader import fetch_stock_data, add_technical_indicators
from src.predictor.models import predict_future_prices
from src.predictor.finance_module import fetch_ten_years_data, train_arima_forecast
from src.assistant.llm_client import LLMClient
import threading
import time

def background_stream_worker(api_url, api_key, model, prompt, history, chat_list_ref, prediction_context=None, is_mock=False):
    """
    Background worker thread to stream model outputs and update the session state in-place.
    Integrates with TradingRAG to retrieve relevant code template context.
    """
    from src.assistant.rag_module import TradingRAG
    rag = TradingRAG()
    augmented_prompt, sources = rag.augment_prompt(prompt, top_k=2, prediction_context=prediction_context)
    
    if chat_list_ref and len(chat_list_ref) > 0:
        chat_list_ref[-1]["sources"] = sources

    if is_mock:
        # Generate mock response using RAG sources
        mock_response = "### 🤖 AI Quant-Coder (Offline Mock Mode)\n\n"
        if sources:
            mock_response += "Since the AI model is currently offline, I am displaying the direct code templates retrieved by our **TradingRAG** engine matching your prompt:\n\n"
            for s in sources:
                mock_response += f"📄 **Source Template: `{s['file']}`**\n"
                mock_response += f"```python\n{s['code']}\n```\n\n"
        else:
            mock_response += "I couldn't find any direct match for your request in our database. Here is a basic Python script structure to help you get started:\n\n"
            mock_response += "```python\n# Basic Trading Strategy Script Template\nimport pandas as pd\nimport numpy as np\n\ndef calculate_signals(data):\n    # Simple crossover logic placeholder\n    data['Signal'] = np.where(data['Close'] > data['Close'].shift(1), 1, -1)\n    return data\n```\n\n"
        mock_response += "\n\n💡 *Tip: To enable live AI code generation and modifications, please go to the **System Configuration** tab in the navigation menu and enter your API base URL, Model ID, and API Token.*"
        
        # Stream it chunk-by-chunk to simulate real-time typing
        chunk_size = 20  # characters per step
        full_response = ""
        for i in range(0, len(mock_response), chunk_size):
            full_response += mock_response[i:i+chunk_size]
            if chat_list_ref and len(chat_list_ref) > 0:
                chat_list_ref[-1]["content"] = full_response
            time.sleep(0.02)
        if chat_list_ref and len(chat_list_ref) > 0:
            chat_list_ref[-1]["status"] = "complete"
        return

    llm = LLMClient(api_url=api_url, api_key=api_key, model=model)
    try:
        stream = llm.generate_stream(augmented_prompt, chat_history=history)
        full_response = ""
        for chunk in stream:
            full_response += chunk
            if chat_list_ref and len(chat_list_ref) > 0:
                chat_list_ref[-1]["content"] = full_response
        if chat_list_ref and len(chat_list_ref) > 0:
            chat_list_ref[-1]["status"] = "complete"
    except Exception as e:
        if chat_list_ref and len(chat_list_ref) > 0:
            chat_list_ref[-1]["content"] = f"### ⚠️ Connection Error\nFailed to connect to Ollama/LLM server:\n- **Error Type:** `{type(e).__name__}`\n- **Error Details:** `{str(e)}`"
            chat_list_ref[-1]["status"] = "error"

# 1. Page Configuration
st.set_page_config(
    page_title="AI Quant-Coder | AMD Dev Hackathon",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject dark theme custom CSS styles
inject_custom_css()

# Helper functions for persistent chat history
def load_persistent_chats():
    import json
    import os
    if os.path.exists("data/chat_history.json"):
        try:
            with open("data/chat_history.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading persistent chats: {e}")
    return {"Default Session": []}

def save_persistent_chats():
    if "chats" in st.session_state:
        try:
            import json
            import os
            os.makedirs("data", exist_ok=True)
            with open("data/chat_history.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.chats, f, indent=4)
        except Exception as e:
            print(f"Error saving persistent chats: {e}")

# Initialize Session State values directly in app.py
from src.assistant.rag_module import TradingRAG
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = TradingRAG()

if "chats" not in st.session_state:
    st.session_state.chats = load_persistent_chats()
    
    # On fresh session load, default to an existing empty chat session,
    # or create a new one so the user starts with a clean empty chat.
    empty_chat_key = None
    for k, v in st.session_state.chats.items():
        if not v:
            empty_chat_key = k
            break
            
    if empty_chat_key:
        st.session_state.active_chat_id = empty_chat_key
    else:
        num_chats = len(st.session_state.chats)
        new_title = f"New Chat {num_chats + 1}"
        while new_title in st.session_state.chats:
            num_chats += 1
            new_title = f"New Chat {num_chats + 1}"
        st.session_state.chats[new_title] = []
        st.session_state.active_chat_id = new_title

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = list(st.session_state.chats.keys())[0] if st.session_state.chats else "Default Session"

# Sync chat_history reference
st.session_state.chat_history = st.session_state.chats.setdefault(st.session_state.active_chat_id, [])

if "active_threads" not in st.session_state:
    st.session_state.active_threads = {}

if "llm_url" not in st.session_state:
    st.session_state.llm_url = "http://127.0.0.1:11434/v1"
if "llm_key" not in st.session_state:
    st.session_state.llm_key = "no-key-required"
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "llama3.2"

# 2. Sidebar Configuration (Clean header and target selectors)
st.sidebar.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h1 class='gradient-text' style='font-size: 28px; margin: 0; padding: 0;'>⚡ Quant-Coder</h1>
        <p style='font-size: 12px; color: #94a3b8; margin: 5px 0 0 0;'>AMD Developer Hackathon: ACT II</p>
    </div>
    """, 
    unsafe_allow_html=True
)
st.sidebar.markdown("---")

# Navigation Selector in the Sidebar
st.sidebar.markdown("<p style='font-size:11px; font-weight:700; color:#475569; letter-spacing:0.1em; margin-bottom: 8px;'>NAVIGATION</p>", unsafe_allow_html=True)
nav_choice = st.sidebar.radio(
    "Navigation Options",
    options=[
        "📈 Market Predictor",
        "💬 AI Code Assistant",
        "⚙️ System Configuration",
        "ℹ️ About Project"
    ],
    label_visibility="collapsed"
)
st.sidebar.markdown("---")

# Stock Target Options (Visible throughout the app for quick context changes)
st.sidebar.markdown("### 📊 Market Target")
ticker_symbol = st.sidebar.text_input(
    "Stock Ticker Symbol", 
    value="AMD",
    help="Enter a stock ticker (e.g. AMD, NVDA, AAPL, MSFT) or crypto asset."
).upper()

today = datetime.now()
default_start = today - timedelta(days=365)
col_start, col_end = st.sidebar.columns(2)
with col_start:
    start_date = st.sidebar.date_input("Start Date", default_start)
with col_end:
    end_date = st.sidebar.date_input("End Date", today)

# Layout Split Mode Selection defaults
layout_focus = st.session_state.get("dash_layout_focus", "Balanced")
panel_order = st.session_state.get("dash_panel_order", "Graph Left | Chat Right")

st.sidebar.markdown("---")

# LLM Backend Connection Status
connected = False
try:
    # 1. Try standard OpenAI-compatible /models endpoint
    headers = {}
    if st.session_state.llm_key and st.session_state.llm_key != "no-key-required":
        headers["Authorization"] = f"Bearer {st.session_state.llm_key}"
    res = requests.get(f"{st.session_state.llm_url.rstrip('/')}/models", headers=headers, timeout=1.5)
    if res.status_code == 200:
        connected = True
except:
    pass

if not connected:
    try:
        # 2. Try native Ollama root if port 11434 is in URL
        if "11434" in st.session_state.llm_url:
            # Extract protocol, host, and port
            base_url = "http://127.0.0.1:11434"
            res = requests.get(base_url, timeout=1.5)
            if res.status_code == 200:
                connected = True
    except:
        pass

st.session_state.connected = connected
if connected:
    st.sidebar.success(f"🟢 Connected: {st.session_state.llm_model}")
else:
    st.sidebar.warning("🟡 LLM Offline (Mock Mode)")

st.sidebar.markdown(
    """
    <div style='background: rgba(30, 41, 59, 0.4); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-top: 25px;'>
        <p style='margin:0; font-size:11px; color:#94a3b8;'>ROCm Acceleration on AMD Developer Cloud GPU hardware.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# 3. Main Dashboard: Sidebar-based navigation routing
# Pages are routed using the `nav_choice` variable.

# Process Stock Data & ARIMA Forecast first (shared across render code if needed)
@st.cache_data(ttl=3600)
def get_processed_data(ticker, start, end):
    raw_df = fetch_stock_data(ticker, period="2y")
    if raw_df.index.tz is not None:
        raw_df.index = raw_df.index.tz_localize(None)
    filtered_df = raw_df.loc[pd.to_datetime(start):pd.to_datetime(end)]
    if filtered_df.empty:
        return raw_df
    return add_technical_indicators(filtered_df)

try:
    df = get_processed_data(ticker_symbol, start_date, end_date)
    last_row = df.iloc[-1]
    prev_close = df.iloc[-2]['Close']
    pct_change = ((last_row['Close'] - prev_close) / prev_close) * 100
except Exception as e:
    st.error(f"Could not load data for '{ticker_symbol}': {str(e)}")
    st.info("Loading default 'AMD' stock ticker data as fallback.")
    df = get_processed_data("AMD", default_start, today)
    last_row = df.iloc[-1]
    prev_close = df.iloc[-2]['Close']
    pct_change = ((last_row['Close'] - prev_close) / prev_close) * 100
    ticker_symbol = "AMD"

# Run Time-Series Forecasting
forecast_days = 30
try:
    ten_year_df = fetch_ten_years_data(ticker_symbol)
    pred_df = train_arima_forecast(ten_year_df, forecast_days=forecast_days)
except Exception as e:
    # Fallback to simple regression on filtered data
    pred_df = predict_future_prices(df, forecast_days=forecast_days)
    pred_df['Forecast_Engine'] = "Linear Regression (Fallback)"

engine_name = pred_df['Forecast_Engine'].iloc[0] if 'Forecast_Engine' in pred_df.columns else "ARIMA"


# ==========================================
# RENDER PAGE: 📈 Market Predictor (Split Screen)
# ==========================================
if nav_choice == "📈 Market Predictor":
    st.markdown("<h2 style='margin-bottom: 2px;'>⚡ AI Quant-Coder Dashboard</h2>", unsafe_allow_html=True)
    st.write("Real-time technical analysis coupled with AI trading assistant.")
    
    if df.attrs.get('is_mock', False):
        st.warning(f"⚠️ Yahoo Finance API is unreachable or rate-limited. Displaying simulated realistic mock stock data for '{ticker_symbol}'.")
    
    # Dashboard Layout Customizer (directly on page for premium UX)
    with st.expander("🖥️ Customize Dashboard Layout & Panels", expanded=False):
        lay_col1, lay_col2 = st.columns([3, 2])
        with lay_col1:
            layout_focus = st.select_slider(
                "Panel Width Focus",
                options=["Graph Only", "Graph Focus", "Balanced", "Chat Focus", "Chat Only"],
                value=layout_focus,
                key="dash_layout_focus",
                help="Adjust space dynamically between charts and AI chat."
            )
        with lay_col2:
            panel_order = st.radio(
                "Panel Arrangement",
                options=["Graph Left | Chat Right", "Chat Left | Graph Right"],
                index=0 if panel_order == "Graph Left | Chat Right" else 1,
                horizontal=True,
                key="dash_panel_order",
                help="Swap position of the graph and the chat panel."
            )

    # Setup panels based on layout focus and order swap
    graph_ratio = 1.4
    chat_ratio = 1.4
    if layout_focus == "Graph Focus":
        graph_ratio, chat_ratio = 2.0, 0.8
    elif layout_focus == "Balanced":
        graph_ratio, chat_ratio = 1.4, 1.4
    elif layout_focus == "Chat Focus":
        graph_ratio, chat_ratio = 0.8, 2.0

    if layout_focus == "Graph Only":
        left_panel = st.container()
        right_panel = None
    elif layout_focus == "Chat Only":
        left_panel = None
        right_panel = st.container()
    else:
        # Split layout with swap logic
        if panel_order == "Graph Left | Chat Right":
            left_col, right_col = st.columns([graph_ratio, chat_ratio])
            left_panel = left_col
            right_panel = right_col
        else:
            left_col, right_col = st.columns([chat_ratio, graph_ratio])
            left_panel = right_col  # graph goes to right column
            right_panel = left_col  # chat goes to left column
        
    if left_panel is not None:
        with left_panel:
            # Top KPIs / Metrics Panel inside Left panel
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            with kpi_col1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:12px; color:#94a3b8;">Price ({ticker_symbol})</p>
                        <h3 style="margin:2px 0; font-size:22px; font-weight:600;">${last_row['Close']:.2f}</h3>
                        <span style="color:{'#10b981' if pct_change >= 0 else '#ef4444'}; font-size:12px; font-weight:600;">
                            {'▲' if pct_change >= 0 else '▼'} {pct_change:.2f}%
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with kpi_col2:
                rsi_val = last_row['RSI_14']
                rsi_status = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:12px; color:#94a3b8;">RSI (14D)</p>
                        <h3 style="margin:2px 0; font-size:22px; font-weight:600;">{rsi_val:.1f}</h3>
                        <span style="color:#818cf8; font-size:12px; font-weight:600;">{rsi_status}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with kpi_col3:
                sma_diff = last_row['SMA_20'] - last_row['SMA_50']
                sma_trend = "Bullish Crossover" if sma_diff > 0 else "Bearish Crossover"
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:12px; color:#94a3b8;">SMA State</p>
                        <h3 style="margin:2px 0; font-size:22px; font-weight:600;">{sma_trend.split()[0]}</h3>
                        <span style="color:{'#10b981' if sma_diff >= 0 else '#ef4444'}; font-size:12px; font-weight:600;">{sma_trend.split()[1]}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with kpi_col4:
                final_pred = pred_df.iloc[-1]['Predicted_Close']
                direction = "UP" if final_pred > last_row['Close'] else "DOWN"
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:12px; color:#94a3b8;">30D Target</p>
                        <h3 style="margin:2px 0; font-size:22px; font-weight:600;">${final_pred:.1f}</h3>
                        <span style="color:#a5b4fc; font-size:11px; font-weight:600;">{direction} ({engine_name})</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            st.write("")
            show_ma = st.checkbox("Overlay Moving Averages (20/50)", value=True, key="overlay_ma_dash")
            
            # Plotly chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Close'], name="Historical Close", line=dict(color="#6366f1", width=2.5)
            ))
            if show_ma:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['SMA_20'], name="SMA 20", line=dict(color="#f59e0b", width=1.5, dash="dash")
                ))
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['SMA_50'], name="SMA 50", line=dict(color="#ec4899", width=1.5, dash="dash")
                ))
            fig.add_trace(go.Scatter(
                x=pred_df.index, y=pred_df['Predicted_Close'], name=f"30D Forecast ({engine_name})", line=dict(color="#10b981", width=2.5, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=list(pred_df.index) + list(pred_df.index[::-1]),
                y=list(pred_df['Conf_Upper']) + list(pred_df['Conf_Lower'][::-1]),
                fill='toself', fillcolor='rgba(16, 185, 129, 0.08)', line=dict(color='rgba(255,255,255,0)'),
                hoverinfo="skip", showlegend=True, name="Confidence Band"
            ))
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)"),
                yaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)"), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # RSI sub-chart
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(
                x=df.index, y=df['RSI_14'], name="RSI", line=dict(color="#a5b4fc", width=1.5)
            ))
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="#ef4444")
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="#10b981")
            rsi_fig.update_layout(
                height=130, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", range=[10, 90])
            )
            st.plotly_chart(rsi_fig, use_container_width=True)

    if right_panel is not None:
        with right_panel:
            st.subheader("🤖 Open-Source Code Assistant")
            st.write("Generate and backtest trading code. (Syncs with dedicated chat page)")
            if not st.session_state.get("connected", False):
                st.info("💡 **Running in Offline Mock Mode.** The chatbot will stream matching RAG template files. To connect a live LLM (Ollama/vLLM/Groq), go to the **System Configuration** tab in the sidebar.")
            
            # Clear & preset options
            clear_dash, preset_dash = st.columns([1.5, 2.5])
            with clear_dash:
                if st.button("🗑️ Clear Chat", key="clear_chat_dash", use_container_width=True):
                    st.session_state.chats[st.session_state.active_chat_id] = []
                    st.session_state.chat_history = []
                    st.rerun()
            
            st.markdown("<p style='font-size:12px; color:#64748b; margin: 5px 0 0 0;'>Quick presets:</p>", unsafe_allow_html=True)
            qp_col1, qp_col2 = st.columns(2)
            qp_query = ""
            with qp_col1:
                if st.button("RSI Backtest Strategy", key="qp_rsi_dash", use_container_width=True):
                    qp_query = f"Write a complete vectorized backtest script in Python for a simple RSI crossover strategy on '{ticker_symbol}'."
            with qp_col2:
                if st.button("Calculate MACD Script", key="qp_macd_dash", use_container_width=True):
                    qp_query = f"Write Python code using pandas to calculate EMA 12/26 and signal lines for '{ticker_symbol}' and plot it."
                    
            chat_box_dash = st.container(height=380)
            with chat_box_dash:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                        if msg.get("role") == "assistant" and msg.get("sources"):
                            with st.expander("🔍 Retrieved Code Templates Used", expanded=False):
                                for s in msg["sources"]:
                                    st.markdown(f"📄 **{s['file']}** (Score: {s['score']:.2f})")
                                    st.code(s["code"], language="python")
                        
            user_input_dash = st.chat_input("Ask for trading code scripts...", key="chat_input_dash")
            if qp_query:
                user_input_dash = qp_query
                
            if user_input_dash:
                current_chat = st.session_state.chats[st.session_state.active_chat_id]
                is_new_session = len(current_chat) == 0
                
                # 1. Rename active chat session immediately if it is a default/new empty session
                if is_new_session and (st.session_state.active_chat_id.startswith("New Chat") or st.session_state.active_chat_id == "Default Session"):
                    raw_title = user_input_dash.strip()
                    clean_title = "".join([c for c in raw_title if c.isalnum() or c.isspace()])
                    words = clean_title.split()
                    short_title = " ".join(words[:4]) if words else "Chat Session"
                    if len(short_title) > 28:
                        short_title = short_title[:25] + "..."
                    if not short_title:
                        short_title = "Chat Session"
                    
                    unique_title = short_title
                    counter = 1
                    while unique_title in st.session_state.chats:
                        unique_title = f"{short_title} ({counter})"
                        counter += 1
                    
                    st.session_state.chats[unique_title] = st.session_state.chats.pop(st.session_state.active_chat_id)
                    st.session_state.active_chat_id = unique_title
                    # Re-sync st.session_state.chat_history reference to the new key
                    st.session_state.chat_history = st.session_state.chats[st.session_state.active_chat_id]
                
                # 2. Append user message and placeholder assistant message immediately
                st.session_state.chat_history.append({"role": "user", "content": user_input_dash})
                st.session_state.chat_history.append({"role": "assistant", "content": "Thinking...", "status": "running"})
                
                # 3. Spawn background thread to query LLM and stream chunks
                history_copy = list(st.session_state.chat_history[:-2]) # Exclude query & placeholder
                chat_list_ref = st.session_state.chat_history
                
                # Compile financial predictor context
                try:
                    pred_last_row = df.iloc[-1]
                    pred_prev_close = df.iloc[-2]['Close']
                    pred_pct_change = ((pred_last_row['Close'] - pred_prev_close) / pred_prev_close) * 100
                    pred_rsi_val = pred_last_row['RSI_14']
                    pred_rsi_status = "Oversold" if pred_rsi_val < 30 else "Overbought" if pred_rsi_val > 70 else "Neutral"
                    pred_sma_diff = pred_last_row['SMA_20'] - pred_last_row['SMA_50']
                    pred_sma_trend = "Bullish Crossover (SMA 20 > 50)" if pred_sma_diff > 0 else "Bearish Crossover (SMA 20 < 50)"
                    pred_final_pred = pred_df.iloc[-1]['Predicted_Close']
                    pred_direction = "UP" if pred_final_pred > pred_last_row['Close'] else "DOWN"
                    
                    prediction_context = f"""
- Stock Ticker Symbol: {ticker_symbol}
- Current Market Close Price: ${pred_last_row['Close']:.2f} ({pred_pct_change:+.2f}%)
- Relative Strength Index (RSI 14D): {pred_rsi_val:.1f} ({pred_rsi_status})
- Simple Moving Average (SMA) Trend: {pred_sma_trend}
- 30-Day Predicted Forecast Close: ${pred_final_pred:.2f} (predicted trend: {pred_direction})
- Forecasting Model: {engine_name}
"""
                except Exception:
                    prediction_context = "No prediction indicators loaded."
                
                t = threading.Thread(
                    target=background_stream_worker,
                    args=(
                        st.session_state.get("llm_url_input", st.session_state.llm_url),
                        st.session_state.get("llm_key_input", st.session_state.llm_key),
                        st.session_state.get("llm_model_input", st.session_state.llm_model),
                        user_input_dash,
                        history_copy,
                        chat_list_ref,
                        prediction_context,
                        not st.session_state.get("connected", False)
                    )
                )
                t.start()
                if "active_threads" not in st.session_state:
                    st.session_state.active_threads = {}
                st.session_state.active_threads[st.session_state.active_chat_id] = t
                st.rerun()


# ==========================================
# RENDER PAGE: 💬 Dedicated Chat (Gemini-Style)
# ==========================================
elif nav_choice == "💬 AI Code Assistant":
    if "show_chat_sidebar" not in st.session_state:
        st.session_state.show_chat_sidebar = True
        
    col_title, col_toggle = st.columns([12, 1])
    with col_title:
        st.markdown("<h2 style='margin-top: 0px; margin-bottom: 2px;'>💬 Dedicated Code Assistant</h2>", unsafe_allow_html=True)
    with col_toggle:
        btn_label = "☰" if st.session_state.show_chat_sidebar else "📂 ☰"
        if st.button(btn_label, key="toggle_chat_sidebar_btn", help="Toggle Chat Session & RAG DB Manager", use_container_width=True):
            st.session_state.show_chat_sidebar = not st.session_state.show_chat_sidebar
            st.rerun()
            
    st.write("A full-screen interface modeled after Gemini. Optimized for large coding scripts.")
    if not st.session_state.get("connected", False):
        st.info("💡 **Running in Offline Mock Mode.** The chatbot will stream matching RAG template files. To connect a live LLM (Ollama/vLLM/Groq), go to the **System Configuration** tab in the sidebar.")
    show_chat_sidebar = st.session_state.show_chat_sidebar
    
    if show_chat_sidebar:
        chat_sidebar_col, chat_main_col = st.columns([1, 3])
        with chat_sidebar_col:
            st.markdown(
                """
                <div style='background: rgba(30, 41, 59, 0.25); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 15px;'>
                    <p style='margin:0; font-size:14px; font-weight:600; color:#818cf8;'>💬 Chat Sessions</p>
                    <p style='margin:2px 0 0 0; font-size:11px; color:#64748b;'>Switch or manage your threads.</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            if st.button("➕ New Chat Session", use_container_width=True, key="new_chat_dedicated"):
                num_chats = len(st.session_state.chats)
                new_title = f"New Chat {num_chats + 1}"
                while new_title in st.session_state.chats:
                    num_chats += 1
                    new_title = f"New Chat {num_chats + 1}"
                st.session_state.chats[new_title] = []
                st.session_state.active_chat_id = new_title
                st.session_state.chat_history = st.session_state.chats[new_title]
                st.rerun()
                
            # Display list of chat sessions as clickable buttons
            st.markdown("<p style='font-size:12px; color:#94a3b8; margin: 10px 0 5px 0;'>Recent Chats:</p>", unsafe_allow_html=True)
            
            for chat_title in list(st.session_state.chats.keys()):
                is_active = (chat_title == st.session_state.active_chat_id)
                
                btn_col, del_col = st.columns([4, 1])
                with btn_col:
                    if is_active:
                        st.button(f"🟢 {chat_title}", key=f"select_{chat_title}", use_container_width=True, disabled=True)
                    else:
                        if st.button(f"💬 {chat_title}", key=f"select_{chat_title}", use_container_width=True):
                            st.session_state.active_chat_id = chat_title
                            st.session_state.chat_history = st.session_state.chats[chat_title]
                            st.rerun()
                with del_col:
                    if len(st.session_state.chats) > 1:
                        if st.button("🗑️", key=f"del_{chat_title}", use_container_width=True):
                            st.session_state.chats.pop(chat_title)
                            if is_active:
                                st.session_state.active_chat_id = list(st.session_state.chats.keys())[0]
                                st.session_state.chat_history = st.session_state.chats[st.session_state.active_chat_id]
                            st.rerun()
                            
            # RAG Templates Database Panel
            import os
            st.markdown("---")
            st.markdown(
                """
                <div style='background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); margin-top: 15px; margin-bottom: 15px;'>
                    <p style='margin:0; font-size:14px; font-weight:600; color:#10b981;'>📚 RAG Templates DB</p>
                    <p style='margin:2px 0 0 0; font-size:11px; color:#94a3b8;'>Open-source python templates matching user prompts.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            rag = st.session_state.rag_engine
            indexed_files = rag.get_indexed_files()
            st.markdown(f"**Index Status:** `🟢 Active ({len(indexed_files)} files)`")
            
            with st.expander("📄 View Indexed Files", expanded=False):
                if indexed_files:
                    for f_name in indexed_files:
                        st.write(f"- `{f_name}`")
                else:
                    st.write("No files indexed.")
                    
            # File uploader to drop new custom Python scripts
            uploaded_file = st.file_uploader(
                "Upload Custom Trading Bot (.py)", 
                type=["py"], 
                key="rag_script_uploader",
                help="Upload custom Python code. It will be chunked and indexed automatically into the vector database."
            )
            
            if uploaded_file is not None:
                filepath = os.path.join(rag.scripts_dir, uploaded_file.name)
                try:
                    file_content = uploaded_file.read().decode("utf-8")
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    rag.build_index()
                    st.success(f"Successfully uploaded and indexed `{uploaded_file.name}`!")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to process uploaded file: {e}")
                    
            if st.button("🔄 Rebuild Vector Index", key="rebuild_rag_index", use_container_width=True):
                with st.spinner("Re-indexing local repository..."):
                    rag.build_index()
                st.success("Vector index successfully rebuilt!")
                st.rerun()
    else:
        chat_main_col = st.container()
        
    with chat_main_col:
        pass
        # Full width chatbot
        chat_box_ded = st.container(height=450)
        with chat_box_ded:
            if st.session_state.chat_history:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                        if msg.get("role") == "assistant" and msg.get("sources"):
                            with st.expander("🔍 Retrieved Code Templates Used", expanded=False):
                                for s in msg["sources"]:
                                    st.markdown(f"📄 **{s['file']}** (Score: {s['score']:.2f})")
                                    st.code(s["code"], language="python")
            else:
                st.markdown(
                    """
                    <div style='text-align:center; padding: 50px 20px; color:#64748b;'>
                        <h3>How can AI Quant-Coder assist you today?</h3>
                        <p style='font-size:14px;'>Ask me to write backtest codes, mathematical indicator models, or explain trading concepts.</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
        preset_ded_query = ""
        ded_col1, ded_col2, ded_col3 = st.columns(3)
        with ded_col1:
            if st.button("Build Vectorized Backtester", key="ded_preset1", use_container_width=True):
                preset_ded_query = "Build a scikit-learn forecasting model to predict future prices based on lagged return indicators."
        with ded_col2:
            if st.button("Plot EMA Indicators", key="ded_preset2", use_container_width=True):
                preset_ded_query = f"Write Python code using pandas to calculate EMA 12/26 and signal lines for '{ticker_symbol}' and plot it."
        with ded_col3:
            if st.button("RSI Strategy Structure", key="ded_preset3", use_container_width=True):
                preset_ded_query = f"Write a complete vectorized backtest script in Python for a simple RSI crossover strategy on '{ticker_symbol}'."
                
        user_input_ded = st.chat_input("Ask about quantitative code, strategy formulas, or backtesting scripts...", key="chat_input_dedicated")
        if preset_ded_query:
            user_input_ded = preset_ded_query
            
        if user_input_ded:
            current_chat = st.session_state.chats[st.session_state.active_chat_id]
            is_new_session = len(current_chat) == 0
            
            # 1. Rename active chat session immediately if it is a default/new empty session
            if is_new_session and (st.session_state.active_chat_id.startswith("New Chat") or st.session_state.active_chat_id == "Default Session"):
                raw_title = user_input_ded.strip()
                clean_title = "".join([c for c in raw_title if c.isalnum() or c.isspace()])
                words = clean_title.split()
                short_title = " ".join(words[:4]) if words else "Chat Session"
                if len(short_title) > 28:
                    short_title = short_title[:25] + "..."
                if not short_title:
                    short_title = "Chat Session"
                
                unique_title = short_title
                counter = 1
                while unique_title in st.session_state.chats:
                    unique_title = f"{short_title} ({counter})"
                    counter += 1
                
                st.session_state.chats[unique_title] = st.session_state.chats.pop(st.session_state.active_chat_id)
                st.session_state.active_chat_id = unique_title
                # Re-sync st.session_state.chat_history reference to the new key
                st.session_state.chat_history = st.session_state.chats[st.session_state.active_chat_id]
            
            # 2. Append user message and placeholder assistant message immediately
            st.session_state.chat_history.append({"role": "user", "content": user_input_ded})
            st.session_state.chat_history.append({"role": "assistant", "content": "Thinking...", "status": "running"})
            
            # 3. Spawn background thread to query LLM and stream chunks
            history_copy = list(st.session_state.chat_history[:-2]) # Exclude query & placeholder
            chat_list_ref = st.session_state.chat_history
            
            # Compile financial predictor context
            try:
                pred_last_row = df.iloc[-1]
                pred_prev_close = df.iloc[-2]['Close']
                pred_pct_change = ((pred_last_row['Close'] - pred_prev_close) / pred_prev_close) * 100
                pred_rsi_val = pred_last_row['RSI_14']
                pred_rsi_status = "Oversold" if pred_rsi_val < 30 else "Overbought" if pred_rsi_val > 70 else "Neutral"
                pred_sma_diff = pred_last_row['SMA_20'] - pred_last_row['SMA_50']
                pred_sma_trend = "Bullish Crossover (SMA 20 > 50)" if pred_sma_diff > 0 else "Bearish Crossover (SMA 20 < 50)"
                pred_final_pred = pred_df.iloc[-1]['Predicted_Close']
                pred_direction = "UP" if pred_final_pred > pred_last_row['Close'] else "DOWN"
                
                prediction_context = f"""
- Stock Ticker Symbol: {ticker_symbol}
- Current Market Close Price: ${pred_last_row['Close']:.2f} ({pred_pct_change:+.2f}%)
- Relative Strength Index (RSI 14D): {pred_rsi_val:.1f} ({pred_rsi_status})
- Simple Moving Average (SMA) Trend: {pred_sma_trend}
- 30-Day Predicted Forecast Close: ${pred_final_pred:.2f} (predicted trend: {pred_direction})
- Forecasting Model: {engine_name}
"""
            except Exception:
                prediction_context = "No prediction indicators loaded."
            
            t = threading.Thread(
                target=background_stream_worker,
                args=(
                    st.session_state.get("llm_url_input", st.session_state.llm_url),
                    st.session_state.get("llm_key_input", st.session_state.llm_key),
                    st.session_state.get("llm_model_input", st.session_state.llm_model),
                    user_input_ded,
                    history_copy,
                    chat_list_ref,
                    prediction_context,
                    not st.session_state.get("connected", False)
                )
            )
            t.start()
            if "active_threads" not in st.session_state:
                st.session_state.active_threads = {}
            st.session_state.active_threads[st.session_state.active_chat_id] = t
            st.rerun()


# ==========================================
# RENDER PAGE: ⚙️ System Configuration
# ==========================================
elif nav_choice == "⚙️ System Configuration":
    st.markdown("<h2 style='margin-bottom: 2px;'>⚙️ AI Engine Settings & Diagnostics</h2>", unsafe_allow_html=True)
    st.write("Manage local/cloud LLM server URLs and model IDs.")
    
    st.markdown("### 🔌 API Endpoint Configuration")
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        new_url = st.text_input(
            "API Base URL", 
            value=st.session_state.llm_url,
            key="llm_url_input",
            help="For local Ollama use http://127.0.0.1:11434/v1. For AMD Dev Cloud use your GPU public endpoint."
        )
        new_key = st.text_input(
            "API Token (optional)", 
            value=st.session_state.llm_key, 
            type="password",
            key="llm_key_input",
            help="Optional access key. Keep default if using local Ollama."
        )
    with config_col2:
        new_model = st.text_input(
            "Model ID", 
            value=st.session_state.llm_model,
            key="llm_model_input",
            help="Model identifier. e.g. llama3.2, phi3, llama3."
        )
        
    st.write("")
    if st.button("Apply & Save Parameters", use_container_width=True, key="save_params_config"):
        st.session_state.llm_url = new_url
        st.session_state.llm_key = new_key
        st.session_state.llm_model = new_model
        st.toast("System settings updated successfully!", icon="✅")
        st.rerun()

    # Integration guidelines helper
    with st.expander("💡 Quick Integration Guide (Groq & OpenRouter Credentials)", expanded=True):
        st.markdown(
            """
            If you do not have a local Ollama server running, you can connect this app to a high-speed cloud provider using a free API Key:
            
            * **Groq Cloud (Recommended for extreme speed):**
              * **API Base URL:** `https://api.groq.com/openai/v1`
              * **Model ID:** `llama-3.3-70b-versatile`
              * **API Token:** Generate a free key from the **[Groq Console](https://console.groq.com/)** (Settings -> API Keys).
            
            * **OpenRouter (Free Llama models):**
              * **API Base URL:** `https://openrouter.ai/api/v1`
              * **Model ID:** `meta-llama/llama-3.2-3b-instruct:free`
              * **API Token:** Generate a free key from the **[OpenRouter Dashboard](https://openrouter.ai/keys)**.
            
            *Paste these credentials into the configuration fields above, click **Apply & Save Parameters**, and then run the diagnostics!*
            """
        )

    # Diagnostics panel
    st.markdown("### 🔍 Connection Diagnostic Tool")
    st.write("Test connection to the specified endpoint to ensure everything is set up correctly.")
    
    if st.button("Run Connection Diagnostics", key="run_diag_btn"):
        st.write("Pinging server...")
        try:
            url = f"{st.session_state.get('llm_url_input', st.session_state.llm_url).rstrip('/')}/chat/completions"
            payload = {
                "model": st.session_state.get('llm_model_input', st.session_state.llm_model),
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            headers = {}
            api_key = st.session_state.get('llm_key_input', st.session_state.llm_key)
            if api_key and api_key != "no-key-required":
                headers["Authorization"] = f"Bearer {api_key}"
            res = requests.post(url, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                st.markdown(
                    f"""
                    <div style="background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 15px; border-radius: 8px;">
                        <h4 style="margin:0; color:#10b981;">🟢 Diagnostic Passed</h4>
                        <p style="margin:5px 0 0 0; font-size:14px; color:#a7f3d0;">
                            Successfully reached API server <strong>{st.session_state.get('llm_url_input', st.session_state.llm_url)}</strong>.<br>
                            Model <strong>{st.session_state.get('llm_model_input', st.session_state.llm_model)}</strong> is responding successfully!
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 15px; border-radius: 8px;">
                        <h4 style="margin:0; color:#ef4444;">🔴 Diagnostic Failed (Status {res.status_code})</h4>
                        <p style="margin:5px 0 0 0; font-size:14px; color:#fca5a5;">
                            Connected to server port, but model returned error: <strong>{res.text}</strong>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.markdown(
                f"""
                <div style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 15px; border-radius: 8px;">
                    <h4 style="margin:0; color:#ef4444;">🔴 Connection Refused</h4>
                    <p style="margin:5px 0 0 0; font-size:14px; color:#fca5a5;">
                        Server is unreachable at <strong>{st.session_state.get('llm_url_input', st.session_state.llm_url)}</strong>.<br>
                        <strong>Error details:</strong> {type(e).__name__} - {str(e)}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )


# ==========================================
# RENDER PAGE: 👤 Team Profile
# ==========================================
# ==========================================
# RENDER PAGE: ℹ️ About Project
# ==========================================
elif nav_choice == "ℹ️ About Project":
    st.markdown("<h2 style='margin-bottom: 2px;'>ℹ️ About AI Quant-Coder Project</h2>", unsafe_allow_html=True)
    st.write("Project abstract, architectural overview, and core module details.")
    
    st.markdown(
        """
        <div style='background: rgba(30, 41, 59, 0.45); padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 25px;'>
            <h3 style='margin:0 0 10px 0; color:#818cf8;'>💡 Project Abstract</h3>
            <p style='margin:0; font-size:15px; color:#cbd5e1; line-height:1.7;'>
                <strong>AI Quant-Coder</strong> is an advanced, end-to-end web framework engineered to assist quantitative traders in formulating, testing, and understanding strategy bots. By combining a mathematically rigorous financial time-series prediction engine with a custom <strong>Retrieval-Augmented Generation (RAG)</strong> pipeline, the platform helps traders predict asset prices and generate customized algorithmic trading scripts in real-time.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("🏗️ System Architecture & Modules")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.4); padding: 20px; border-radius: 10px; border: 1px solid rgba(99, 102, 241, 0.2); height: 100%;">
                <h4 style="margin:0 0 10px 0; color:#6366f1;">📈 1. Market Predictor Module</h4>
                <p style="font-size:13px; color:#94a3b8; line-height:1.6; margin-bottom:12px;">
                    Integrates historical stock data extraction with complex technical indicator processing and statistical forecasting models:
                </p>
                <ul style="margin:0; padding-left:20px; font-size:13px; color:#cbd5e1; line-height:1.7;">
                    <li><strong>Live Market Feeds:</strong> Downloads historical asset price records via the yfinance API.</li>
                    <li><strong>Technical Analytics:</strong> Computes rolling Simple/Exponential Moving Averages (SMA/EMA) and Relative Strength Index (RSI).</li>
                    <li><strong>ARIMA Forecasting:</strong> Fits statistical Autoregressive Integrated Moving Average models on 10 years of records to predict future 30-day close targets.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.4); padding: 20px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.2); height: 100%;">
                <h4 style="margin:0 0 10px 0; color:#10b981;">💬 2. RAG Coding Assistant</h4>
                <p style="font-size:13px; color:#94a3b8; line-height:1.6; margin-bottom:12px;">
                    Generates production-grade algorithmic trading scripts tailored to predictions using a lightweight vector database:
                </p>
                <ul style="margin:0; padding-left:20px; font-size:13px; color:#cbd5e1; line-height:1.7;">
                    <li><strong>Lightweight Vector Database:</strong> Uses TF-IDF similarity vectors to index code templates on functional boundaries.</li>
                    <li><strong>Predictor Integration:</strong> Automatically appends real-time close prices, RSI status, and forecast targets into the LLM system prompt.</li>
                    <li><strong>ROCm Accelerated LLM:</strong> Streams script responses in real-time, optimized for AMD Developer Cloud GPU execution.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.subheader("⚡ Core Hackathon Innovations")
    
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown(
            """
            <div class="metric-card" style="height: 100%;">
                <h5 style="margin:0 0 8px 0; color:#a5b4fc;">🔄 Isolated Streaming</h5>
                <p style="margin:0; font-size:13px; color:#94a3b8; line-height:1.5;">
                    Runs LLM queries on background worker threads, allowing the frontend to remain highly responsive and letting you start or view other sessions seamlessly.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_feat2:
        st.markdown(
            """
            <div class="metric-card" style="height: 100%;">
                <h5 style="margin:0 0 8px 0; color:#f59e0b;">🖥️ Swapable Layouts</h5>
                <p style="margin:0; font-size:13px; color:#94a3b8; line-height:1.5;">
                    Adjust split focus and swap panel positioning (Graph Left / Chat Right vs Chat Left / Graph Right) directly on the page to customize your workspace.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_feat3:
        st.markdown(
            """
            <div class="metric-card" style="height: 100%;">
                <h5 style="margin:0 0 8px 0; color:#10b981;">🔌 Server Ready</h5>
                <p style="margin:0; font-size:13px; color:#94a3b8; line-height:1.5;">
                    Features native support to route API requests to remote high-throughput vLLM backends accelerated by AMD ROCm GPU servers.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.write("")
    st.subheader("👥 Hackathon Team Members")
    team_col1, team_col2 = st.columns(2)
    with team_col1:
        st.markdown(
            """
            <div class="metric-card" style="text-align: center; padding: 20px;">
                <h4 style="margin:0; color:#818cf8;">Agha Essa Khan</h4>
                <p style="margin:5px 0 0 0; font-size:14px; color:#cbd5e1; font-weight:600;">Team Lead & Full-Stack Developer</p>
                <p style="margin:8px 0 0 0; font-size:12px; color:#94a3b8; line-height:1.5;">
                    Built the prediction system integration, database architecture, and RAG search index orchestration.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with team_col2:
        st.markdown(
            """
            <div class="metric-card" style="text-align: center; padding: 20px;">
                <h4 style="margin:0; color:#10b981;">Misbah Ramzan</h4>
                <p style="margin:5px 0 0 0; font-size:14px; color:#cbd5e1; font-weight:600;">Data Scientist & Quant Developer</p>
                <p style="margin:8px 0 0 0; font-size:12px; color:#94a3b8; line-height:1.5;">
                    Engineered the time-series ARIMA prediction engine, technical indicators calculations, and strategy backtesters.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

# Always save chat history to file at the end of execution to persist streaming & user updates
save_persistent_chats()

# Periodic background refresh loop when model is generating in background
if "active_threads" in st.session_state:
    # Only poll/refresh if the CURRENTLY viewed chat is generating
    curr_thread = st.session_state.active_threads.get(st.session_state.active_chat_id)
    if curr_thread and curr_thread.is_alive():
        time.sleep(0.2)  # Fast response streaming update
        st.rerun()
