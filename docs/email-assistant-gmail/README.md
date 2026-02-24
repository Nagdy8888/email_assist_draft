# Gmail Email Assistant Agent

This document describes the **Gmail-integrated, human-in-the-loop (HITL), memory-enabled** email assistant implemented in `src/email_assistant/email_assistant_hitl_memory_gmail.py`.

## Overview

The agent:

- **Triages** incoming emails (from Gmail or mock input) into **ignore**, **notify**, or **respond**.
- **Notifies** the user for important-but-no-reply-needed emails and can learn from user choices (respond vs ignore).
- **Responds** to emails by drafting replies, scheduling meetings, and asking clarifying questions—all with **human review** before sending.
- **Learns** from feedback via persistent **memory** (triage preferences, response style, calendar preferences).

It is built with **LangGraph** (state graph, interrupts, store) and uses the **Gmail API** (and optionally Google Calendar) for real email and calendar operations.

## Key Features

| Feature | Description |
|--------|-------------|
| **Triage** | LLM classifies each email as ignore / notify / respond using structured output (`RouterSchema`). |
| **Human-in-the-loop** | Tool calls (send email, schedule meeting, Question) are sent to an **Agent Inbox** via `interrupt()`; user can accept, edit, respond with feedback, or ignore. |
| **Memory** | Three namespaces: `triage_preferences`, `response_preferences`, `cal_preferences`. Updated from HITL feedback without overwriting entire profiles. |
| **Gmail** | Uses `send_email_tool`, `check_calendar_tool`, `schedule_meeting_tool`, and `mark_as_read`; input can be Gmail-style (`from`, `to`, `subject`, `body`, `id`) or mock/Studio format. |

## Document Index

| Document | Content |
|----------|--------|
| [README.md](README.md) (this file) | Overview and index. |
| [01-architecture.md](01-architecture.md) | Graph structure, state, nodes, edges, and high-level flow. |
| [02-triage-and-memory.md](02-triage-and-memory.md) | Triage router, triage interrupt handler, and memory (get/update). |
| [03-response-agent-and-tools.md](03-response-agent-and-tools.md) | Response agent subgraph, LLM node, interrupt handler, tools, and mark-as-read. |
| [04-prompts-and-schemas.md](04-prompts-and-schemas.md) | Prompts, `RouterSchema`, `State`, `UserPreferences`, and input formats. |

## Running the Agent

- The compiled graph is exposed as **`email_assistant`** in `email_assistant_hitl_memory_gmail.py`.
- Invocation requires a **checkpointer** and **store** (for memory). See the main repo README and transcript guides for run instructions (e.g. LangGraph Studio, or Python with `MemorySaver` and a store).
- Gmail operations require valid credentials (e.g. `GMAIL_TOKEN` or `.secrets/token.json`); see `tools/gmail/` and transcript guide **13-setting-up-google-apis.md** for setup.

## Dependencies

- **LangGraph** (StateGraph, interrupt, Command, BaseStore)
- **LangChain** (chat model, structured output, tool binding)
- **email_assistant** modules: `tools`, `prompts`, `schemas`, `utils` (e.g. `parse_gmail`, `format_gmail_markdown`, `format_for_display`)
- **Gmail tools**: `send_email_tool`, `check_calendar_tool`, `schedule_meeting_tool`, `mark_as_read`; optional `fetch_emails_tool` for ingestion
