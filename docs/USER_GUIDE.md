# FinTradeAgent User Guide

## Welcome to FinTradeAgent

FinTradeAgent is an AI-powered trading intelligence platform that helps you create and manage automated trading strategies using Large Language Models (LLMs). This guide will walk you through all the features and workflows to get the most out of the platform.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Portfolio Management](#portfolio-management)
4. [Creating Trading Agents](#creating-trading-agents)
5. [Agent Execution Workflows](#agent-execution-workflows)
6. [Trade Management](#trade-management)
7. [Performance Analysis](#performance-analysis)
8. [System Administration](#system-administration)
9. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### First Login

1. **Access the Application**: Navigate to `http://localhost:3000` (development) or your production URL
2. **Dashboard Welcome**: You'll see the main dashboard with an overview of your trading performance
3. **Quick Tour**: Take a moment to explore the main navigation:
   - **Dashboard**: Overview of all portfolios and performance
   - **Portfolios**: Create and manage trading strategies
   - **Trades**: Review and execute trade recommendations
   - **System**: Monitor system health and settings

### Initial Setup

Before creating your first trading agent, ensure you have:

1. **API Keys Configured**: 
   - OpenAI API key for GPT models
   - Anthropic API key for Claude models
   - Brave Search API key for web research

2. **Market Data Access**: 
   - Yahoo Finance (free, built-in)
   - SEC EDGAR access for filings

3. **Starting Capital**: 
   - Decide on initial amount for each strategy
   - Recommended: Start with $10,000 virtual capital per portfolio

## Dashboard Overview

### Main Dashboard Components

#### Portfolio Summary Cards
At the top of the dashboard, you'll see cards showing:

- **Total AUM (Assets Under Management)**: Combined value of all portfolios
- **Total Return**: Absolute dollar return across all strategies
- **Total Return %**: Percentage return on initial capital
- **Best Performer**: Top-performing portfolio by percentage return
- **Active Portfolios**: Number of currently active trading strategies

#### Performance Chart
The main chart displays:
- **Portfolio Value Over Time**: Combined value of all portfolios
- **Benchmark Comparison**: Performance vs S&P 500 (SPY)
- **Interactive Controls**: Zoom, pan, and time period selection
- **Return Metrics**: Daily, weekly, monthly, and YTD returns

#### Recent Activity Feed
Stay updated with:
- **Latest Executions**: Recent agent runs and their results
- **Trade Notifications**: New recommendations and executed trades
- **System Events**: Important system notifications
- **Performance Milestones**: Notable gains, losses, or achievements

#### Top Holdings
View your largest positions across all portfolios:
- **Symbol**: Stock ticker
- **Total Shares**: Combined shares across portfolios
- **Total Value**: Current market value
- **Unrealized P&L**: Paper gains/losses
- **Weight**: Percentage of total portfolio

## Portfolio Management

### Creating a New Portfolio

#### Step 1: Navigate to Portfolio Creation
1. Click **"Portfolios"** in the main navigation
2. Click **"Create Portfolio"** button
3. The portfolio creation modal will open

#### Step 2: Basic Configuration
Fill in the essential details:

**Portfolio Name**: Choose a descriptive name
- Example: "Take-Private Arbitrage", "Earnings Momentum", "Tech Growth"
- Keep it short but memorable
- Avoid special characters

**Asset Class**: Select the type of assets to trade
- **Stocks**: US equities (most common)
- **Crypto**: Cryptocurrencies (BTC-USD, ETH-USD, etc.)
- **Mixed**: Both stocks and crypto

**Initial Amount**: Starting virtual capital
- Recommended range: $10,000 - $100,000
- This is virtual money for backtesting and strategy development
- Start smaller to test strategy effectiveness

#### Step 3: Strategy Configuration

**Strategy Prompt**: This is the heart of your trading agent. Write a detailed description of your trading strategy:

```
You are a [STRATEGY TYPE] specialist focused on [MARKET FOCUS].

RESEARCH FOCUS:
- [What data sources to examine]
- [Key metrics to analyze]
- [Market conditions to monitor]

BUY SIGNALS:
- [Specific conditions that trigger buy recommendations]
- [Technical indicators to monitor]
- [Fundamental criteria to evaluate]

SELL SIGNALS:
- [Conditions that trigger sell recommendations]
- [Exit criteria and profit-taking rules]
- [Risk management guidelines]

RISK MANAGEMENT:
- [Position sizing rules]
- [Stop-loss criteria]
- [Maximum exposure limits]

Always use current market data and explain your reasoning clearly.
```

**Example Strategy Prompts**:

*Merger Arbitrage Strategy*:
```
You are a merger arbitrage specialist focused on announced acquisition deals.

RESEARCH FOCUS:
- Announced M&A deals with defined terms and timelines
- Regulatory approval progress and potential hurdles
- Deal completion probability based on financing and conditions
- Spread analysis between current price and deal price

BUY SIGNALS:
- Deal announced with spread >10% and high completion probability
- Regulatory approval milestones achieved
- Strong management/board support statements
- Adequate financing confirmed

SELL SIGNALS:
- Spread compresses below 5% (limited upside)
- Regulatory challenges or delays emerge
- Deal terms renegotiated lower
- Take profit at 95% of deal price

RISK MANAGEMENT:
- Maximum 20% position size per deal
- Stop loss at 15% below entry price
- Monitor deal completion timeline closely
```

*Earnings Momentum Strategy*:
```
You are an earnings momentum specialist focused on post-earnings opportunities.

RESEARCH FOCUS:
- Companies reporting earnings in the next 30 days
- Historical earnings surprise patterns
- Guidance revisions and management commentary
- Analyst estimate revisions post-earnings

BUY SIGNALS:
- "Double beat" - EPS and revenue both exceed estimates
- Raised guidance with confident management tone
- Strong sector tailwinds and positive outlook
- Technical breakout post-earnings

SELL SIGNALS:
- Earnings miss or lowered guidance
- Momentum fading (3+ days of decline)
- Sector rotation or macro headwinds
- Take profit at 15-20% gains

RISK MANAGEMENT:
- Maximum 15% position size per stock
- Stop loss at 8% below entry price
- Diversify across sectors and market caps
```

#### Step 4: Execution Parameters

**Trades Per Run**: How many trades the agent can recommend per execution
- **Conservative**: 1-2 trades (focused approach)
- **Moderate**: 3-5 trades (balanced)
- **Aggressive**: 5+ trades (diversified)

**Run Frequency**: How often the agent executes
- **Daily**: Best for momentum strategies
- **Weekly**: Good for swing trading
- **Monthly**: Suitable for long-term strategies

**LLM Configuration**:
- **Provider**: Choose between OpenAI, Anthropic, or local models
- **Model**: Select specific model (GPT-4o, Claude-3-Opus, etc.)
- **Agent Mode**: 
  - **Simple**: Single agent analysis
  - **Debate**: Multiple agents debate before decisions
  - **LangGraph**: Structured multi-step workflow

#### Step 5: Risk Management (Optional)

**Position Limits**:
- **Max Position Size**: Maximum percentage of portfolio per stock (e.g., 20%)
- **Stop Loss Default**: Default stop-loss percentage (e.g., 10%)
- **Take Profit Default**: Default profit-taking level (e.g., 25%)

### Managing Existing Portfolios

#### Portfolio List View
The portfolio list shows all your trading strategies with key metrics:

- **Name**: Portfolio identifier
- **Total Value**: Current portfolio value
- **Return**: Absolute and percentage returns
- **Last Execution**: When the agent last ran
- **Status**: Active, paused, or error state
- **Actions**: Edit, execute, view details, delete

#### Portfolio Detail View
Click on any portfolio to access the detailed view:

**Overview Tab**:
- Current portfolio composition
- Recent performance chart
- Key statistics and metrics
- Holdings breakdown

**Execution Tab**:
- Manual agent execution
- Real-time execution progress
- User guidance input
- Execution history

**Trades Tab**:
- Pending recommendations
- Trade history
- Performance by trade
- Risk analysis

**Settings Tab**:
- Edit portfolio configuration
- Adjust risk parameters
- Update strategy prompt
- Scheduling options

## Creating Trading Agents

### Strategy Development Process

#### 1. Research Phase
Before writing your strategy prompt:
- **Study the Market**: Understand the sector or opportunity you're targeting
- **Analyze Historical Data**: Look at past performance of similar strategies
- **Define Clear Rules**: Establish specific, measurable criteria
- **Consider Risk Factors**: Identify what could go wrong

#### 2. Strategy Design Principles

**Specificity**: Be explicit about what the agent should look for
❌ Bad: "Look for good stocks to buy"
✅ Good: "Identify stocks with EPS growth >20% YoY and revenue growth >15% YoY"

**Measurable Criteria**: Use quantifiable metrics
❌ Bad: "Buy stocks with strong momentum"
✅ Good: "Buy stocks trading above 50-day MA with RSI between 50-70"

**Risk Management**: Always include downside protection
❌ Bad: No mention of when to sell or cut losses
✅ Good: "Stop loss at 10% below entry, take profit at 25% gain"

**Context Awareness**: Help the agent understand market conditions
❌ Bad: "Always buy on earnings beats"
✅ Good: "Buy earnings beats in bull markets, avoid in high volatility (VIX >25)"

#### 3. Common Strategy Types

**Momentum Strategies**:
- Focus on stocks with strong price trends
- Use technical indicators (RSI, MACD, moving averages)
- Quick entry and exit rules
- Good for volatile markets

**Value Strategies**:
- Look for undervalued securities
- Use fundamental metrics (P/E, P/B, DCF analysis)
- Longer holding periods
- Good for patient capital

**Event-Driven Strategies**:
- Focus on corporate events (earnings, M&A, spinoffs)
- Time-sensitive opportunities
- Require quick execution
- High research intensity

**Sector Rotation**:
- Move between different sectors based on economic cycles
- Monitor macroeconomic indicators
- Diversification benefits
- Medium-term holding periods

### Advanced Strategy Features

#### Multi-Agent Debate Mode
For complex strategies, use debate mode where multiple AI agents discuss before making decisions:

1. **Bull Agent**: Argues for buying opportunities
2. **Bear Agent**: Identifies risks and reasons to sell
3. **Neutral Agent**: Provides balanced perspective
4. **Moderator**: Makes final decision based on debate

This approach helps reduce bias and improves decision quality.

#### LangGraph Structured Workflows
For systematic approaches, use LangGraph mode with defined steps:

1. **Research Agent**: Gathers market data and news
2. **Analysis Agent**: Evaluates opportunities
3. **Risk Agent**: Assesses downside risks
4. **Decision Agent**: Makes final recommendations

## Agent Execution Workflows

### Manual Execution

#### Starting an Execution
1. Navigate to the portfolio detail page
2. Click the **"Execute Agent"** button
3. Optionally provide user guidance:
   - "Focus on tech stocks today"
   - "Avoid energy sector due to volatility"
   - "Look for defensive plays"

#### Real-Time Progress Monitoring
Watch the execution unfold in real-time:

**Phase 1: Data Collection (20-40% complete)**
- Fetching current portfolio state
- Gathering market data for holdings
- Collecting macro-economic indicators
- Retrieving news and analyst reports

**Phase 2: Market Research (40-70% complete)**
- Web search for relevant information
- SEC filing analysis
- Earnings data compilation
- Insider trading activity review

**Phase 3: AI Analysis (70-90% complete)**
- LLM processing of collected data
- Strategy application to current market
- Risk assessment and opportunity identification
- Recommendation generation

**Phase 4: Results Compilation (90-100% complete)**
- Formatting recommendations
- Calculating confidence scores
- Preparing reasoning explanations
- Finalizing execution report

#### Understanding Execution Results

Each execution provides:

**Summary**: Overall market assessment and key findings
**Recommendations**: Specific trade suggestions with:
- **Ticker**: Stock symbol
- **Action**: BUY or SELL
- **Quantity**: Number of shares
- **Target Price**: Recommended execution price
- **Stop Loss**: Risk management price
- **Take Profit**: Profit-taking target
- **Confidence**: AI confidence score (0-100%)
- **Reasoning**: Detailed explanation for the trade

**Market Analysis**: Contextual information about:
- Current market conditions
- Sector performance
- Volatility indicators
- Economic factors

### Automated Scheduling

#### Setting Up Automated Execution
1. Go to portfolio settings
2. Enable **"Automated Execution"**
3. Set execution frequency (daily, weekly, monthly)
4. Configure execution time (e.g., 9:30 AM EST for market open)

#### Monitoring Automated Executions
- Check execution logs regularly
- Review performance trends
- Adjust strategies based on results
- Disable automation if strategy underperforms

⚠️ **Important**: Always keep `auto_apply_trades: false` for safety. Review recommendations before execution.

## Trade Management

### Reviewing Recommendations

#### Trade Recommendation Cards
Each recommended trade displays:

**Basic Information**:
- **Ticker Symbol**: With company name
- **Action**: BUY or SELL with colored indicators
- **Quantity**: Number of shares recommended
- **Current Price**: Real-time market price

**Financial Details**:
- **Target Price**: AI's recommended execution price
- **Stop Loss**: Risk management exit price
- **Take Profit**: Profit-taking target
- **Total Cost**: Estimated transaction amount
- **Position Impact**: Effect on portfolio allocation

**AI Analysis**:
- **Confidence Score**: How confident the AI is (displayed as percentage)
- **Reasoning**: Detailed explanation of the trade logic
- **Research Data**: Supporting market data and news
- **Risk Factors**: Identified potential downsides

#### Trade Validation Process

Before executing any trade, consider:

1. **Verify Ticker Accuracy**: Ensure the symbol is correct (AI sometimes hallucinates tickers)
2. **Check Current Price**: Compare AI's target price with current market price
3. **Review Reasoning**: Does the logic make sense given current conditions?
4. **Assess Risk/Reward**: Is the potential upside worth the downside risk?
5. **Portfolio Impact**: How will this trade affect overall diversification?

### Executing Trades

#### Applying Recommended Trades
1. Click **"Apply Trade"** button on the recommendation card
2. Review the execution confirmation dialog:
   - Verify all trade details
   - Check current market price
   - Confirm available cash (for buys)
   - Review fees and total cost
3. Optionally adjust:
   - **Quantity**: Reduce shares if desired
   - **Price Limit**: Set maximum buy price or minimum sell price
   - **Notes**: Add personal notes about the decision
4. Click **"Confirm Execution"**

#### Trade Execution Results
After execution, you'll see:
- **Execution Status**: Success or failure
- **Actual Price**: Price at which trade was executed
- **Total Cost**: Including fees and commissions
- **Portfolio Update**: New cash balance and holdings
- **Performance Impact**: Effect on unrealized P&L

### Managing Active Positions

#### Holdings Overview
The holdings table shows all current positions:

**Position Details**:
- **Ticker**: Stock symbol with company name
- **Shares**: Number of shares owned
- **Avg Price**: Average cost basis per share
- **Current Price**: Real-time market price
- **Total Value**: Current market value
- **Unrealized P&L**: Paper gain/loss (dollar and percentage)
- **Weight**: Position size as percentage of portfolio

**Position Actions**:
- **Sell**: Create sell order for position
- **Add**: Buy more shares (increase position)
- **Set Alerts**: Price or percentage alerts
- **View Details**: Detailed position analysis

#### Stop Loss and Take Profit Management

**Setting Stop Losses**:
1. Click on a holding in your portfolio
2. Select **"Set Stop Loss"**
3. Choose:
   - **Percentage**: e.g., 10% below current price
   - **Absolute Price**: specific price level
   - **Trailing Stop**: follows price higher
4. Confirm the stop loss order

**Managing Take Profits**:
1. Select holding with unrealized gains
2. Click **"Take Profit"**
3. Options:
   - **Partial Sale**: Sell portion of position
   - **Full Sale**: Exit entire position
   - **Scale Out**: Gradual selling plan
4. Set target prices and quantities

### Trade History and Analysis

#### Trade History View
Access complete trading history:

**Filters**:
- **Date Range**: Custom time periods
- **Portfolio**: Specific strategy
- **Ticker**: Individual stocks
- **Action**: Buys vs sells
- **Status**: Executed, cancelled, pending

**Trade Records**:
- **Entry/Exit Details**: Prices, dates, quantities
- **Hold Period**: Days between buy and sell
- **Realized P&L**: Actual profit/loss
- **Fees**: Transaction costs
- **Reasoning**: Why the trade was made

#### Performance Analysis
Analyze trading performance:

**Win Rate Metrics**:
- **Overall Win Rate**: Percentage of profitable trades
- **Average Win**: Average gain on winning trades  
- **Average Loss**: Average loss on losing trades
- **Profit Factor**: Ratio of gross profits to gross losses

**Risk Metrics**:
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns
- **Volatility**: Standard deviation of returns
- **Beta**: Correlation with market movements

## Performance Analysis

### Portfolio Performance Dashboard

#### Key Performance Indicators (KPIs)

**Return Metrics**:
- **Total Return**: Absolute dollar gain/loss
- **Total Return %**: Percentage return on initial capital
- **Annualized Return**: Year-over-year performance projection
- **Time-Weighted Return**: Performance accounting for cash flows

**Risk Metrics**:
- **Volatility**: Standard deviation of daily returns
- **Max Drawdown**: Worst peak-to-trough decline
- **Sharpe Ratio**: Return per unit of risk
- **Beta**: Sensitivity to market movements

**Trading Metrics**:
- **Win Rate**: Percentage of profitable trades
- **Average Hold Period**: Days between buy and sell
- **Turnover Rate**: How frequently portfolio changes
- **Trading Frequency**: Trades per month

#### Performance Charts and Analysis

**Cumulative Return Chart**:
- Portfolio value over time
- Benchmark comparison (S&P 500)
- Drawdown periods highlighted
- Key events annotated

**Risk/Return Scatter Plot**:
- Compare multiple portfolios
- Risk (x-axis) vs Return (y-axis)
- Efficient frontier reference
- Sharpe ratio visualization

**Rolling Performance**:
- 30-day rolling returns
- Volatility trends
- Performance consistency
- Seasonal patterns

### Benchmarking and Comparison

#### Benchmark Comparison
Compare your portfolios against:

**Market Benchmarks**:
- **SPY**: S&P 500 ETF (broad market)
- **QQQ**: NASDAQ 100 ETF (tech-heavy)
- **IWM**: Russell 2000 ETF (small caps)
- **Custom**: Define your own benchmark

**Performance Attribution**:
- **Alpha**: Excess return vs benchmark
- **Beta**: Market sensitivity
- **Correlation**: Relationship to benchmark
- **Tracking Error**: Deviation from benchmark

#### Portfolio Comparison
Compare multiple strategies:

**Side-by-Side Metrics**:
- Return and risk statistics
- Trade frequency and win rates
- Sector allocations
- Performance over different time periods

**Relative Performance**:
- Which strategies outperform in different market conditions
- Correlation between strategies
- Diversification benefits
- Risk-adjusted performance ranking

### Performance Reporting

#### Custom Reports
Generate detailed performance reports:

**Report Types**:
- **Monthly Summary**: Key metrics and trades
- **Quarterly Review**: Detailed analysis and insights
- **Annual Report**: Comprehensive year-end review
- **Custom Period**: Any date range

**Export Options**:
- **PDF**: Professional formatted reports
- **CSV**: Data for external analysis
- **JSON**: Programmatic access to data
- **Email**: Automated report delivery

## System Administration

### User Settings and Preferences

#### Profile Configuration
Manage your account settings:

**Personal Information**:
- Username and display name
- Email address and notifications
- Time zone and regional settings
- Language preferences

**Trading Preferences**:
- Default position sizing
- Risk tolerance settings
- Notification preferences
- Execution confirmations

#### API Configuration
Configure external service connections:

**LLM Provider Settings**:
- **OpenAI**: API key and model preferences
- **Anthropic**: Claude access configuration
- **Local Models**: Ollama server settings

**Market Data Sources**:
- **Yahoo Finance**: Default free data source
- **Alpha Vantage**: Premium data option
- **Custom Sources**: API endpoint configuration

### System Monitoring

#### Health Dashboard
Monitor system performance:

**Service Status**:
- **API Server**: Response time and availability
- **Database**: Query performance and connections
- **Cache**: Hit rates and memory usage
- **LLM Providers**: API status and rate limits

**Performance Metrics**:
- **Response Times**: API endpoint performance
- **Throughput**: Requests per minute
- **Error Rates**: Failed request percentage
- **Resource Usage**: CPU, memory, and disk

#### Alert Configuration
Set up monitoring alerts:

**System Alerts**:
- High error rates
- Slow response times
- Service outages
- Resource exhaustion

**Trading Alerts**:
- Large gains or losses
- Failed executions
- Low confidence trades
- Risk limit breaches

### Backup and Data Management

#### Data Export
Export your data for backup or analysis:

**Portfolio Data**:
- Configuration files (YAML)
- Historical state data (JSON)
- Trade history (CSV)
- Performance metrics (JSON)

**System Data**:
- Execution logs
- Error logs
- Configuration backups
- Database snapshots

#### Data Import
Import existing trading data:

**Supported Formats**:
- CSV trade history
- JSON portfolio data
- YAML configuration files
- Custom data formats

**Import Process**:
1. Select data source and format
2. Map fields to system schema
3. Validate data integrity
4. Preview import results
5. Confirm and execute import

## Tips and Best Practices

### Strategy Development

#### Start Simple
- Begin with basic strategies before attempting complex multi-factor models
- Test with small position sizes initially
- Focus on one market or sector first
- Use clear, measurable criteria

#### Iterate and Improve
- Analyze failed trades to understand weaknesses
- Adjust strategy prompts based on results
- Keep detailed notes about market conditions
- Review and refine regularly

#### Risk Management
- Never risk more than you can afford to lose (even with virtual capital)
- Diversify across different strategies and sectors
- Use stop losses consistently
- Monitor correlation between strategies

### Execution Best Practices

#### Trade Validation
- Always verify ticker symbols before executing
- Check current market prices against AI recommendations
- Review reasoning for logical consistency
- Consider current market conditions and volatility

#### Position Management
- Start with smaller position sizes while learning
- Scale successful strategies gradually
- Rebalance portfolios periodically
- Monitor portfolio concentration risk

#### Performance Monitoring
- Review performance regularly but don't overtrade
- Focus on risk-adjusted returns, not just absolute returns
- Compare against relevant benchmarks
- Document lessons learned from both wins and losses

### Common Pitfalls to Avoid

#### Over-Optimization
- Don't constantly tweak strategies based on short-term results
- Avoid curve-fitting to historical data
- Allow sufficient time for strategy evaluation
- Focus on process over individual trade outcomes

#### Emotional Trading
- Stick to your systematic approach
- Don't panic during market volatility
- Avoid revenge trading after losses
- Let the AI handle the analysis while you manage risk

#### Technical Issues
- Always have API keys properly configured
- Monitor system health regularly
- Keep backups of successful strategy configurations
- Test changes in small amounts first

### Advanced Usage

#### Multi-Strategy Portfolios
- Run different strategies for different market conditions
- Combine momentum and value approaches
- Use sector rotation alongside stock picking
- Balance short-term and long-term strategies

#### Custom Research Integration
- Incorporate proprietary research into strategy prompts
- Use sector-specific knowledge to enhance prompts
- Combine fundamental and technical analysis
- Leverage industry expertise for better context

#### Performance Optimization
- Monitor LLM token usage and costs
- Optimize execution frequency based on strategy type
- Use caching for market data to reduce API calls
- Balance comprehensive analysis with execution speed

## Getting Help

### Documentation Resources
- **API Documentation**: Complete API reference at `/docs`
- **Architecture Guide**: Understanding system design
- **Developer Guide**: For customization and development
- **Troubleshooting Guide**: Common issues and solutions

### Community and Support
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Share strategies and ask questions
- **Wiki**: Community-contributed tips and guides
- **Examples**: Sample strategies and configurations

### Best Practice Examples

#### Successful Strategy Templates
The system includes several proven strategy templates:

- **Take-Private Arbitrage**: Focus on merger deals
- **Earnings Momentum**: Post-earnings opportunities
- **Insider Conviction**: Following insider buying
- **Sector Rotation**: Cyclical sector allocation

Study these examples to understand effective prompt structure and risk management techniques.

Remember: FinTradeAgent is a powerful tool for systematic trading research and strategy development. Success comes from combining AI capabilities with sound trading principles, proper risk management, and continuous learning from market feedback.

Happy trading! 📈