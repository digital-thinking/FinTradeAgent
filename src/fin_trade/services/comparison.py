"""Portfolio comparison and benchmarking service."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from fin_trade.models import AssetClass

if TYPE_CHECKING:
    from fin_trade.services.portfolio import PortfolioService
    from fin_trade.services.stock_data import StockDataService


@dataclass
class PortfolioMetrics:
    """Performance metrics for a portfolio."""

    total_return_pct: float
    annualized_return_pct: float | None
    volatility_pct: float | None  # Annualized standard deviation
    sharpe_ratio: float | None  # (return - risk_free_rate) / volatility
    max_drawdown_pct: float
    win_rate_pct: float | None  # % of trades that were profitable
    profit_factor_pct: float | None  # Σwinners_$ / |Σlosers_$|
    alpha_pct: float | None  # Excess return vs benchmark
    beta: float | None  # Correlation with benchmark
    days_active: int
    num_trades: int


class ComparisonService:
    """Service for comparing portfolio performance against benchmarks."""

    RISK_FREE_RATE = 0.05  # 5% annual risk-free rate assumption

    def __init__(
        self,
        portfolio_service: "PortfolioService",
        stock_data_service: "StockDataService",
    ):
        self.portfolio_service = portfolio_service
        self.stock_data_service = stock_data_service

    def get_default_benchmark(self, asset_class: AssetClass) -> str:
        """Return a benchmark symbol appropriate for portfolio asset class."""
        if asset_class == AssetClass.CRYPTO:
            return "BTC-USD"
        return "SPY"

    def _build_portfolio_value_series(
        self,
        portfolio_name: str,
    ) -> pd.DataFrame:
        """Build a time series of portfolio values from trade history.

        Returns DataFrame with columns: date, value
        """
        config, state = self.portfolio_service.load_portfolio(portfolio_name)

        if not state.trades:
            return pd.DataFrame(columns=["date", "value"])

        # Reconstruct portfolio value over time
        initial_cash = (
            state.initial_investment
            if state.initial_investment is not None
            else config.initial_amount
        )
        cash = initial_cash
        holdings: dict[str, float] = {}
        trades = sorted(state.trades, key=lambda trade: trade.timestamp)
        tickers = [trade.ticker for trade in trades]
        closes = self.stock_data_service.get_closes(
            tickers, trades[0].timestamp, datetime.now(timezone.utc)
        )
        # Key by calendar date (no tz): trade timestamps are tz-aware UTC while
        # the close-price index is tz-naive UTC. `date` lets the two line up.
        trades_by_date: dict[date, list] = {}
        for trade in trades:
            trades_by_date.setdefault(trade.timestamp.date(), []).append(trade)

        records = []

        for bar_ts, close_row in closes.iterrows():
            for trade in trades_by_date.get(bar_ts.date(), []):
                ticker = trade.ticker.upper()
                trade_cost = trade.price * trade.quantity

                if trade.action == "BUY":
                    cash -= trade_cost
                    holdings[ticker] = holdings.get(ticker, 0.0) + trade.quantity
                else:  # SELL
                    cash += trade_cost
                    holdings[ticker] = holdings.get(ticker, 0.0) - trade.quantity
                    if holdings[ticker] <= 0:
                        del holdings[ticker]

            holdings_value = sum(
                quantity * float(close_row[ticker])
                for ticker, quantity in holdings.items()
            )
            total_value = cash + holdings_value

            records.append({
                "date": bar_ts,
                "value": total_value,
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def get_normalized_returns(
        self,
        portfolio_names: list[str],
        start_date: datetime | None = None,
        include_benchmark: bool = True,
        benchmark_symbol: str | None = None,
    ) -> pd.DataFrame:
        """Get normalized (rebased to 100) return series for multiple portfolios.

        Args:
            portfolio_names: List of portfolio names to compare
            start_date: Optional start date (uses latest first trade if None)
            include_benchmark: Include benchmark (SPY) in comparison
            benchmark_symbol: Benchmark ticker symbol

        Returns:
            DataFrame with columns: date, {portfolio_name}_return, ..., benchmark_return
            All returns are rebased to 100 at the start date.
        """
        all_series = {}
        earliest_dates = []

        # Get portfolio value series
        for name in portfolio_names:
            df = self._build_portfolio_value_series(name)
            if df.empty:
                continue
            # Convert to date only (no time component) for proper comparison
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            all_series[name] = df
            earliest_dates.append(df["date"].min())

        if not all_series:
            return pd.DataFrame()

        # Use provided start_date or latest first trade
        if start_date is None:
            start_date = max(earliest_dates)
        else:
            start_date = pd.to_datetime(start_date).normalize()

        if benchmark_symbol is None and portfolio_names:
            first_config, _ = self.portfolio_service.load_portfolio(portfolio_names[0])
            benchmark_symbol = self.get_default_benchmark(first_config.asset_class)
        benchmark_symbol = benchmark_symbol or "SPY"

        # Get benchmark data if requested
        if include_benchmark:
            end_date = datetime.now(timezone.utc)
            benchmark_df = self.stock_data_service.get_benchmark_performance(
                symbol=benchmark_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            benchmark_df = benchmark_df.copy()
            benchmark_df["date"] = pd.to_datetime(benchmark_df["date"]).dt.normalize()
            # Rebase to 100
            benchmark_df["value"] = 100 * (1 + benchmark_df["cumulative_return"] / 100)
            all_series[f"{benchmark_symbol}_benchmark"] = benchmark_df[["date", "value"]]

        # Create unified date range (daily) from all series
        min_date = min(df["date"].min() for df in all_series.values())
        max_date = max(df["date"].max() for df in all_series.values())
        date_range = pd.date_range(start=min_date, end=max_date, freq="D")

        result_data = {"date": date_range}

        # Resample each series to daily using forward fill
        for name, df in all_series.items():
            # Filter to start_date
            df_filtered = df[df["date"] >= start_date].copy()
            if df_filtered.empty:
                continue

            # Get start value for normalization
            start_value = df_filtered["value"].iloc[0]
            if start_value == 0:
                continue

            # Create normalized values (rebased to 100)
            df_filtered["normalized"] = (df_filtered["value"] / start_value) * 100

            # Set date as index and reindex to full date range with forward fill
            df_indexed = df_filtered.set_index("date")["normalized"]
            # Remove duplicates by keeping last value for each date
            df_indexed = df_indexed[~df_indexed.index.duplicated(keep="last")]
            # Reindex to full date range and forward fill
            df_reindexed = df_indexed.reindex(date_range, method="ffill")

            # Set values before start_date to None
            df_reindexed[date_range < start_date] = None

            col_name = f"{name}_return" if not name.endswith("_benchmark") else name
            result_data[col_name] = df_reindexed.values

        return pd.DataFrame(result_data)

    def _calculate_max_drawdown(self, values: list[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if not values or len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_performance_stats(self, trades: list) -> tuple[float | None, float | None]:
        """Calculate win rate (%) and profit factor (Σwins/|Σlosses|).

        Win rate is calculated per tax-lot closure (FIFO), not per SELL event.
        Profit factor is sum of gross profits / sum of gross losses.
        """
        if not trades:
            return None, None

        # Track positions and realized P/L
        positions: dict[str, list[tuple[float, int]]] = {}  # ticker -> [(price, qty), ...]
        profitable_lots = 0
        total_lots_closed = 0
        gross_profits = 0.0
        gross_losses = 0.0

        for trade in trades:
            if trade.action == "BUY":
                if trade.ticker not in positions:
                    positions[trade.ticker] = []
                positions[trade.ticker].append((trade.price, trade.quantity))
            else:  # SELL
                if trade.ticker in positions and positions[trade.ticker]:
                    # FIFO: sell oldest shares first
                    remaining_to_sell = trade.quantity
                    sell_price = trade.price

                    while remaining_to_sell > 0 and positions[trade.ticker]:
                        buy_price, buy_qty = positions[trade.ticker][0]
                        shares_to_close = min(remaining_to_sell, buy_qty)

                        # Calculate P/L for this tax lot
                        pnl = (sell_price - buy_price) * shares_to_close
                        if pnl > 0:
                            profitable_lots += 1
                            gross_profits += pnl
                        elif pnl < 0:
                            gross_losses += abs(pnl)
                        # We count a "lot" as each unique BUY entry we touch
                        total_lots_closed += 1

                        remaining_to_sell -= shares_to_close
                        if shares_to_close >= buy_qty:
                            positions[trade.ticker].pop(0)
                        else:
                            positions[trade.ticker][0] = (buy_price, buy_qty - shares_to_close)

        win_rate = None
        if total_lots_closed > 0:
            win_rate = (profitable_lots / total_lots_closed) * 100

        profit_factor = None
        if gross_losses > 0:
            profit_factor = gross_profits / gross_losses
        elif gross_profits > 0:
            # Infinite profit factor if no losses, but some profit
            profit_factor = float('inf')

        return win_rate, profit_factor

    def _calculate_beta(
        self,
        portfolio_values: pd.DataFrame,
        benchmark_values: pd.DataFrame,
    ) -> float | None:
        """Calculate beta from aligned business-day return series."""
        portfolio_series = portfolio_values.copy()
        benchmark_series = benchmark_values.copy()

        portfolio_series["date"] = pd.to_datetime(portfolio_series["date"]).dt.normalize()
        benchmark_series["date"] = pd.to_datetime(benchmark_series["date"]).dt.normalize()

        portfolio_series = portfolio_series.sort_values("date").drop_duplicates(
            subset="date", keep="last"
        )
        benchmark_series = benchmark_series.sort_values("date").drop_duplicates(
            subset="date", keep="last"
        )

        common_start = max(
            portfolio_series["date"].min(),
            benchmark_series["date"].min(),
        )
        common_end = min(
            portfolio_series["date"].max(),
            benchmark_series["date"].max(),
        )
        business_days = pd.date_range(start=common_start, end=common_end, freq="B")
        if len(business_days) < 2:
            return None

        aligned_portfolio = portfolio_series.set_index("date")["value"].reindex(
            business_days,
            method="ffill",
        )
        aligned_benchmark = benchmark_series.set_index("date")["price"].reindex(
            business_days,
            method="ffill",
        )

        portfolio_returns = aligned_portfolio.pct_change().dropna()
        benchmark_returns = aligned_benchmark.pct_change().dropna()
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return None

        benchmark_return_values = benchmark_returns.to_numpy()
        benchmark_variance = float(np.var(benchmark_return_values))
        if np.isclose(benchmark_variance, 0.0):
            return None

        portfolio_return_values = portfolio_returns.to_numpy()
        covariance = float(
            np.cov(portfolio_return_values, benchmark_return_values, ddof=0)[0, 1]
        )
        return covariance / benchmark_variance

    def _calculate_annualized_return(
        self,
        start_value: float,
        end_value: float,
        days_active: int,
    ) -> float | None:
        """Calculate annualized return percentage for a period."""
        if days_active <= 0 or start_value <= 0 or end_value <= 0:
            return None

        years = days_active / 365
        if years <= 0:
            return None

        return float(((end_value / start_value) ** (1 / years) - 1) * 100)

    def _calculate_daily_returns(self, value_df: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from a daily-resampled portfolio value series."""
        series_df = value_df.copy()
        series_df["date"] = pd.to_datetime(series_df["date"]).dt.normalize()
        series_df = series_df.sort_values("date").drop_duplicates(subset="date", keep="last")

        if series_df.empty:
            return pd.Series(dtype=float)

        daily_index = pd.date_range(
            start=series_df["date"].iloc[0],
            end=series_df["date"].iloc[-1],
            freq="D",
        )
        daily_values = series_df.set_index("date")["value"].reindex(daily_index, method="ffill")
        return daily_values.pct_change().dropna()

    def calculate_metrics(
        self,
        portfolio_name: str,
        benchmark_symbol: str | None = None,
    ) -> PortfolioMetrics:
        """Calculate comprehensive performance metrics for a portfolio.

        Args:
            portfolio_name: Name of the portfolio
            benchmark_symbol: Benchmark ticker for alpha/beta calculation

        Returns:
            PortfolioMetrics dataclass with all calculated metrics
        """
        config, state = self.portfolio_service.load_portfolio(portfolio_name)
        benchmark_symbol = benchmark_symbol or self.get_default_benchmark(config.asset_class)

        if not state.trades:
            return PortfolioMetrics(
                total_return_pct=0.0,
                annualized_return_pct=None,
                volatility_pct=None,
                sharpe_ratio=None,
                max_drawdown_pct=0.0,
                win_rate_pct=None,
                profit_factor_pct=None,
                alpha_pct=None,
                beta=None,
                days_active=0,
                num_trades=0,
            )

        # Build value series
        value_df = self._build_portfolio_value_series(portfolio_name)
        if value_df.empty:
            raise ValueError(f"No value data for portfolio {portfolio_name}")

        initial_value = (
            state.initial_investment
            if state.initial_investment is not None
            else config.initial_amount
        )
        current_value = value_df["value"].iloc[-1]

        # Total return
        total_return = ((current_value - initial_value) / initial_value) * 100

        # Days active
        first_trade = state.trades[0].timestamp
        days_active = (datetime.now(timezone.utc) - first_trade).days
        days_active = max(days_active, 1)  # Avoid division by zero

        # Annualized return
        annualized_return = self._calculate_annualized_return(
            initial_value,
            current_value,
            days_active,
        )

        # Calculate daily returns for volatility and Sharpe
        daily_returns = self._calculate_daily_returns(value_df)

        volatility = None
        sharpe_ratio = None
        if len(daily_returns) > 1:
            # Annualized volatility (std * sqrt(252 trading days))
            volatility = float(daily_returns.std() * np.sqrt(252) * 100)

            if volatility > 0 and annualized_return is not None:
                # Sharpe ratio
                excess_return = annualized_return - self.RISK_FREE_RATE * 100
                sharpe_ratio = excess_return / volatility

        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(value_df["value"].tolist())

        # Performance stats (win rate, profit factor)
        win_rate, profit_factor = self._calculate_performance_stats(state.trades)

        # Alpha and Beta (vs benchmark)
        alpha = None
        beta = None
        try:
            benchmark_df = self.stock_data_service.get_benchmark_performance(
                symbol=benchmark_symbol,
                start_date=first_trade,
                end_date=datetime.now(timezone.utc),
            )
            if not benchmark_df.empty:
                beta = self._calculate_beta(value_df[["date", "value"]], benchmark_df)
                benchmark_annualized_return = self._calculate_annualized_return(
                    float(benchmark_df["price"].iloc[0]),
                    float(benchmark_df["price"].iloc[-1]),
                    days_active,
                )
                if (
                    annualized_return is not None
                    and benchmark_annualized_return is not None
                ):
                    risk_free_rate_pct = self.RISK_FREE_RATE * 100
                    if beta is None:
                        alpha = annualized_return - benchmark_annualized_return
                    else:
                        alpha = annualized_return - (
                            risk_free_rate_pct
                            + beta * (benchmark_annualized_return - risk_free_rate_pct)
                        )
        except Exception:
            pass  # Benchmark data unavailable

        return PortfolioMetrics(
            total_return_pct=total_return,
            annualized_return_pct=annualized_return,
            volatility_pct=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown,
            win_rate_pct=win_rate,
            profit_factor_pct=profit_factor,
            alpha_pct=alpha,
            beta=beta,
            days_active=days_active,
            num_trades=len(state.trades),
        )

    def get_comparison_table(
        self,
        portfolio_names: list[str],
        benchmark_symbol: str | None = None,
    ) -> pd.DataFrame:
        """Get a comparison table of metrics for multiple portfolios.

        Args:
            portfolio_names: List of portfolio names to compare
            benchmark_symbol: Benchmark ticker symbol

        Returns:
            DataFrame with portfolios as columns and metrics as rows
        """
        metrics_data = {}
        portfolio_metrics: dict[str, PortfolioMetrics] = {}
        portfolio_first_trades: dict[str, datetime] = {}
        use_excess_return_label = False
        if benchmark_symbol is None and portfolio_names:
            first_config, _ = self.portfolio_service.load_portfolio(portfolio_names[0])
            benchmark_symbol = self.get_default_benchmark(first_config.asset_class)
        benchmark_symbol = benchmark_symbol or "SPY"

        for name in portfolio_names:
            try:
                _, state = self.portfolio_service.load_portfolio(name)
                if state.trades:
                    portfolio_first_trades[name] = min(
                        trade.timestamp for trade in state.trades
                    )
                metrics = self.calculate_metrics(name, benchmark_symbol)
                portfolio_metrics[name] = metrics
                use_excess_return_label = use_excess_return_label or metrics.beta is None
            except Exception as e:
                metrics_data[name] = {"Error": str(e)}

        alpha_label = "Excess Return" if use_excess_return_label else "Alpha"

        for name, metrics in portfolio_metrics.items():
            metrics_data[name] = {
                    "Total Return": f"{metrics.total_return_pct:+.1f}%",
                    "Annualized Return": (
                        f"{metrics.annualized_return_pct:+.1f}%"
                        if metrics.annualized_return_pct is not None
                        else "N/A"
                    ),
                    "Volatility": (
                        f"{metrics.volatility_pct:.1f}%"
                        if metrics.volatility_pct is not None
                        else "N/A"
                    ),
                    "Sharpe Ratio": (
                        f"{metrics.sharpe_ratio:.2f}"
                        if metrics.sharpe_ratio is not None
                        else "N/A"
                    ),
                    "Max Drawdown": f"-{metrics.max_drawdown_pct:.1f}%",
                    "Win Rate": (
                        f"{metrics.win_rate_pct:.0f}%"
                        if metrics.win_rate_pct is not None
                        else "N/A"
                    ),
                    "Profit Factor": (
                        f"{metrics.profit_factor_pct:.2f}"
                        if metrics.profit_factor_pct is not None
                        else "N/A"
                    ),
                    alpha_label: (
                        f"{metrics.alpha_pct:+.1f}%"
                        if metrics.alpha_pct is not None
                        else "N/A"
                    ),
                    "Beta": f"{metrics.beta:.2f}" if metrics.beta is not None else "N/A",
                    "Days Active": str(metrics.days_active),
                    "Trades": str(metrics.num_trades),
                }

        # Benchmark column: compute real metrics over the widest portfolio window
        # (earliest first_trade across the set → now) so numbers are directly
        # comparable to the portfolio rows instead of being fabricated.
        benchmark_window = None
        if portfolio_first_trades:
            widest_start = min(portfolio_first_trades.values())
            now = datetime.now(timezone.utc)
            try:
                benchmark_df = self.stock_data_service.get_benchmark_performance(
                    symbol=benchmark_symbol,
                    start_date=widest_start,
                    end_date=now,
                )
                if not benchmark_df.empty:
                    benchmark_value_df = benchmark_df[["date", "price"]].rename(
                        columns={"price": "value"}
                    )
                    start_price = float(benchmark_df["price"].iloc[0])
                    end_price = float(benchmark_df["price"].iloc[-1])
                    days_active = max((now - widest_start).days, 1)

                    total_return = (
                        ((end_price - start_price) / start_price) * 100
                        if start_price > 0
                        else 0.0
                    )
                    annualized_return = self._calculate_annualized_return(
                        start_price, end_price, days_active
                    )

                    daily_returns = self._calculate_daily_returns(benchmark_value_df)
                    volatility = None
                    sharpe_ratio = None
                    if len(daily_returns) > 1:
                        volatility = float(daily_returns.std() * np.sqrt(252) * 100)
                        if volatility > 0 and annualized_return is not None:
                            excess_return = annualized_return - self.RISK_FREE_RATE * 100
                            sharpe_ratio = excess_return / volatility

                    max_drawdown = self._calculate_max_drawdown(
                        benchmark_value_df["value"].tolist()
                    )

                    metrics_data[benchmark_symbol] = {
                        "Total Return": f"{total_return:+.1f}%",
                        "Annualized Return": (
                            f"{annualized_return:+.1f}%"
                            if annualized_return is not None
                            else "N/A"
                        ),
                        "Volatility": (
                            f"{volatility:.1f}%"
                            if volatility is not None
                            else "N/A"
                        ),
                        "Sharpe Ratio": (
                            f"{sharpe_ratio:.2f}"
                            if sharpe_ratio is not None
                            else "N/A"
                        ),
                        "Max Drawdown": f"-{max_drawdown:.1f}%",
                        "Win Rate": "N/A",
                        "Profit Factor": "N/A",
                        alpha_label: "+0.0%",
                        "Beta": "1.00",
                        "Days Active": str(days_active),
                        "Trades": "N/A",
                    }
                    benchmark_window = {
                        "symbol": benchmark_symbol,
                        "start": widest_start,
                        "end": now,
                        "days": days_active,
                    }
            except Exception:
                pass

        result = pd.DataFrame(metrics_data)
        if benchmark_window is not None:
            result.attrs["benchmark_window"] = benchmark_window
        return result
