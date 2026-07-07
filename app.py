"""
app.py
======
Streamlit front door for the SQL Chatbot.

Run with:  streamlit run app.py

Flow:
  - Not logged in -> Login / Register tabs
  - Logged in     -> Sidebar with chat history + main chat area
"""

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from db import ensure_databases, create_session, get_sessions, get_messages, save_message, delete_session
from auth import register_user, authenticate_user
from guardrails import check_input

load_dotenv()

st.set_page_config(
    page_title="Campus Query — SQL Chatbot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_databases()

# ----------------------------------------------------------------------
# STYLE
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --navy: #0E1420;
        --navy-2: #161E2E;
        --card: #1B2434;
        --amber: #E3A857;
        --amber-soft: rgba(227, 168, 87, 0.14);
        --text: #E9EDF5;
        --muted: #8B96AB;
        --border: #2A3547;
        --good: #6FCF97;
        --bad: #E37373;
    }

    html, body, [class*="css"]  {
        font-family: 'Space Grotesk', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 15% 0%, #182034 0%, var(--navy) 45%);
        color: var(--text);
    }

    section[data-testid="stSidebar"] {
        background: var(--navy-2);
        border-right: 1px solid var(--border);
    }

    /* Hide default streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}

    .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0 18px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 14px;
    }
    .brand .mark {
        font-size: 26px;
    }
    .brand .name {
        font-weight: 700;
        font-size: 20px;
        letter-spacing: 0.2px;
    }
    .brand .tag {
        font-size: 11px;
        color: var(--muted);
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .auth-card {
        max-width: 440px;
        margin: 6vh auto 0 auto;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 40px 36px 30px 36px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    }
    .auth-hero {
        text-align: center;
        margin-bottom: 28px;
    }
    .auth-hero .glyph {
        font-size: 40px;
        display: block;
        margin-bottom: 6px;
    }
    .auth-hero h1 {
        font-size: 24px;
        margin: 0;
        font-weight: 700;
    }
    .auth-hero p {
        color: var(--muted);
        font-size: 13.5px;
        margin-top: 6px;
    }

    .stTextInput input, .stTextInput > div > div {
        background: var(--navy) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
    }

    div.stButton > button {
        width: 100%;
        background: var(--amber) !important;
        color: #1A1206 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.55rem 0 !important;
        transition: transform 0.08s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.06);
    }

    .session-pill {
        padding: 9px 12px;
        border-radius: 8px;
        border: 1px solid var(--border);
        margin-bottom: 6px;
        font-size: 13px;
        color: var(--text);
        cursor: pointer;
    }
    .session-pill:hover {
        border-color: var(--amber);
    }

    .badge-guard {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: var(--bad);
        background: rgba(227, 115, 115, 0.12);
        border: 1px solid rgba(227,115,115,0.4);
        border-radius: 6px;
        padding: 2px 8px;
        margin-bottom: 6px;
    }

    .stChatMessage {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    .stat-row {
        display: flex; gap: 10px; margin: 4px 0 18px 0;
    }
    .stat-chip {
        flex: 1;
        background: var(--amber-soft);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 12px;
        text-align: center;
    }
    .stat-chip .n { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: var(--amber); font-weight: 600;}
    .stat-chip .l { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "agent" not in st.session_state:
    st.session_state.agent = None
if "auth_notice" not in st.session_state:
    st.session_state.auth_notice = None


def get_agent():
    """Lazily build the LangGraph agent (needs GROQ_API_KEY)."""
    if st.session_state.agent is not None:
        return st.session_state.agent

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    from sql_agent import build_agent  # imported lazily so the app still loads without the key

    st.session_state.agent = build_agent(api_key)
    return st.session_state.agent


# ----------------------------------------------------------------------
# LOGIN / REGISTER VIEW
# ----------------------------------------------------------------------
def render_auth():
    st.markdown(
        """
        <div class="auth-card">
            <div class="auth-hero">
                <span class="glyph">🎓</span>
                <h1>Campus Query</h1>
                <p>Your conversational window into the student database</p>
            </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            identifier = st.text_input("Username or email", key="login_id")
            password = st.text_input("Password", type="password", key="login_pw")
            submitted = st.form_submit_button("Log In")
            if submitted:
                user = authenticate_user(identifier, password)
                if user:
                    st.session_state.user = user
                    st.session_state.active_session_id = None
                    st.rerun()
                else:
                    st.error("Incorrect username/email or password.")

    with tab_register:
        with st.form("register_form", clear_on_submit=False):
            r_username = st.text_input("Username", key="reg_username")
            r_email = st.text_input("Email", key="reg_email")
            r_password = st.text_input("Password", type="password", key="reg_pw")
            r_confirm = st.text_input("Confirm password", type="password", key="reg_pw2")
            submitted = st.form_submit_button("Create Account")
            if submitted:
                ok, msg = register_user(r_username, r_email, r_password, r_confirm)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# SIDEBAR (post-login)
# ----------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
                <span class="mark">🎓</span>
                <div>
                    <div class="name">Campus Query</div>
                    <div class="tag">SQL Chatbot</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"**Signed in as** `{st.session_state.user['username']}`")

        if st.button("＋ New Chat"):
            st.session_state.active_session_id = None
            st.rerun()

        st.markdown("#### History")
        sessions = get_sessions(st.session_state.user["user_id"])

        if not sessions:
            st.caption("No conversations yet — ask something to get started.")
        else:
            for s in sessions:
                cols = st.columns([5, 1])
                label = s["title"] if len(s["title"]) < 34 else s["title"][:31] + "…"
                if cols[0].button(label, key=f"sess_{s['session_id']}"):
                    st.session_state.active_session_id = s["session_id"]
                    st.rerun()
                if cols[1].button("🗑", key=f"del_{s['session_id']}"):
                    delete_session(s["session_id"])
                    if st.session_state.active_session_id == s["session_id"]:
                        st.session_state.active_session_id = None
                    st.rerun()

        st.markdown("---")
        if st.button("Log Out"):
            st.session_state.user = None
            st.session_state.active_session_id = None
            st.session_state.agent = None
            st.rerun()

        st.caption("Guardrails active: input moderation + read-only SQL only.")


# ----------------------------------------------------------------------
# MAIN CHAT VIEW
# ----------------------------------------------------------------------
def render_chat():
    st.markdown(
        """
        <div class="stat-row">
            <div class="stat-chip"><div class="n">6</div><div class="l">Tables</div></div>
            <div class="stat-chip"><div class="n">8</div><div class="l">Students</div></div>
            <div class="stat-chip"><div class="n">6</div><div class="l">Courses</div></div>
            <div class="stat-chip"><div class="n">🛡️</div><div class="l">Guardrails On</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    api_key_present = bool(os.getenv("GROQ_API_KEY"))
    if not api_key_present:
        st.warning(
            "No `GROQ_API_KEY` found in your environment. Add one to a `.env` file "
            "(see `.env.example`) to enable live responses. The chat UI, guardrails, "
            "and history still work below."
        )

    session_id = st.session_state.active_session_id
    history = get_messages(session_id) if session_id else []

    for msg in history:
        avatar = "🧑" if msg["role"] == "user" else "🎓"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["blocked"]:
                st.markdown('<span class="badge-guard">BLOCKED BY GUARDRAIL</span>', unsafe_allow_html=True)
            st.write(msg["content"])

    prompt = st.chat_input("Ask about students, courses, grades, attendance…")
    if prompt:
        allowed, reason = check_input(prompt)

        if session_id is None:
            title = prompt.strip()[:40] or "New conversation"
            session_id = create_session(st.session_state.user["user_id"], title)
            st.session_state.active_session_id = session_id

        with st.chat_message("user", avatar="🧑"):
            st.write(prompt)
        save_message(session_id, "user", prompt)

        with st.chat_message("assistant", avatar="🎓"):
            if not allowed:
                st.markdown('<span class="badge-guard">BLOCKED BY GUARDRAIL</span>', unsafe_allow_html=True)
                st.write(reason)
                save_message(session_id, "assistant", reason, blocked=True)
            else:
                agent = get_agent()
                if agent is None:
                    reply = (
                        "I can't reach the language model yet because `GROQ_API_KEY` "
                        "isn't set. Add it to your `.env` file and restart the app."
                    )
                    st.write(reply)
                    save_message(session_id, "assistant", reply)
                else:
                    with st.spinner("Querying the database…"):
                        from sql_agent import ask_agent

                        try:
                            reply = ask_agent(agent, thread_id=str(session_id), question=prompt)
                        except Exception as e:
                            reply = f"Something went wrong while answering: {e}"
                    st.write(reply)
                    save_message(session_id, "assistant", reply)

        st.rerun()


# ----------------------------------------------------------------------
# ROUTER
# ----------------------------------------------------------------------
if st.session_state.user is None:
    render_auth()
else:
    render_sidebar()
    st.title("🎓 Campus Query")
    st.caption("Ask questions in plain English — the agent inspects the schema and writes safe SQL for you.")
    render_chat()