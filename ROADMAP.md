# Product Roadmap

This document outlines the future development direction for the Agentic Trade Assistant.

---

## 🚀 Core Functionality
*Focus: Stability, automation, and core trading capabilities.*

- **Scheduled Execution**: Implement a robust background job runner (e.g., APScheduler) to execute agent strategies automatically at user-defined intervals, removing the need to have the UI open.

---

## 🧠 Agent Intelligence
*Focus: Enhancing the sophistication and adaptability of trading agents.*

- **Self-Reflective Learning**: Agents will analyze their past performance, including the reasoning behind their decisions, to identify biases and refine their strategies over time.

---

## 📊 Data & Integrations
*Focus: Broadening the data sources to give agents a more comprehensive market view.*

- **Macro-Economic Data**: Integrate key economic indicators (e.g., CPI, GDP, unemployment rates, Fed interest rate decisions) into the agent's context.
- **Alternative Data Sources**:
    - **SEC Filings**: Real-time alerts and summaries for key filings (8-K, 10-Q, 10-K).
    - **Earnings Calendar**: Integrate upcoming earnings dates and subsequent results.
    - **Insider Trading Data**: Provide agents with data on insider buy/sell activity.

---

## ✨ User Experience & Interface
*Focus: Making the application more interactive, intuitive, and insightful.*

- **Interactive "What-If" Scenarios**: A sandbox mode where users can test agent reactions to hypothetical market events (e.g., "What would the agent do if the Fed raises rates by 50 basis points?").
- **LLM Reasoning Visualization**: Move beyond simple text logs to a more graphical representation of the agent's decision-making process, such as a decision tree or a mind map.
- **Enhanced Performance Analytics**: Detailed analytics on portfolio and agent performance, including attribution analysis to show what decisions led to specific outcomes.
