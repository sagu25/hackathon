"""Chat Agent page — conversational interface to the multi-agent system."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import uuid

st.set_page_config(page_title="Chat Agent", page_icon="💬", layout="wide")
st.title("💬 Chat Agent")
st.caption("Ask questions about learning data in natural language")

# Session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []  # conversation history for agent

# Sidebar: suggested prompts
with st.sidebar:
    st.subheader("Suggested Queries")
    suggestions = [
        "What is the compliance completion rate for Engineering?",
        "Who are the top 10 overdue learners in Sales?",
        "Show me the skill gaps for the Finance department",
        "Generate a weekly learning KPI report for all departments",
        "Create a Power Automate flow to send compliance reminders every Monday",
        "Which department has the highest training hours per employee?",
        "What are the top 5 courses by enrollment?",
        "Give me a skill gap analysis for HR department",
    ]
    for s in suggestions:
        if st.button(s, key=f"sug_{s[:20]}", use_container_width=True):
            st.session_state.pending_message = s

    st.divider()
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools_used"):
            with st.expander(f"Tools used: {', '.join(msg['tools_used'])}", expanded=False):
                for tc in msg.get("tool_details", []):
                    st.code(f"{tc['tool']}({tc['args'][:100]})", language="python")

# Handle pending message from sidebar buttons
pending = st.session_state.pop("pending_message", None)

# Chat input
user_input = st.chat_input("Ask about learning data...") or pending
if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                from agents.orchestrator import run
                result = run(
                    user_message=user_input,
                    session_id=st.session_state.session_id,
                    conversation_history=st.session_state.history,
                )
                response_text = result["response"]
                tool_calls = result.get("tool_calls_made", [])

                st.markdown(response_text)

                if tool_calls:
                    tools_used = [tc["tool"] for tc in tool_calls]
                    with st.expander(f"Tools used: {', '.join(tools_used)}", expanded=False):
                        for tc in tool_calls:
                            st.code(f"{tc['tool']}({str(tc['args'])[:150]})", language="python")

                # Update conversation history for multi-turn
                st.session_state.history.append({"role": "user", "content": user_input})
                st.session_state.history.append({"role": "assistant", "content": response_text})

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "tools_used": [tc["tool"] for tc in tool_calls],
                    "tool_details": tool_calls,
                })
            except Exception as exc:
                error_msg = f"Error: {exc}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
