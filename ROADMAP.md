# Product Roadmap

This document outlines the future development direction for the Agentic Trade Assistant. Features are prioritized but not bound to specific timelines.

## 🔴 High Priority
*Focus: Core stability, reliability, and essential trading capabilities.*

- **Backtesting Framework**: Ability to run agent strategies against historical data to validate logic before live deployment.
- **Scheduled Execution**: Background job runner (e.g., Celery/APScheduler) to run agents automatically at defined intervals without keeping the UI open.
- **Stop-Loss & Take-Profit**: Agents must recommend exit criteria for every position they open.

## 🟡 Medium Priority
*Focus: Enhanced intelligence, data richness, and user experience.*

- **Data Source Expansion**:
    - Earnings Calendar integration.
    - SEC Filing alerts (8-K, 10-Q).
    - Social Sentiment aggregation (Reddit/Twitter).
- **Performance Attribution**: Detailed breakdown of *why* a portfolio is up or down (e.g., "Tech sector exposure", "Specific stock selection").
