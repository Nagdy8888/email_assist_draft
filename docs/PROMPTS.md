# Prompts

Where prompts live and what they do.

## Phase 2

- **`prompts.SIMPLE_AGENT_SYSTEM_PROMPT`** — System prompt for the simple Q&A agent (one node, no tools). Used in `simple_agent._chat_node` so the LLM answers the user clearly and concisely.

Triage and response-agent prompts are added in later phases (`prompts.py` and `tools/gmail/prompt_templates.py`).
