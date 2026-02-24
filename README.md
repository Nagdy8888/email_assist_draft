# Email Assistant

LangGraph-based email assistant with triage, human-in-the-loop, memory, and Gmail integration.

## How to run

1. **Create virtual environment and install dependencies** (using [uv](https://docs.astral.sh/uv/)):

   ```bash
   uv venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Unix
   uv sync
   ```

2. Copy `.env.example` to `.env` and set your API keys and configuration.

3. Run the simple agent (Phase 2: user message → LLM response):

   ```bash
   python scripts/run_agent.py
   ```
   Set `OPENAI_API_KEY` in `.env`. Optionally set `RUN_MESSAGE` and `THREAD_ID`.

4. **Optional — LangGraph Studio:** Run the agent in the browser with a local dev server:
   ```bash
   uv sync --extra dev
   uv run langgraph dev
   ```
   Use `uv run` so the dev server runs with the project venv (required for the `email_assistant` package). Then open the Studio URL shown in the terminal. See `docs/RUNNING_AND_TESTING.md` for details.

See `docs/` for architecture, configuration, and running/testing details (filled in as the project is implemented).
