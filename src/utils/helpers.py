import streamlit as st

def initialize_session_state():
    """
    Setup default Streamlit session state keys.
    """
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "llm_url" not in st.session_state:
        st.session_state.llm_url = "http://127.0.0.1:11434/v1"
    if "llm_key" not in st.session_state:
        st.session_state.llm_key = "no-key-required"
    if "llm_model" not in st.session_state:
        st.session_state.llm_model = "llama3.2"

def inject_custom_css():
    """
    Inject vibrant dark-themed styling, fonts, and container animations.
    """
    css_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        /* Apply Outfit font across the app */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Outfit', sans-serif !important;
        }
        
        /* Main background & moving gradient animation */
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .stApp {
            background: linear-gradient(-45deg, #090d16, #111827, #1e1b4b, #030712) !important;
            background-size: 400% 400% !important;
            animation: gradientBG 18s ease infinite !important;
        }
        
        /* Floating background glow blobs */
        @keyframes float {
            0% { transform: translateY(0px) translateX(0px) scale(1); }
            50% { transform: translateY(-40px) translateX(30px) scale(1.1); }
            100% { transform: translateY(0px) translateX(0px) scale(1); }
        }
        @keyframes float-reverse {
            0% { transform: translateY(0px) translateX(0px) scale(1.1); }
            50% { transform: translateY(40px) translateX(-30px) scale(1); }
            100% { transform: translateY(0px) translateX(0px) scale(1.1); }
        }
        .glow-blob {
            position: fixed !important;
            border-radius: 50% !important;
            filter: blur(130px) !important;
            opacity: 0.16 !important;
            z-index: -99 !important; /* Send to absolute back */
            pointer-events: none !important;
        }
        .blob-1 {
            width: 450px !important;
            height: 450px !important;
            background: #4f46e5 !important;
            top: -150px !important;
            left: -100px !important;
            animation: float 22s infinite ease-in-out !important;
        }
        .blob-2 {
            width: 500px !important;
            height: 500px !important;
            background: #db2777 !important;
            bottom: -200px !important;
            right: -100px !important;
            animation: float-reverse 26s infinite ease-in-out !important;
        }
        
        /* Customized cards styling */
        .metric-card {
            background: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(12px);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.15);
        }
        
        /* Profile cards styling */
        .profile-container {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .profile-card {
            background: rgba(30, 41, 59, 0.35);
            backdrop-filter: blur(8px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 25px;
            flex: 1;
            min-width: 280px;
            text-align: center;
            transition: all 0.3s ease;
        }
        .profile-card:hover {
            transform: translateY(-4px);
            border-color: rgba(129, 140, 248, 0.5);
            box-shadow: 0 12px 30px rgba(129, 140, 248, 0.12);
        }
        
        .profile-avatar {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1 0%, #a5b4fc 100%);
            margin: 0 auto 15px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            color: white;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }
        
        .profile-name {
            font-size: 20px;
            font-weight: 600;
            color: #f8fafc;
            margin: 10px 0 5px 0;
        }
        
        .profile-role {
            font-size: 14px;
            color: #818cf8;
            font-weight: 500;
            margin-bottom: 12px;
        }
        
        .profile-desc {
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }
        
        /* Titles and headers */
        h1, h2, h3 {
            color: #f8fafc !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em;
        }
        
        .gradient-text {
            background: linear-gradient(135deg, #a5b4fc 0%, #818cf8 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Sidebar styling override */
        section[data-testid="stSidebar"] {
            background-color: rgb(15, 23, 42) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        /* Premium Sidebar Radio Navigation Override (Solid Bars Style) */
        [data-testid="stSidebar"] div[data-testid="stRadio"] {
            background: transparent !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 12px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
            background: rgba(15, 23, 42, 0.4) !important;
            border: 1px solid rgba(255, 255, 255, 0.04) !important;
            border-left: 4px solid transparent !important; /* Invisible indicator for inactive bars */
            border-radius: 6px !important;
            padding: 12px 18px !important;
            margin: 0 !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            background: rgba(99, 102, 241, 0.08) !important;
            border-color: rgba(99, 102, 241, 0.2) !important;
            border-left: 4px solid rgba(99, 102, 241, 0.4) !important;
            transform: translateX(4px) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: rgba(99, 102, 241, 0.14) !important;
            border-color: rgba(99, 102, 241, 0.4) !important;
            border-left: 4px solid #6366f1 !important; /* Left active bar indicator */
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.08) !important;
        }
        /* Completely hide default circular radio selectors inside the sidebar */
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] div[data-testid="stMarkdownContainer"] p {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div[data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        

        /* Dynamic micro-animations for interactive components */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: white !important;
            border: None !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        div.stButton > button:first-child:hover {
            transform: scale(1.02) !important;
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.4) !important;
        }
        div.stButton > button:first-child:disabled {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            opacity: 1.0 !important;
            border: None !important;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.45) !important;
            cursor: not-allowed !important;
            transform: none !important;
        }
        
        /* Diagnostic card styling */
        .diagnostic-card {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 15px;
            margin-top: 15px;
        }
    </style>
    """
    st.markdown(css_content, unsafe_allow_html=True)
    
    # Inject background floating glow blobs
    st.markdown(
        """
        <div class="glow-blob blob-1"></div>
        <div class="glow-blob blob-2"></div>
        """,
        unsafe_allow_html=True
    )
