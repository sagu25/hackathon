"""Agent memory: episodic, semantic, and procedural stores backed by SQLite + ChromaDB."""
import json
import sqlite3
from datetime import datetime
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from config import DB_PATH, CHROMA_DIR, settings


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# ── ChromaDB Vector Store ────────────────────────────────────────────────────

def _get_chroma_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_embedding_fn():
    if settings.is_azure_configured:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

        class AzureEmbedFn(embedding_functions.EmbeddingFunction):
            def __call__(self, input: list[str]) -> list[list[float]]:
                resp = client.embeddings.create(model=settings.azure_openai_embedding_deployment, input=input)
                return [e.embedding for e in resp.data]

        return AzureEmbedFn()
    # Fallback: lightweight local embedding
    return embedding_functions.DefaultEmbeddingFunction()


# ── Episodic Memory ──────────────────────────────────────────────────────────

def save_episode(session_id: str, query: str, response_summary: str, intent: str, entities: dict) -> int:
    """Save a query/response episode to episodic memory."""
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO agent_memory_episodic (session_id, query, response_summary, intent, entities) VALUES (?,?,?,?,?)",
        (session_id, query, response_summary, intent, json.dumps(entities))
    )
    conn.commit()
    episode_id = cur.lastrowid
    conn.close()

    # Also index in vector store for semantic recall
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection("episodic_memory", embedding_function=_get_embedding_fn())
        col.add(
            documents=[f"{query} {response_summary}"],
            metadatas=[{"intent": intent, "session_id": session_id, "episode_id": str(episode_id)}],
            ids=[f"ep_{episode_id}"],
        )
    except Exception:
        pass  # Vector indexing is best-effort
    return episode_id


def recall_similar_episodes(query_text: str, n_results: int = 5) -> list[dict]:
    """Find semantically similar past queries."""
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection("episodic_memory", embedding_function=_get_embedding_fn())
        if col.count() == 0:
            return []
        results = col.query(query_texts=[query_text], n_results=min(n_results, col.count()))
        return [
            {"document": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
    except Exception:
        return []


def get_recent_episodes(session_id: str | None = None, limit: int = 10) -> list[dict]:
    conn = _conn()
    if session_id:
        rows = conn.execute(
            "SELECT * FROM agent_memory_episodic WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM agent_memory_episodic ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Semantic Memory (org knowledge) ─────────────────────────────────────────

def index_org_knowledge():
    """Index key org facts into vector store for NL grounding."""
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection("org_knowledge", embedding_function=_get_embedding_fn())
        if col.count() > 0:
            return  # Already indexed

        conn = _conn()
        depts = conn.execute("SELECT * FROM gold_dept_learning_kpis").fetchall()
        docs, metas, ids = [], [], []
        for d in depts:
            d = dict(d)
            text = (
                f"{d['department']} department has {d['headcount']} employees. "
                f"Completion rate: {d['completion_rate']}%. Required compliance: {d['required_completion_rate']}%. "
                f"Avg training hours: {d['avg_hours_per_employee']}h. Budget utilisation: {d['budget_utilization']}%."
            )
            docs.append(text)
            metas.append({"type": "dept_kpi", "department": d["department"]})
            ids.append(f"dept_{d['department'].lower().replace(' ', '_')}")
        conn.close()
        if docs:
            col.add(documents=docs, metadatas=metas, ids=ids)
    except Exception:
        pass


def search_org_knowledge(query_text: str, n_results: int = 5) -> list[dict]:
    """Semantic search over indexed org knowledge."""
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection("org_knowledge", embedding_function=_get_embedding_fn())
        if col.count() == 0:
            return []
        results = col.query(query_texts=[query_text], n_results=min(n_results, col.count()))
        return [{"text": doc, "metadata": meta} for doc, meta in
                zip(results["documents"][0], results["metadatas"][0])]
    except Exception:
        return []


# ── Procedural Memory (recipes) ─────────────────────────────────────────────

DEFAULT_RECIPES = [
    {
        "recipe_name": "compliance_report",
        "description": "Generate compliance training status report",
        "steps": ["get_compliance_summary", "identify_overdue_learners", "generate_narrative", "format_report"],
    },
    {
        "recipe_name": "skill_gap_analysis",
        "description": "Analyse skill gaps across a department",
        "steps": ["get_skill_gap_report", "compare_with_role_requirements", "generate_recommendations"],
    },
    {
        "recipe_name": "weekly_briefing",
        "description": "Generate weekly learning briefing for leaders",
        "steps": ["get_dept_kpis", "detect_anomalies", "generate_narrative", "format_briefing"],
    },
]


def ensure_default_recipes():
    conn = _conn()
    for r in DEFAULT_RECIPES:
        conn.execute(
            "INSERT OR IGNORE INTO agent_memory_procedural (recipe_name, description, steps) VALUES (?,?,?)",
            (r["recipe_name"], r["description"], json.dumps(r["steps"]))
        )
    conn.commit()
    conn.close()


def get_recipe(recipe_name: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM agent_memory_procedural WHERE recipe_name=?", (recipe_name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_recipes() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT recipe_name, description, used_count FROM agent_memory_procedural").fetchall()
    conn.close()
    return [dict(r) for r in rows]
