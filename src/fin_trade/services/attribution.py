"""Performance attribution service for sector and ticker analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fin_trade.models import PortfolioConfig, PortfolioState
    from fin_trade.services.security import SecurityService


@dataclass
class HoldingAttribution:
    """Attribution data for a single holding."""

    ticker: str
    name: str
    sector: str | None
    industry: str | None
    quantity: int
    avg_price: float
    current_price: float
    cost_basis: float
    current_value: float
    unrealized_gain: float
    gain_pct: float
    contribution_pct: float  # % of total portfolio gain


@dataclass
class SectorAttribution:
    """Attribution data for a sector."""

    sector: str
    holdings_count: int
    total_cost_basis: float
    total_current_value: float
    total_gain: float
    gain_pct: float
    allocation_pct: float  # % of portfolio value in this sector
    contribution_pct: float  # % of total portfolio gain from this sector


@dataclass
class AttributionResult:
    """Complete attribution analysis result."""

    by_holding: list[HoldingAttribution] = field(default_factory=list)
    by_sector: list[SectorAttribution] = field(default_factory=list)
    total_cost_basis: float = 0.0
    total_current_value: float = 0.0
    total_gain: float = 0.0
    total_gain_pct: float = 0.0
    top_contributor: HoldingAttribution | None = None
    top_detractor: HoldingAttribution | None = None


class AttributionService:
    """Service for calculating performance attribution by sector and ticker."""

    UNKNOWN_SECTOR = "Unknown"

    def __init__(self, security_service: SecurityService):
        self.security_service = security_service

    def calculate_attribution(
        self,
        config: PortfolioConfig,
        state: PortfolioState,
    ) -> AttributionResult:
        """Calculate performance attribution for a portfolio.

        Args:
            config: Portfolio configuration
            state: Current portfolio state

        Returns:
            AttributionResult with per-holding and per-sector breakdowns
        """
        if not state.holdings:
            return AttributionResult()

        # Calculate per-holding attribution
        holding_attributions: list[HoldingAttribution] = []
        total_cost_basis = 0.0
        total_current_value = 0.0

        for holding in state.holdings:
            current_price = self._get_price(holding.ticker)
            stock_info = self._get_stock_info(holding.ticker)

            cost_basis = holding.avg_price * holding.quantity
            current_value = current_price * holding.quantity
            unrealized_gain = current_value - cost_basis
            gain_pct = (unrealized_gain / cost_basis) * 100 if cost_basis > 0 else 0.0

            total_cost_basis += cost_basis
            total_current_value += current_value

            attr = HoldingAttribution(
                ticker=holding.ticker,
                name=holding.name,
                sector=stock_info.get("sector"),
                industry=stock_info.get("industry"),
                quantity=holding.quantity,
                avg_price=holding.avg_price,
                current_price=current_price,
                cost_basis=cost_basis,
                current_value=current_value,
                unrealized_gain=unrealized_gain,
                gain_pct=gain_pct,
                contribution_pct=0.0,  # Calculated below
            )
            holding_attributions.append(attr)

        # Calculate total gain and contribution percentages
        total_gain = total_current_value - total_cost_basis
        total_gain_pct = (total_gain / total_cost_basis) * 100 if total_cost_basis > 0 else 0.0

        # Update contribution percentages
        for attr in holding_attributions:
            if total_gain != 0:
                attr.contribution_pct = (attr.unrealized_gain / total_gain) * 100
            else:
                attr.contribution_pct = 0.0

        # Calculate sector attribution
        sector_attributions = self._calculate_sector_attribution(
            holding_attributions, total_current_value, total_gain
        )

        # Find top contributor and detractor
        sorted_by_gain = sorted(holding_attributions, key=lambda x: x.unrealized_gain, reverse=True)
        top_contributor = sorted_by_gain[0] if sorted_by_gain else None
        top_detractor = sorted_by_gain[-1] if sorted_by_gain and sorted_by_gain[-1].unrealized_gain < 0 else None

        return AttributionResult(
            by_holding=holding_attributions,
            by_sector=sector_attributions,
            total_cost_basis=total_cost_basis,
            total_current_value=total_current_value,
            total_gain=total_gain,
            total_gain_pct=total_gain_pct,
            top_contributor=top_contributor,
            top_detractor=top_detractor,
        )

    def _calculate_sector_attribution(
        self,
        holding_attributions: list[HoldingAttribution],
        total_current_value: float,
        total_gain: float,
    ) -> list[SectorAttribution]:
        """Aggregate holdings by sector."""
        sector_data: dict[str, dict] = {}

        for attr in holding_attributions:
            sector = attr.sector or self.UNKNOWN_SECTOR

            if sector not in sector_data:
                sector_data[sector] = {
                    "holdings_count": 0,
                    "total_cost_basis": 0.0,
                    "total_current_value": 0.0,
                    "total_gain": 0.0,
                }

            sector_data[sector]["holdings_count"] += 1
            sector_data[sector]["total_cost_basis"] += attr.cost_basis
            sector_data[sector]["total_current_value"] += attr.current_value
            sector_data[sector]["total_gain"] += attr.unrealized_gain

        # Build sector attributions
        sector_attributions: list[SectorAttribution] = []
        for sector, data in sector_data.items():
            gain_pct = (
                (data["total_gain"] / data["total_cost_basis"]) * 100
                if data["total_cost_basis"] > 0
                else 0.0
            )
            allocation_pct = (
                (data["total_current_value"] / total_current_value) * 100
                if total_current_value > 0
                else 0.0
            )
            contribution_pct = (
                (data["total_gain"] / total_gain) * 100 if total_gain != 0 else 0.0
            )

            sector_attributions.append(
                SectorAttribution(
                    sector=sector,
                    holdings_count=data["holdings_count"],
                    total_cost_basis=data["total_cost_basis"],
                    total_current_value=data["total_current_value"],
                    total_gain=data["total_gain"],
                    gain_pct=gain_pct,
                    allocation_pct=allocation_pct,
                    contribution_pct=contribution_pct,
                )
            )

        # Sort by contribution (highest first)
        sector_attributions.sort(key=lambda x: x.total_gain, reverse=True)
        return sector_attributions

    def _get_price(self, ticker: str) -> float:
        """Get current price for a ticker."""
        return self.security_service.get_price(ticker)

    def _get_stock_info(self, ticker: str) -> dict:
        """Get stock info for a ticker."""
        return self.security_service.get_stock_info(ticker)
