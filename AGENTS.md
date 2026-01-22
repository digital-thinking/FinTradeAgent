# Agent Instructions

## Core Philosophy
*   **Simplicity**: Don't overengineer. Simple beats complex.
*   **Single Path**: One correct way to do things, no fallbacks or alternatives.
*   **Fail Fast**: Throw errors when preconditions aren't met.
*   **No Mocking**: Do not mock or make up data outside of tests.
*   **Separation of Concerns**: Each function should have a single responsibility.

## Development Guidelines
*   **Git**: Do not commit on your own. Only commit if explicitly prompted by the user.
*   **Debugging**: Use evidence-based debugging with minimal, targeted logging. Fix root causes, not symptoms.
*   **Testing**: Add unit tests if they are missing.

## Project Context
**Agentic Trade Assistant** is a Streamlit application for managing AI-powered stock portfolios.

### Tech Stack
*   **Python 3.12+** (Poetry)
*   **Streamlit** (UI)
*   **OpenAI/Anthropic** (LLM APIs)
*   **yfinance** (Data)
*   **pandas/plotly** (Analysis/Charts)

### Key Directories
*   `src/fin_trade/app.py`: Main entry point.
*   `src/fin_trade/models/`: Data structures.
*   `src/fin_trade/services/`: Core logic (Portfolio, Agent, Stock Data).
*   `src/fin_trade/pages/`: UI Views.
*   `data/`: Configuration and state storage.

## Configuration & Environment
*   **Windows Environment**: Use forward slashes in Python paths.
*   **Secrets**: API keys are in `.env`.
*   **Portfolios**: Defined in `data/portfolios/*.yaml`.
*   **Logs**: LLM interactions logged to `data/logs/`.

## Common Workflows
*   **New Strategy**: Add YAML to `data/portfolios/`.
*   **Agent Logic**: Modify `src/fin_trade/services/agent.py`.
*   **Run App**: `poetry run streamlit run src/fin_trade/app.py`.

## Task Management
*   Refer to `tasks.md` for current work packages.
*   Respect package boundaries to enable parallel work.
