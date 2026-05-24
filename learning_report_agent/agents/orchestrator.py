"""Orchestrator Agent — routes intent, manages agent turns, composes responses."""
import json
import uuid
from datetime import datetime

from agents.llm_client import chat
from agents.tools_registry import ALL_TOOLS
from agents.tool_executor import execute_tool_call
from memory.agent_memory import save_episode, recall_similar_episodes, search_org_knowledge

SYSTEM_PROMPT = """You are the Learning Report Agent — an intelligent assistant for learning & development analytics.

You have access to tools that query:
- LMS data: course completions, enrollments, compliance status, overdue learners
- HR/workforce data: employee profiles, org hierarchy, skill assessments, skill gaps
- Power BI datasets: KPIs, trends, reports
- Power Automate: create and trigger workflow automations

Your responsibilities:
1. Understand the user's intent (report request, data query, automation, insight)
2. Call the right tools to gather data
3. Synthesise clear, actionable insights with specific numbers
4. For report requests: call create_report and present the results
5. For automation requests: call create_flow with detailed action steps
6. Always cite specific data points (e.g., "Engineering has 82% compliance rate")
7. Proactively flag risks (e.g., overdue compliance training)

Tone: professional, data-driven, concise. Use bullet points for lists. Be specific."""


def run(user_message: str, session_id: str | None = None, conversation_history: list[dict] | None = None) -> dict:
    """
    Run one turn of the orchestrator.
    Returns: {response, tool_calls_made, session_id, intent}
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Recall similar past queries for context
    similar = recall_similar_episodes(user_message, n_results=3)
    similar_ctx = ""
    if similar:
        similar_ctx = "\n\nRelevant past queries:\n" + "\n".join(
            f"- {s['document'][:120]}" for s in similar[:2]
        )

    # Build message list
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT + similar_ctx}]
    if conversation_history:
        messages.extend(conversation_history[-10:])  # last 5 turns
    messages.append({"role": "user", "content": user_message})

    tool_calls_made = []
    max_turns = 6  # prevent infinite tool loops

    for _ in range(max_turns):
        response = chat(messages, tools=ALL_TOOLS)

        if not response.get("tool_calls"):
            # Final answer
            final_content = response.get("content", "")
            _save_memory(session_id, user_message, final_content, tool_calls_made)
            return {
                "response": final_content,
                "tool_calls_made": tool_calls_made,
                "session_id": session_id,
                "intent": _infer_intent(user_message),
            }

        # Execute tool calls
        messages.append({"role": "assistant", "content": response.get("content"), "tool_calls": response["tool_calls"]})
        for tc in response["tool_calls"]:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"]["arguments"]
            result = execute_tool_call(fn_name, fn_args)
            tool_calls_made.append({"tool": fn_name, "args": fn_args, "result_preview": result[:200]})
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # Fallback if max turns hit
    final = chat(messages)
    return {
        "response": final.get("content", "I gathered the data but hit a processing limit. Please try a more specific question."),
        "tool_calls_made": tool_calls_made,
        "session_id": session_id,
        "intent": _infer_intent(user_message),
    }


def _infer_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["report", "dashboard", "chart", "visual"]):
        return "report_request"
    if any(w in msg for w in ["flow", "automate", "remind", "schedule", "send"]):
        return "automation_request"
    if any(w in msg for w in ["compliance", "overdue", "required"]):
        return "compliance_query"
    if any(w in msg for w in ["skill", "gap", "training need"]):
        return "skill_gap_query"
    if any(w in msg for w in ["who", "employee", "team", "staff"]):
        return "people_query"
    return "general_query"


def _save_memory(session_id, query, response, tool_calls):
    try:
        entities = {
            "tools_used": [tc["tool"] for tc in tool_calls],
        }
        summary = response[:300] if response else ""
        save_episode(session_id, query, summary, _infer_intent(query), entities)
    except Exception:
        pass
