# Architecture

Flow, graph, state, and data flow.

## Phase 2: Simple agent (current)

- **Graph:** Single path: `START → chat → END`. One node calls ChatOpenAI with `state["messages"]` and appends the assistant reply.
- **State:** `MessagesState` — a single key `messages` with the `add_messages` reducer (append-only conversation).
- **Checkpointer:** `MemorySaver` (in-memory) so that `config={"configurable": {"thread_id": "..."}}` gives multi-turn: each invoke with the same `thread_id` sees prior messages.
- **Entry:** `simple_agent.build_simple_graph()` builds and compiles the graph; `run_agent.py` invokes it with a user message and prints the last message.

No DB, no store, no email. Full graph (input_router, triage, response_agent, etc.) is added in later phases.
