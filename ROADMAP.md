# Product Roadmap

This document outlines the future development direction for the Agentic Trade Assistant. Features are prioritized but not bound to specific timelines.

## 🔴 High Priority
*Focus: Core stability, reliability, and essential trading capabilities.*

- **Broker Integration (Paper Trading)**: Connect to Alpaca or Interactive Brokers for paper trading execution to move beyond manual entry.
- **Backtesting Framework**: Ability to run agent strategies against historical data to validate logic before live deployment.
- **Scheduled Execution**: Background job runner (e.g., Celery/APScheduler) to run agents automatically at defined intervals without keeping the UI open.
- **Confidence Scoring**: Agents should provide a confidence score (0-100%) for each trade recommendation to aid human decision-making.
- **Stop-Loss & Take-Profit**: Agents must recommend exit criteria for every position they open.

## 🟡 Medium Priority
*Focus: Enhanced intelligence, data richness, and user experience.*

- **Multi-Agent Debates (Enhanced)**: Formalize the "Bull vs Bear" debate structure with distinct personas and a moderator for all strategy types.
- **Data Source Expansion**:
    - Earnings Calendar integration.
    - SEC Filing alerts (8-K, 10-Q).
    - Social Sentiment aggregation (Reddit/Twitter).
- **Performance Attribution**: Detailed breakdown of *why* a portfolio is up or down (e.g., "Tech sector exposure", "Specific stock selection").
- **Position Sizing Logic**: Move beyond fixed quantities to dynamic sizing based on portfolio volatility and conviction.
- **Chain-of-Thought Visualization**: UI to step through the agent's reasoning process in real-time (Research -> Hypothesis -> Validation -> Decision).

## 🟢 Low Priority
*Focus: Platform scalability and community features.*

- **Strategy Marketplace**: Mechanism to export, share, and import agent strategy configurations.
- **Multi-User Support**: User authentication and isolated portfolio states for multiple traders.
- **API Endpoint**: REST API to trigger agent runs and retrieve recommendations programmatically.
- **A/B Testing**: Framework to run two variations of a prompt against the same market conditions to compare performance.
- **Options Trading Support**: Expand data models and execution logic to support options contracts.
