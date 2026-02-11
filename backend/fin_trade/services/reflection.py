"""Self-reflective learning service for trading agents."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fin_trade.models import PortfolioState, Trade


@dataclass
class CompletedTrade:
    """A completed trade cycle (BUY followed by SELL)."""

    ticker: str
    name: str
    buy_date: datetime
    sell_date: datetime
    buy_price: float
    sell_price: float
    quantity: int
    buy_reasoning: str
    sell_reasoning: str
    holding_days: int
    profit_loss: float
    return_pct: float
    is_winner: bool


@dataclass
class TradeMetrics:
    """Aggregate metrics from trade analysis."""

    total_completed_trades: int
    winners: int
    losers: int
    win_rate: float
    avg_gain_pct: float
    avg_loss_pct: float
    avg_holding_days: float
    total_realized_profit: float
    best_trade: CompletedTrade | None
    worst_trade: CompletedTrade | None
    avg_winner_holding_days: float
    avg_loser_holding_days: float


@dataclass
class BiasAnalysis:
    """Analysis of potential trading biases."""

    # Sector concentration
    sector_concentration: dict[str, int] = field(default_factory=dict)
    most_traded_sector: str | None = None

    # Timing patterns
    avg_holding_days: float = 0.0
    quick_trades_count: int = 0  # < 7 days
    long_trades_count: int = 0  # > 30 days

    # Win/loss patterns
    winners_cut_early: int = 0  # Winners held < avg holding time
    losers_held_long: int = 0  # Losers held > avg holding time

    # Common reasoning themes
    buy_themes: list[tuple[str, int]] = field(default_factory=list)
    sell_themes: list[tuple[str, int]] = field(default_factory=list)

    # Warnings
    warnings: list[str] = field(default_factory=list)


@dataclass
class ReflectionResult:
    """Complete self-reflection analysis."""

    metrics: TradeMetrics
    bias_analysis: BiasAnalysis
    completed_trades: list[CompletedTrade]
    insights: list[str]

    def to_context_string(self) -> str:
        """Format reflection as context for agent prompt."""
        lines = []

        if self.metrics.total_completed_trades == 0:
            return "No completed trade cycles to analyze yet. Focus on building positions according to your strategy."

        lines.append("SELF-REFLECTION ON PAST PERFORMANCE:")
        lines.append("")

        # Performance summary
        lines.append(f"Trade Record: {self.metrics.winners}W-{self.metrics.losers}L "
                    f"({self.metrics.win_rate:.1f}% win rate)")
        lines.append(f"Average Winner: +{self.metrics.avg_gain_pct:.1f}% | "
                    f"Average Loser: {self.metrics.avg_loss_pct:.1f}%")
        lines.append(f"Total Realized P/L: ${self.metrics.total_realized_profit:,.2f}")
        lines.append(f"Average Holding Period: {self.metrics.avg_holding_days:.0f} days")
        lines.append("")

        # Best and worst trades
        if self.metrics.best_trade:
            bt = self.metrics.best_trade
            lines.append(f"Best Trade: {bt.ticker} +{bt.return_pct:.1f}% "
                        f"(held {bt.holding_days} days)")
            lines.append(f"  Reasoning: {bt.buy_reasoning[:100]}...")
        if self.metrics.worst_trade:
            wt = self.metrics.worst_trade
            lines.append(f"Worst Trade: {wt.ticker} {wt.return_pct:.1f}% "
                        f"(held {wt.holding_days} days)")
            lines.append(f"  Reasoning: {wt.buy_reasoning[:100]}...")
        lines.append("")

        # Bias warnings
        if self.bias_analysis.warnings:
            lines.append("IDENTIFIED BIASES TO ADDRESS:")
            for warning in self.bias_analysis.warnings:
                lines.append(f"  - {warning}")
            lines.append("")

        # Actionable insights
        if self.insights:
            lines.append("KEY INSIGHTS FOR IMPROVEMENT:")
            for insight in self.insights:
                lines.append(f"  - {insight}")

        return "\n".join(lines)


class ReflectionService:
    """Service for analyzing past trading performance and generating insights."""

    # Common reasoning themes to detect
    REASONING_THEMES = {
        "momentum": ["momentum", "trend", "breakout", "rally", "surge"],
        "value": ["undervalued", "cheap", "discount", "pe ratio", "value"],
        "growth": ["growth", "expanding", "revenue growth", "earnings growth"],
        "technical": ["support", "resistance", "moving average", "rsi", "macd"],
        "fundamental": ["earnings", "revenue", "profit", "margin", "balance sheet"],
        "news": ["news", "announcement", "report", "event", "catalyst"],
        "sector": ["sector", "industry", "rotation", "cyclical"],
        "fear": ["fear", "panic", "selloff", "crash", "correction"],
        "fomo": ["missing out", "opportunity", "everyone", "hot stock"],
    }

    def __init__(self, security_service=None):
        self.security_service = security_service

    def analyze_performance(self, state: PortfolioState) -> ReflectionResult:
        """Analyze past trading performance and generate insights."""
        completed_trades = self._find_completed_trades(state.trades)
        metrics = self._calculate_metrics(completed_trades)
        bias_analysis = self._analyze_biases(completed_trades, metrics)
        insights = self._generate_insights(metrics, bias_analysis)

        return ReflectionResult(
            metrics=metrics,
            bias_analysis=bias_analysis,
            completed_trades=completed_trades,
            insights=insights,
        )

    def _find_completed_trades(self, trades: list[Trade]) -> list[CompletedTrade]:
        """Find completed trade cycles (BUY followed by SELL)."""
        completed = []

        # Group trades by ticker
        trades_by_ticker: dict[str, list[Trade]] = {}
        for trade in trades:
            if trade.ticker not in trades_by_ticker:
                trades_by_ticker[trade.ticker] = []
            trades_by_ticker[trade.ticker].append(trade)

        # For each ticker, match BUYs with subsequent SELLs
        for ticker, ticker_trades in trades_by_ticker.items():
            # Sort by timestamp
            sorted_trades = sorted(ticker_trades, key=lambda t: t.timestamp)

            # Track open positions (FIFO matching)
            open_buys: list[Trade] = []

            for trade in sorted_trades:
                if trade.action == "BUY":
                    open_buys.append(trade)
                elif trade.action == "SELL" and open_buys:
                    # Match with oldest buys (FIFO), handling partial fills
                    remaining_sell_qty = trade.quantity

                    while remaining_sell_qty > 0 and open_buys:
                        buy = open_buys[0]
                        matched_qty = min(buy.quantity, remaining_sell_qty)

                        holding_days = (trade.timestamp - buy.timestamp).days
                        profit_loss = (trade.price - buy.price) * matched_qty
                        return_pct = ((trade.price - buy.price) / buy.price) * 100

                        completed.append(
                            CompletedTrade(
                                ticker=ticker,
                                name=buy.name,
                                buy_date=buy.timestamp,
                                sell_date=trade.timestamp,
                                buy_price=buy.price,
                                sell_price=trade.price,
                                quantity=matched_qty,
                                buy_reasoning=buy.reasoning,
                                sell_reasoning=trade.reasoning,
                                holding_days=holding_days,
                                profit_loss=profit_loss,
                                return_pct=return_pct,
                                is_winner=return_pct > 0,
                            )
                        )

                        remaining_sell_qty -= matched_qty

                        if matched_qty >= buy.quantity:
                            # Buy fully consumed, remove it
                            open_buys.pop(0)
                        else:
                            # Buy partially consumed, update remaining quantity
                            open_buys[0] = Trade(
                                ticker=buy.ticker,
                                name=buy.name,
                                action=buy.action,
                                quantity=buy.quantity - matched_qty,
                                price=buy.price,
                                timestamp=buy.timestamp,
                                reasoning=buy.reasoning,
                            )

        return sorted(completed, key=lambda t: t.sell_date, reverse=True)

    def _calculate_metrics(self, completed_trades: list[CompletedTrade]) -> TradeMetrics:
        """Calculate aggregate trading metrics."""
        if not completed_trades:
            return TradeMetrics(
                total_completed_trades=0,
                winners=0,
                losers=0,
                win_rate=0.0,
                avg_gain_pct=0.0,
                avg_loss_pct=0.0,
                avg_holding_days=0.0,
                total_realized_profit=0.0,
                best_trade=None,
                worst_trade=None,
                avg_winner_holding_days=0.0,
                avg_loser_holding_days=0.0,
            )

        winners = [t for t in completed_trades if t.is_winner]
        losers = [t for t in completed_trades if not t.is_winner]

        win_rate = (len(winners) / len(completed_trades)) * 100 if completed_trades else 0
        avg_gain = sum(t.return_pct for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.return_pct for t in losers) / len(losers) if losers else 0
        avg_holding = sum(t.holding_days for t in completed_trades) / len(completed_trades)
        total_profit = sum(t.profit_loss for t in completed_trades)

        best = max(completed_trades, key=lambda t: t.return_pct)
        worst = min(completed_trades, key=lambda t: t.return_pct)

        avg_winner_days = sum(t.holding_days for t in winners) / len(winners) if winners else 0
        avg_loser_days = sum(t.holding_days for t in losers) / len(losers) if losers else 0

        return TradeMetrics(
            total_completed_trades=len(completed_trades),
            winners=len(winners),
            losers=len(losers),
            win_rate=win_rate,
            avg_gain_pct=avg_gain,
            avg_loss_pct=avg_loss,
            avg_holding_days=avg_holding,
            total_realized_profit=total_profit,
            best_trade=best,
            worst_trade=worst,
            avg_winner_holding_days=avg_winner_days,
            avg_loser_holding_days=avg_loser_days,
        )

    def _analyze_biases(
        self, completed_trades: list[CompletedTrade], metrics: TradeMetrics
    ) -> BiasAnalysis:
        """Analyze trading patterns for potential biases."""
        bias = BiasAnalysis()

        if not completed_trades:
            return bias

        # Timing analysis
        bias.avg_holding_days = metrics.avg_holding_days
        bias.quick_trades_count = sum(1 for t in completed_trades if t.holding_days < 7)
        bias.long_trades_count = sum(1 for t in completed_trades if t.holding_days > 30)

        # Win/loss holding pattern analysis
        if metrics.avg_holding_days > 0:
            for trade in completed_trades:
                if trade.is_winner and trade.holding_days < metrics.avg_holding_days * 0.5:
                    bias.winners_cut_early += 1
                if not trade.is_winner and trade.holding_days > metrics.avg_holding_days * 1.5:
                    bias.losers_held_long += 1

        # Reasoning theme analysis
        buy_theme_counts: Counter = Counter()
        sell_theme_counts: Counter = Counter()

        for trade in completed_trades:
            buy_lower = trade.buy_reasoning.lower()
            sell_lower = trade.sell_reasoning.lower()

            for theme, keywords in self.REASONING_THEMES.items():
                if any(kw in buy_lower for kw in keywords):
                    buy_theme_counts[theme] += 1
                if any(kw in sell_lower for kw in keywords):
                    sell_theme_counts[theme] += 1

        bias.buy_themes = buy_theme_counts.most_common(5)
        bias.sell_themes = sell_theme_counts.most_common(5)

        # Generate warnings
        warnings = []

        if metrics.win_rate < 40 and metrics.total_completed_trades >= 5:
            warnings.append(
                f"Low win rate ({metrics.win_rate:.0f}%). Consider more thorough analysis before entering positions."
            )

        if bias.quick_trades_count > len(completed_trades) * 0.5:
            warnings.append(
                "High frequency of quick trades (<7 days). May indicate overtrading or impatience."
            )

        if bias.winners_cut_early > len([t for t in completed_trades if t.is_winner]) * 0.5:
            warnings.append(
                "Tendency to cut winners early. Consider letting profitable positions run longer."
            )

        if bias.losers_held_long > len([t for t in completed_trades if not t.is_winner]) * 0.5:
            warnings.append(
                "Tendency to hold losers too long. Consider stricter stop-loss discipline."
            )

        if metrics.avg_loss_pct < -15:
            warnings.append(
                f"Average loss of {metrics.avg_loss_pct:.1f}% is significant. Tighten stop-losses."
            )

        # Check for FOMO patterns
        if "fomo" in dict(bias.buy_themes):
            warnings.append(
                "FOMO-driven purchases detected in reasoning. Make decisions based on fundamentals, not fear of missing out."
            )

        bias.warnings = warnings
        return bias

    def _generate_insights(
        self, metrics: TradeMetrics, bias: BiasAnalysis
    ) -> list[str]:
        """Generate actionable insights from the analysis."""
        insights = []

        if metrics.total_completed_trades == 0:
            return ["Not enough completed trades for meaningful analysis."]

        # Win rate insight
        if metrics.win_rate >= 60:
            insights.append(
                f"Strong win rate of {metrics.win_rate:.0f}%. Continue current selection methodology."
            )
        elif metrics.win_rate >= 40:
            insights.append(
                f"Moderate win rate of {metrics.win_rate:.0f}%. Focus on improving entry timing."
            )
        else:
            insights.append(
                f"Win rate of {metrics.win_rate:.0f}% needs improvement. Review selection criteria."
            )

        # Risk/reward insight
        if metrics.avg_gain_pct > 0 and metrics.avg_loss_pct < 0:
            risk_reward = abs(metrics.avg_gain_pct / metrics.avg_loss_pct)
            if risk_reward > 2:
                insights.append(
                    f"Excellent risk/reward ratio of {risk_reward:.1f}:1. Maintain this discipline."
                )
            elif risk_reward < 1:
                insights.append(
                    f"Poor risk/reward ratio of {risk_reward:.1f}:1. Let winners run, cut losers faster."
                )

        # Holding period insight
        if metrics.avg_winner_holding_days > 0 and metrics.avg_loser_holding_days > 0:
            if metrics.avg_loser_holding_days > metrics.avg_winner_holding_days * 1.5:
                insights.append(
                    f"Losers held avg {metrics.avg_loser_holding_days:.0f} days vs winners {metrics.avg_winner_holding_days:.0f} days. "
                    "Reverse this pattern."
                )

        # Theme-based insights
        if bias.buy_themes:
            top_theme = bias.buy_themes[0][0]
            insights.append(
                f"Most common buy thesis: '{top_theme}'. Ensure diversification of strategies."
            )

        # Best trade lesson
        if metrics.best_trade:
            bt = metrics.best_trade
            insights.append(
                f"Best trade ({bt.ticker} +{bt.return_pct:.1f}%) held for {bt.holding_days} days. "
                "Look for similar setups."
            )

        return insights[:5]  # Limit to top 5 insights
