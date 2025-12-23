import streamlit as st
import time
import base64
import textwrap
import os
import uuid
from dotenv import load_dotenv
from neo4j import GraphDatabase
from agent import NvidiaSentinelAgent
import auth
try:
    from streamlit_agraph import agraph, Node, Edge, Config
except ImportError:
    st.error("Please install streamlit-agraph: pip install streamlit-agraph")

# --- 1. CONFIGURATION ---
load_dotenv()
st.set_page_config(
    page_title="NVIDIA SENTINEL",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SESSION MANAGEMENT ---
if "sessions" not in st.session_state:
    default_id = str(uuid.uuid4())
    st.session_state.sessions = {}
    st.session_state.current_id = ""
    st.session_state.pinned_sessions = set()
    st.session_state.user = None
    st.session_state.authenticated = False

# --- 2b. AUTH LOGIC ---
def login_user(username, password):
    if auth.check_credentials(username, password):
        st.session_state.authenticated = True
        st.session_state.user = username
        # Load History
        sessions, current_id = auth.load_user_history(username)
        pinned = auth.load_pinned(username)
        st.session_state.sessions = sessions
        st.session_state.current_id = current_id
        st.session_state.pinned_sessions = pinned
        st.rerun()
    else:
        st.error("Invalid credentials")

def signup_user(username, password):
    if auth.sign_up(username, password):
        st.success("Account created! Please log in.")
    else:
        st.error("Username already exists.")

def logout_user():
    # Save before exit
    if st.session_state.user:
        auth.save_user_history(
            st.session_state.user, 
            st.session_state.sessions, 
            st.session_state.current_id,
            st.session_state.pinned_sessions
        )
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

def create_new_session():
    new_id = str(uuid.uuid4())
    st.session_state.sessions[new_id] = []
    st.session_state.current_id = new_id

def delete_session(session_id):
    if session_id in st.session_state.sessions:
        del st.session_state.sessions[session_id]
        if session_id in st.session_state.pinned_sessions:
            st.session_state.pinned_sessions.remove(session_id)
        
        # If we deleted the current one, switch to another or create new
        if st.session_state.current_id == session_id:
            remaining = list(st.session_state.sessions.keys())
            if remaining:
                st.session_state.current_id = remaining[0]
            else:
                create_new_session()
        st.rerun()

def toggle_pin(session_id):
    if session_id in st.session_state.pinned_sessions:
        st.session_state.pinned_sessions.remove(session_id)
    else:
        st.session_state.pinned_sessions.add(session_id)
    st.rerun()

def get_session_name(session_id):
    messages = st.session_state.sessions[session_id]
    if not messages: return "New Chat"
    for msg in messages:
        if msg["role"] == "user":
            return " ".join(msg["content"].split()[:3]) + "..."
    return "New Chat"

# --- 3. MINIMALIST CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Global Background */
    .stApp {
        background-color: #050505;
        background-image: 
            radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #ffffff; }
    .mono { font-family: 'JetBrains Mono', monospace; color: #888; font-size: 0.8rem; }

    /* User Message Style */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
    }
    
    /* Assistant Message Style */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: transparent;
        border: none;
        padding-left: 0px;
    }

    /* GLASS CARD */
    .glass-card {
        background: rgba(16, 185, 129, 0.05);
        border-left: 3px solid #10b981;
        padding: 20px;
        border-radius: 0px 12px 0px 0px;
        margin-top: 10px;
        backdrop-filter: blur(5px);
    }
    
    /* EXPANDER STYLING */
    div[data-testid="stExpander"] {
        background: rgba(16, 185, 129, 0.02);
        border-left: 3px solid #10b981;
        border-radius: 12px 0px 12px 12px;
        margin-top: 4px;
        border-top: none; border-right: none;
        border-bottom: 1px solid rgba(16, 185, 129, 0.2);
    }
    .streamlit-expanderHeader {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem !important;
        color: #888 !important;
        background-color: transparent !important;
    }
    .streamlit-expanderHeader:hover {
        color: #888 !important;
        background-color: transparent !important;
    }
    .streamlit-expanderHeader svg { fill: #888 !important; }

    /* HISTORY BUTTONS */
    section[data-testid="stSidebar"] .stButton button {
        width: 100%;
        border: none;
        background: transparent;
        color: #888;
        text-align: left;
        padding: 12px;
        transition: 0.2s;
        border-left: 2px solid transparent;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #111;
        color: #fff;
        border-left: 2px solid #10b981;
    }

    /* NEW CHAT BUTTON (Top Left) */
    .new-chat-btn button {
        background: transparent;
        border: 1px solid #333;
        color: #10b981;
        border-radius: 8px; /* Slightly squarer for tech look */
        width: 45px;
        height: 45px;
        font-size: 1.2rem;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 10px; /* Align with Logo */
    }
    .new-chat-btn button:hover {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
        color: #fff;
    }

    /* Animation Classes */
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    .animate-new { animation: fadeIn 0.8s ease-out; }

    /* LOGIN PAGE STYLES */
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify_content: center;
        animation: fadeIn 1.5s ease-in-out;
        margin-top: 100px;
    }
    .login-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #fff, #bbb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }

    /* Hide Defaults */
    /* Header Adjustments to show Hamburger */
    header { visibility: visible !important; background: transparent !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Style the Sidebar Toggle (Collapsed Control) */
    [data-testid="stSidebarCollapsedControl"] {
        color: #10b981 !important; /* Green Accent */
        background-color: transparent !important;
    }
    
    /* Popover Button Styling (The three dots) */
    button[data-testid="stPopoverButton"] {
        border: none;
        background: transparent;
        color: #666;
    }
    button[data-testid="stPopoverButton"]:hover {
        color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }

    section[data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #222; }
</style>
""", unsafe_allow_html=True)

# --- 4. BACKEND SETUP ---
@st.cache_resource
def get_agent_v5():
    return NvidiaSentinelAgent()

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# --- 5. HEADER COMPONENT ---
def render_header():
    img_base64 = get_base64_of_bin_file("nvidia_logo.png")
    
    # LAYOUT: [Logo + Title] ------------------
    col_title = st.columns([1])[0]
    
    with col_title:
        if img_base64:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 20px;">
                <img src="data:image/png;base64,{img_base64}" style="width: 50px; height: 50px; object-fit: contain;">
                <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -1px; background: linear-gradient(90deg, #fff, #bbb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    NVIDIA SENTINEL
                </h1>
            </div>
            """, unsafe_allow_html=True)
    
    # The Line
    st.markdown("""
    <div style="display: flex; align-items: center; width: 100%; margin-bottom: 30px; margin-top: 10px;">
        <div style="flex-grow: 1; height: 2px; background: linear-gradient(90deg, #10b981 0%, transparent 100%); margin-right: 20px;"></div>
        <div class="mono" style="color: #666; letter-spacing: 2px;">MARKET MIND <span style="color: #10b981;">v2.5</span></div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. SIDEBAR (History Only) ---

# --- 7. PAGES ---

def login_page():
    img_base64 = get_base64_of_bin_file("nvidia_logo.png")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="login-container">
            <div style="display: flex; align-items: center; gap: 20px; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{img_base64}" style="width: 80px; height: 80px; object-fit: contain;"> 
            </div>
            <div class="login-header">NVIDIA SENTINEL</div>
            <div class="mono" style="margin-bottom: 40px; color: #10b981;">SECURE ACCESS PORTAL</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
            
            with tab1:
                u = st.text_input("Username", key="l_u")
                p = st.text_input("Password", type="password", key="l_p")
                if st.button("AUTHENTICATE", use_container_width=True, type="primary"):
                    login_user(u, p)
            
            with tab2:
                nu = st.text_input("New Username", key="r_u")
                np = st.text_input("New Password", type="password", key="r_p")
                if st.button("CREATE ID", use_container_width=True):
                    signup_user(nu, np)

def main_app():
    render_header()
    
    # --- SIDEBAR CONTENT (Inside function to avoid rendering on login) ---
    with st.sidebar:
        # --- NEW CHAT BUTTON ---
        st.markdown('<div class="new-chat-btn" style="margin-bottom: 20px;">', unsafe_allow_html=True)
        if st.button("➕ New Chat", use_container_width=True):
            create_new_session()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### 🗄️ HISTORY")
        
        # 1. Sort Sessions: Pinned First, then Latest
        all_sessions = list(st.session_state.sessions.keys())[::-1] # Reverse Chronological
        pinned = [sid for sid in all_sessions if sid in st.session_state.pinned_sessions]
        others = [sid for sid in all_sessions if sid not in st.session_state.pinned_sessions]
        
        display_list = pinned + others
        
        for sid in display_list:
            label = get_session_name(sid)
            if sid in st.session_state.pinned_sessions:
                label = f"📌 {label}"
                
            col_chat, col_menu = st.columns([0.85, 0.15])
            with col_chat:
                btn_type = "primary" if sid == st.session_state.current_id else "secondary"
                if st.button(label, key=f"hist_{sid}", use_container_width=True):
                    st.session_state.current_id = sid
                    st.rerun()
            with col_menu:
                with st.popover("⋮", use_container_width=True):
                    pin_label = "Unpin" if sid in st.session_state.pinned_sessions else "Pin"
                    if st.button(f"📌 {pin_label}", key=f"pin_{sid}", use_container_width=True): toggle_pin(sid)
                    if st.button("🗑️ Delete", key=f"del_{sid}", use_container_width=True): delete_session(sid)
        
        st.markdown("---")
        st.markdown("### 🚀 QUICK INTEL")
        SUGGESTED_QUESTIONS = [
            "Who supplies TSMC?",
            "How would a Taiwan blockade affect Nvidia?",
            "What products does ASML manufacture?",
            "Identify critical supply chain risks."
        ]
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, use_container_width=True):
                st.session_state["suggested_input"] = q
                st.rerun()
                
        # --- USER PROFILE ---
        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"**👤 {st.session_state.user.upper()}**")
            if st.button("🚪 Logout", use_container_width=True):
                logout_user()

    # --- MAIN CHAT RENDER ---
    current_messages = st.session_state.sessions.get(st.session_state.current_id, [])
    
    for i, message in enumerate(current_messages):
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                is_last = (i == len(current_messages) - 1)
                content = message["content"]
                if is_last: content = content.replace('class="glass-card"', 'class="glass-card animate-new"')
                
                st.markdown(content, unsafe_allow_html=True)
                if "cypher" in message and message["cypher"]:
                    with st.expander("▶ VIEW SOURCE LOGIC"): 
                        st.code(message["cypher"], language="cypher")
                
                if "graph_data" in message and message["graph_data"]:
                    with st.expander("🕸️ NEURAL GRID", expanded=True):
                        g_data = message["graph_data"]
                        nodes = [Node(id=n["id"], label=n["label"], size=15, color="#10b981") for n in g_data["nodes"]]
                        edges = [Edge(source=e["source"], target=e["target"], type="CURVE_SMOOTH") for e in g_data["edges"]]
                        config = Config(width="100%", height=400, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6", collapsible=False)
                        agraph(nodes=nodes, edges=edges, config=config)

    # Input
    if prompt := (st.session_state.get("suggested_input") or st.chat_input("Query the Supply Chain...")):
        if "suggested_input" in st.session_state: del st.session_state["suggested_input"]

        if st.session_state.current_id not in st.session_state.sessions:
             st.session_state.sessions[st.session_state.current_id] = []
             
        st.session_state.sessions[st.session_state.current_id].append({"role": "user", "content": prompt})
        
        with st.spinner("🔍 Analyzing..."):
            try:
                agent = get_agent_v5()
                response_data = agent.ask(prompt)
                
                final_html_card = textwrap.dedent(f"""
                <div class="glass-card">
                    <h4 style="color: #10b981; margin: 0 0 10px 0;">⚡ INTELLIGENCE REPORT</h4>
                    <div style="font-size: 1rem; line-height: 1.6; color: #e0e0e0;">
                        {response_data['result']}
                    </div>
                </div>
                """)
                
                # Only visualize if it's a DATA query
                graph_data = None
                if "General Conversation" not in response_data['cypher'] and "Error" not in response_data['cypher']:
                    graph_data = agent.visualize_query_neighborhood(prompt)

                st.session_state.sessions[st.session_state.current_id].append({
                    "role": "assistant", 
                    "content": final_html_card,
                    "cypher": response_data['cypher'],
                    "graph_data": graph_data
                })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- EXECUTION ---
if not st.session_state.authenticated:
    login_page()
else:
    main_app()