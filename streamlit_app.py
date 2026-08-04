"""
The user-facing app. Ties together everything built so far:

    Streamlit (this file)
        -> demo auth (app.services.auth.demo_users) -> role
        -> app.services.rag.pipeline.ask(question, role)
            -> input guardrail -> RBAC -> retrieval -> LLM -> output guardrail

DEMO AUTH ONLY — see demo_users.py's docstring. In production this
login form is replaced entirely by an Azure AD / Entra ID OAuth2 redirect
(Phase 14): the user never types a password into this app at all, and
their role would come from their actual company directory group
membership rather than a hardcoded dict.
"""

import streamlit as st

from app.services.auth.demo_users import authenticate
from app.services.rag.pipeline import ask

st.set_page_config(page_title="FinSolve Internal Assistant", page_icon="💬", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.messages = []  # [{"role": "user"/"assistant", "content": str, "meta": dict|None}]


def render_login():
    st.title("FinSolve Internal Assistant")
    st.caption("Demo login — this is a portfolio project, not a real authentication system.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        role = authenticate(username, password)
        if role is None:
            st.error("Invalid username or password.")
        else:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.role = role
            st.rerun()

    with st.expander("Demo accounts (for reviewers)"):
        st.markdown(
            "- `Tony` / `password123` — engineering\n"
            "- `Sam` / `financepass` — finance\n"
            "- `Bruce` / `securepass` — marketing\n"
            "- `Natasha` / `hrpass123` — hr\n"
            "- `Nick` / `execpass123` — executive"
        )


def render_chat():
    with st.sidebar:
        st.markdown(f"**Logged in as:** {st.session_state.username}")
        st.markdown(f"**Role:** `{st.session_state.role}`")
        if st.button("Log out"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.messages = []
            st.rerun()

    st.title("FinSolve Internal Assistant")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            meta = msg.get("meta")
            if meta:
                if meta.get("blocked"):
                    st.warning(f"Request blocked: {meta['block_reason']}")
                elif meta.get("output_guardrail_category") == "pii_leak":
                    st.info("Some information in this answer was redacted by the output guardrail.")
                if meta.get("sources"):
                    with st.expander("Sources"):
                        for source in meta["sources"]:
                            st.markdown(f"- `{source}`")

    question = st.chat_input("Ask a question about FinSolve...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question, "meta": None})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = ask(question, role=st.session_state.role)

            st.markdown(result["answer"])

            if result.get("blocked"):
                st.warning(f"Request blocked: {result['block_reason']}")
            elif result.get("output_guardrail_category") == "pii_leak":
                st.info("Some information in this answer was redacted by the output guardrail.")

            if result.get("sources"):
                with st.expander("Sources"):
                    for source in result["sources"]:
                        st.markdown(f"- `{source}`")

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "meta": result,
        })


if not st.session_state.authenticated:
    render_login()
else:
    render_chat()