# Running and testing

How to run and test the agent.

## Phase 2: Simple agent

1. **Environment**
   - Copy `.env.example` to `.env`.
   - Set `OPENAI_API_KEY` (required). Optionally set `OPENAI_MODEL` (default `gpt-4o`).
   - For LangSmith tracing: set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and optionally `LANGCHAIN_PROJECT`.

2. **Run**
   - From repo root with venv activated:
     ```bash
     uv venv
     .venv\Scripts\activate   # Windows
     uv sync
     python scripts/run_agent.py
     ```
   - Default message is "Hello, how are you?" or set `RUN_MESSAGE` in `.env` to ask something else.
   - Optional: set `THREAD_ID` in `.env` to fix the conversation thread (default `default-thread`).

3. **Multi-turn**
   - Use the same `thread_id` in `config` when invoking the graph (e.g. same `THREAD_ID`). The checkpointer keeps conversation history for that thread; a second run with the same thread_id would see the previous messages. The current script runs one turn and exits; multi-turn is supported by calling `graph.invoke(...)` repeatedly with the same `config`.

4. **No DB / store / email**
   - Phase 2 uses only LangGraph, OpenAI, and optional LangSmith. No Supabase or Postgres.

## LangGraph Studio (local)

Run the agent in [LangGraph Studio](https://smith.langchain.com/studio) with a local dev server:

1. **Install project and Studio CLI** from the project root:
   ```bash
   uv sync --extra dev
   ```
   This installs the project (so `email_assistant` is importable) and `langgraph-cli[inmem]`.

2. **Start the dev server using the project venv** (required so `email_assistant` is found):
   ```bash
   uv run langgraph dev
   ```
   Or activate the venv first, then run:
   ```bash
   .venv\Scripts\activate   # Windows
   langgraph dev
   ```
   If you run `langgraph dev` without the project venv (e.g. global Python), you'll get `ModuleNotFoundError: No module named 'email_assistant'`.
   - API: `http://127.0.0.1:2024`
   - Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
   - API docs: `http://127.0.0.1:2024/docs`

3. **Use Studio:** Open the Studio URL in your browser (it may open automatically). Select the **simple_agent** graph, create a thread, and send messages. Input format: `{"messages": [{"role": "human", "content": "Hello"}]}`. The platform handles persistence (threads/checkpoints) when using Studio.

4. **Config:** `langgraph.json` points to `./src/email_assistant/simple_agent.py:graph`. The graph exposed to Studio is compiled without a checkpointer; the script `run_agent.py` still uses `MemorySaver()` for CLI multi-turn.
