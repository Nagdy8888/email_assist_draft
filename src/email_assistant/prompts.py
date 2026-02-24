"""
Triage, agent, and memory-update prompts; default_* constants.

Use cases: centralize system prompts for triage router, response agent, and
memory-update LLM; keep prompt text out of node code.
"""

# Phase 2: system prompt for the simple Q&A agent (no tools, no triage).
SIMPLE_AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's questions clearly and concisely."
)
