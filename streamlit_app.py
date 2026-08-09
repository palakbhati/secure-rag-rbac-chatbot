"""
The user-facing app. Ties together everything built so far:

    Streamlit (this file)
        -> demo auth (app.services.auth.demo_users) -> role
        -> app.services.rag.pipeline.ask(question, role)
            -> input guardrail -> RBAC -> retrieval -> LLM -> output guardrail

DEMO AUTH ONLY — see demo_users.py's docstring.

UI REDESIGN v2 — full rebuild from scratch, not a patch on v1.

ROOT CAUSE OF v1's CONTRAST BUG, fixed here: v1 only styled the custom
HTML/CSS I injected, but never forced Streamlit's own base theme. A
visitor's browser/OS dark-mode preference made Streamlit's NATIVE
widgets (input labels, button text, captions) render in light colors,
against the light backgrounds my custom CSS drew — invisible text.
The fix lives in .streamlit/config.toml: it forces base="light" with
an explicit palette, so native widgets and custom CSS now share the
same color assumptions and can never fight each other again.

BACKEND INTEGRATION POINTS — unchanged from every prior phase:
  - authenticate(username, password) -> role | None
  - ask(question, role, user_id) -> result dict
Every call site below passes the same arguments, in the same way, and
uses the same return value shape as before. Nothing in app/rbac/,
app/guardrails/, app/services/, or evaluation/ was touched.
"""

from datetime import datetime

import streamlit as st

from app.services.auth.demo_users import authenticate
from app.services.rag.pipeline import ask

st.set_page_config(
    page_title="FinSolve Internal Assistant",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUGGESTIONS = [
    ("Leave & Benefits", "What is the company's leave policy?"),
    ("HR Policies", "What is the process for applying for leave?"),
    ("Insurance", "What insurance benefits does the company provide?"),
    ("Engineering", "What frontend technologies does the company use?"),
]


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        .stApp { background-color: #F7F8FA; }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 6rem;
            max-width: 760px;
        }

        /* Force every plain-text element we didn't explicitly color to
           the dark charcoal body color, so no native-widget text can
           ever silently inherit a light color again. */
        p, span, label, .stMarkdown, .stCaption {
            color: #111827;
        }
        .stCaption, small { color: #6B7280 !important; }

        /* ================= SIDEBAR ================= */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E5E7EB;
        }
        section[data-testid="stSidebar"] .block-container { padding-top: 1.25rem; }

        .brand-row { display: flex; align-items: center; gap: 10px; margin-bottom: 2px; }
        .brand-mark {
            width: 32px; height: 32px; border-radius: 8px;
            background: #2563EB; color: #FFFFFF;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 15px; flex-shrink: 0;
        }
        .brand-name { font-weight: 700; font-size: 16px; color: #111827; }
        .brand-sub { font-size: 12px; color: #6B7280; margin: 0 0 16px 42px; }

        .sidebar-section-title {
            font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
            color: #6B7280; text-transform: uppercase;
            margin: 18px 0 6px 2px;
        }

        div[data-testid="stSidebar"] .stButton > button {
            background: transparent; border: none; box-shadow: none;
            text-align: left; justify-content: flex-start;
            color: #374151; font-size: 13.5px; font-weight: 400;
            padding: 6px 8px; border-radius: 6px;
        }
        div[data-testid="stSidebar"] .stButton > button:hover {
            background: #F3F4F6; color: #111827;
        }
        .st-key-new_chat_btn .stButton > button {
            background: #2563EB !important; color: #FFFFFF !important;
            font-weight: 600 !important; justify-content: center !important;
            padding: 8px !important; border-radius: 8px !important;
        }
        .st-key-new_chat_btn .stButton > button:hover { background: #1D4ED8 !important; }
        .st-key-logout_btn .stButton > button {
            border: 1px solid #E5E7EB !important; justify-content: center !important;
            color: #374151 !important; border-radius: 8px !important;
        }
        .st-key-logout_btn .stButton > button:hover {
            border-color: #DC2626 !important; color: #DC2626 !important; background: #FEF2F2 !important;
        }

        .profile-card {
            background: #F7F8FA; border: 1px solid #E5E7EB; border-radius: 10px;
            padding: 10px 12px; margin-top: 8px;
        }
        .profile-name { font-weight: 600; font-size: 13.5px; color: #111827; }
        .profile-role { font-size: 12px; color: #6B7280; text-transform: capitalize; margin: 1px 0 5px 0; }
        .profile-status { font-size: 11px; color: #16A34A; font-weight: 600; }
        .profile-status::before { content: "●"; margin-right: 5px; }

        /* ================= LOGIN ================= */
        .login-wrap { display: flex; flex-direction: column; align-items: center; padding-top: 6vh; }
        .login-logo {
            width: 52px; height: 52px; border-radius: 12px; background: #2563EB; color: #FFFFFF;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 24px; margin-bottom: 14px;
        }
        .login-title { font-size: 22px; font-weight: 700; color: #111827; margin: 0; text-align: center; }
        .login-subtitle { font-size: 14px; color: #6B7280; margin: 4px 0 22px 0; text-align: center; }
        .login-card {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px;
            box-shadow: 0 1px 3px rgba(16,24,40,0.06), 0 1px 2px rgba(16,24,40,0.04);
            padding: 28px 28px 18px 28px; width: 100%; max-width: 420px;
        }
        .login-card-title { font-size: 15px; font-weight: 600; color: #111827; margin-bottom: 14px; }
        .login-tagline { margin-top: 20px; font-size: 12.5px; color: #6B7280; text-align: center; }
        div[data-testid="stForm"] input {
            border: 1px solid #E5E7EB !important; border-radius: 8px !important;
            color: #111827 !important; background: #FFFFFF !important;
        }
        div[data-testid="stForm"] label { color: #374151 !important; font-size: 13px !important; font-weight: 500 !important; }
        div[data-testid="stForm"] .stButton > button {
            background: #2563EB !important; color: #FFFFFF !important; border: none !important;
            font-weight: 600 !important; border-radius: 8px !important; padding: 9px 0 !important;
        }
        div[data-testid="stForm"] .stButton > button:hover { background: #1D4ED8 !important; }
        .stAlert { border-radius: 8px !important; }

        /* ================= CHAT HEADER ================= */
        .chat-header {
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 14px; margin-bottom: 18px; border-bottom: 1px solid #E5E7EB;
            flex-wrap: wrap; gap: 10px;
        }
        .chat-header-left h1 { font-size: 21px; font-weight: 700; color: #111827; margin: 0 0 2px 0; }
        .chat-header-left .subtitle-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .chat-header-left p { font-size: 13.5px; color: #6B7280; margin: 0; }
        .secure-badge {
            font-size: 11.5px; color: #16A34A; background: #F0FDF4; border: 1px solid #BBF7D0;
            padding: 2px 8px; border-radius: 20px; font-weight: 500;
        }
        .secure-badge::before { content: "●"; margin-right: 4px; }
        .header-user-chip { text-align: right; }
        .header-user-chip .name { font-size: 13.5px; font-weight: 600; color: #111827; }
        .header-user-chip .role { font-size: 12px; color: #6B7280; text-transform: capitalize; }

        /* ================= WELCOME ================= */
        .welcome-greeting h2 { font-size: 20px; font-weight: 700; color: #111827; margin-bottom: 4px; }
        .welcome-greeting p { font-size: 14px; color: #6B7280; max-width: 560px; line-height: 1.6; }

        .st-key-sugg_grid .stButton > button {
            width: 100%; text-align: left; justify-content: flex-start; flex-direction: column;
            align-items: flex-start; background: #FFFFFF !important; border: 1px solid #E5E7EB !important;
            border-radius: 10px !important; padding: 12px 14px !important; height: auto !important;
            box-shadow: none !important; white-space: normal !important;
        }
        .st-key-sugg_grid .stButton > button:hover { border-color: #2563EB !important; background: #F5F8FF !important; }
        .st-key-sugg_grid .stButton > button p { color: #111827 !important; font-size: 13.5px !important; margin: 0 !important; }
        .sugg-label {
            font-size: 11.5px; font-weight: 600; color: #2563EB; text-transform: uppercase;
            letter-spacing: 0.03em; margin-bottom: 3px; display: block;
        }

        /* ================= CHAT MESSAGES ================= */
        .msg-row { display: flex; margin-bottom: 16px; }
        .msg-row.user { justify-content: flex-end; }
        .msg-row.assistant { justify-content: flex-start; align-items: flex-start; gap: 8px; }

        .msg-bubble { max-width: 74%; padding: 11px 15px; border-radius: 12px; font-size: 14.5px; line-height: 1.6; }
        .msg-bubble.user { background: #2563EB; color: #FFFFFF !important; border-bottom-right-radius: 3px; }
        .msg-bubble.user * { color: #FFFFFF !important; }
        .msg-bubble.assistant {
            background: #FFFFFF; border: 1px solid #E5E7EB; color: #111827;
            border-bottom-left-radius: 3px;
        }
        .msg-bubble.assistant * { color: #111827 !important; }

        .assistant-avatar {
            width: 26px; height: 26px; border-radius: 50%; background: #2563EB; color: #FFFFFF;
            font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; margin-top: 2px;
        }

        /* ================= SOURCES / SECURITY / REDACTION ================= */
        div[data-testid="stExpander"] { border: 1px solid #E5E7EB !important; border-radius: 10px !important; background: #FFFFFF; }
        div[data-testid="stExpander"] summary { color: #374151 !important; font-size: 13px !important; font-weight: 500 !important; }
        .source-row {
            border: 1px solid #E5E7EB; border-radius: 8px; padding: 8px 10px; margin-bottom: 6px;
            font-size: 13px; color: #111827; background: #F9FAFB;
        }
        .source-row .doc-name { font-weight: 600; color: #111827; }
        .source-row .doc-desc { color: #6B7280; font-size: 12px; margin-top: 1px; }

        .security-card {
            background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px;
            padding: 12px 14px; margin-top: 8px; font-size: 13.5px; color: #7F1D1D;
        }
        .security-card .title { font-weight: 700; margin-bottom: 3px; color: #991B1B; }

        .redaction-card {
            background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px;
            padding: 10px 14px; margin-top: 8px; font-size: 13px; color: #1E40AF;
        }

        /* ================= CHAT INPUT ================= */
        div[data-testid="stChatInput"] {
            border: 1px solid #E5E7EB !important; border-radius: 10px !important;
            box-shadow: 0 1px 2px rgba(16,24,40,0.04) !important; background: #FFFFFF !important;
        }
        div[data-testid="stChatInput"] textarea { color: #111827 !important; }

        @media (max-width: 640px) {
            .msg-bubble { max-width: 88%; }
            .chat-header { flex-direction: column; align-items: flex-start; }
            .header-user-chip { text-align: left; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.conversations = {}
        st.session_state.active_conversation_id = None


def new_conversation() -> str:
    conv_id = f"conv_{len(st.session_state.conversations)}_{datetime.now().timestamp()}"
    st.session_state.conversations[conv_id] = {"title": "New conversation", "messages": []}
    st.session_state.active_conversation_id = conv_id
    return conv_id


def get_active_conversation() -> dict:
    if st.session_state.active_conversation_id is None:
        new_conversation()
    return st.session_state.conversations[st.session_state.active_conversation_id]


def greeting_for_now() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


# ---------------------------------------------------------------------------
# Login screen
# ---------------------------------------------------------------------------
def render_login():
    inject_css()
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown(
            '<div class="login-wrap">'
            '<div class="login-logo">F</div>'
            '<p class="login-title">FinSolve Internal Assistant</p>'
            '<p class="login-subtitle">Secure company knowledge assistant</p>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-card-title">Sign in to your account</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. Sam")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            # UNCHANGED: same authenticate() call as every prior phase.
            role = authenticate(username, password)
            if role is None:
                st.error("Invalid username or password. Please try again.")
            else:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                new_conversation()
                st.rerun()

        with st.expander("Demo accounts"):
            st.markdown(
                "- `Tony` / `password123` — engineering\n"
                "- `Sam` / `financepass` — finance\n"
                "- `Bruce` / `securepass` — marketing\n"
                "- `Natasha` / `hrpass123` — hr\n"
                "- `Nick` / `execpass123` — executive"
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="login-tagline">Secure • Private • Role-based</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="brand-row"><div class="brand-mark">F</div>'
            '<div class="brand-name">FinSolve</div></div>'
            '<div class="brand-sub">Internal Assistant</div>',
            unsafe_allow_html=True,
        )

        with st.container(key="new_chat_btn"):
            if st.button("+ New Chat", use_container_width=True):
                new_conversation()
                st.rerun()

        st.markdown('<div class="sidebar-section-title">Recent conversations</div>', unsafe_allow_html=True)
        if not st.session_state.conversations:
            st.caption("No conversations yet")
        for conv_id, conv in reversed(list(st.session_state.conversations.items())):
            label = conv["title"] or "New conversation"
            if st.button(label, key=f"conv_{conv_id}", use_container_width=True):
                st.session_state.active_conversation_id = conv_id
                st.rerun()

        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-name">{st.session_state.username}</div>'
            f'<div class="profile-role">{st.session_state.role}</div>'
            f'<div class="profile-status">Authenticated</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.container(key="logout_btn"):
            if st.button("Log out", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.role = None
                st.session_state.conversations = {}
                st.session_state.active_conversation_id = None
                st.rerun()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def render_header():
    st.markdown(
        '<div class="chat-header">'
        '<div class="chat-header-left">'
        "<h1>FinSolve Internal Assistant</h1>"
        '<div class="subtitle-row">'
        "<p>Secure internal knowledge assistant</p>"
        '<span class="secure-badge">Secure connection</span>'
        "</div></div>"
        f'<div class="header-user-chip">'
        f'<div class="name">{st.session_state.username}</div>'
        f'<div class="role">{st.session_state.role}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Guardrail / source rendering
# ---------------------------------------------------------------------------
def render_security_card():
    # Deliberately generic — never renders the raw block_reason (which can
    # contain a matched regex pattern). The underlying guardrail category/
    # logic is completely untouched; only this display text changed.
    st.markdown(
        '<div class="security-card">'
        '<div class="title">🛡 Security Protection</div>'
        "This request was blocked because it appears to contain an instruction "
        "designed to bypass the assistant's security controls.<br>Your request was not processed."
        "</div>",
        unsafe_allow_html=True,
    )


def render_redaction_notice():
    st.markdown(
        '<div class="redaction-card">Some information in this answer was redacted '
        "by our data protection safeguards.</div>",
        unsafe_allow_html=True,
    )


def render_sources(sources: list[str]):
    if not sources:
        return
    with st.expander(f"▼ Sources ({len(sources)})"):
        for source in sources:
            st.markdown(
                f'<div class="source-row"><span class="doc-name">📄 {source}</span></div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
def render_message(msg: dict):
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-row user"><div class="msg-bubble user">{msg["content"]}</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="msg-row assistant">', unsafe_allow_html=True)
    st.markdown('<div class="assistant-avatar">F</div>', unsafe_allow_html=True)
    bubble = st.container()
    st.markdown("</div>", unsafe_allow_html=True)
    with bubble:
        st.markdown('<div class="msg-bubble assistant">', unsafe_allow_html=True)
        st.markdown(msg["content"])
        st.markdown("</div>", unsafe_allow_html=True)

    meta = msg.get("meta")
    if meta:
        if meta.get("blocked"):
            render_security_card()
        elif meta.get("output_guardrail_category") == "pii_leak":
            render_redaction_notice()
        if meta.get("sources"):
            render_sources(meta["sources"])


# ---------------------------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------------------------
def render_welcome() -> str | None:
    st.markdown(
        f'<div class="welcome-greeting">'
        f"<h2>{greeting_for_now()}, {st.session_state.username}.</h2>"
        "<p>How can I help you today? I can answer questions about FinSolve's internal "
        "policies, benefits, engineering documentation, and other authorized company information.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    clicked_question = None
    with st.container(key="sugg_grid"):
        cols = st.columns(2)
        for i, (label, question) in enumerate(SUGGESTIONS):
            with cols[i % 2]:
                if st.button(f"{label}\n\n{question}", key=f"sugg_{i}", use_container_width=True):
                    clicked_question = question
    return clicked_question


# ---------------------------------------------------------------------------
# Shared question handler — the ONLY path into the pipeline, used by both
# the chat input and the suggestion cards. No second answering system.
# ---------------------------------------------------------------------------
def handle_question(question: str):
    conv = get_active_conversation()
    conv["messages"].append({"role": "user", "content": question, "meta": None})
    if conv["title"] == "New conversation":
        conv["title"] = question[:36] + ("…" if len(question) > 36 else "")

    with st.spinner("Thinking..."):
        # UNCHANGED: same ask() call as every prior phase — RBAC, retrieval,
        # Groq generation, and both guardrails run exactly as before.
        result = ask(question, role=st.session_state.role, user_id=st.session_state.username)

    conv["messages"].append({"role": "assistant", "content": result["answer"], "meta": result})


# ---------------------------------------------------------------------------
# Main chat screen
# ---------------------------------------------------------------------------
def render_chat():
    render_sidebar()
    render_header()

    conv = get_active_conversation()

    example_clicked = None
    if not conv["messages"]:
        example_clicked = render_welcome()

    for msg in conv["messages"]:
        render_message(msg)

    question = st.chat_input("Ask FinSolve anything...")

    final_question = question or example_clicked
    if final_question:
        handle_question(final_question)
        st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
init_session_state()

if not st.session_state.authenticated:
    render_login()
else:
    inject_css()
    render_chat()