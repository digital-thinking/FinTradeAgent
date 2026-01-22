"""LangGraph-based agent service for trading recommendations."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fin_trade.agents.graphs.simple_agent import build_simple_agent_graph
from fin_trade.models import AgentRecommendation, PortfolioConfig, PortfolioState
from fin_trade.services.security import SecurityService

_project_root = Path(__file__).parent.parent.parent.parent
_logs_dir = _project_root / "data" / "logs"

# Node descriptions for progress reporting
NODE_INFO = {
    "research": {
        "label": "Research",
        "description": "Searching for market data and news...",
        "icon": "🔍",
    },
    "analysis": {
        "label": "Analysis",
        "description": "Analyzing opportunities based on strategy...",
        "icon": "📊",
    },
    "generate": {
        "label": "Generate Trades",
        "description": "Generating trade recommendations...",
        "icon": "💡",
    },
    "validate": {
        "label": "Validate",
        "description": "Validating recommendations against constraints...",
        "icon": "✅",
    },
}


@dataclass
class StepMetrics:
    """Metrics for a single workflow step."""

    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ExecutionMetrics:
    """Aggregated metrics for the entire workflow execution."""

    total_duration_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    steps: dict[str, StepMetrics] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add_step(self, step_name: str, metrics: StepMetrics) -> None:
        self.steps[step_name] = metrics
        self.total_input_tokens += metrics.input_tokens
        self.total_output_tokens += metrics.output_tokens


@dataclass
class StepProgress:
    """Progress update for a workflow step."""

    step: str
    label: str
    description: str
    icon: str
    status: str  # "running", "completed", "failed"
    result_preview: str | None = None
    metrics: StepMetrics | None = None


class LangGraphAgentService:
    """Service for invoking LangGraph agents to get trading recommendations.

    This is a drop-in replacement for the original AgentService, using
    LangGraph for structured workflow execution.
    """

    def __init__(self, security_service: SecurityService | None = None):
        self.security_service = security_service or SecurityService()
        self.graph = build_simple_agent_graph()
        _logs_dir.mkdir(parents=True, exist_ok=True)

    def _save_log(
        self,
        portfolio_name: str,
        state: dict,
        result: dict,
        metrics: ExecutionMetrics,
    ) -> None:
        """Save workflow execution to log file for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = _logs_dir / f"{portfolio_name}_{timestamp}_langgraph.log"

        # Extract relevant info from state
        market_research = result.get("market_research", "N/A")
        analysis = result.get("analysis", "N/A")
        recommendations = result.get("recommendations")
        error = result.get("error")
        retry_count = result.get("retry_count", 0)

        recs_str = "None"
        if recommendations:
            trades_info = []
            for t in recommendations.trades:
                trades_info.append(
                    f"  - {t.action} {t.quantity} {t.ticker} ({t.name}): {t.reasoning[:100]}..."
                )
            recs_str = "\n".join(trades_info) if trades_info else "No trades"

        # Format metrics
        metrics_lines = []
        for step_name, step_metrics in metrics.steps.items():
            metrics_lines.append(
                f"  {step_name}: {step_metrics.duration_ms}ms, "
                f"{step_metrics.input_tokens} in / {step_metrics.output_tokens} out tokens"
            )
        metrics_str = "\n".join(metrics_lines) if metrics_lines else "  No metrics collected"

        log_content = f"""================================================================================
LANGGRAPH AGENT LOG - {datetime.now().isoformat()}
================================================================================
Portfolio: {portfolio_name}
Agent Mode: langgraph (simple)
Retry Count: {retry_count}
Error: {error or 'None'}

================================================================================
METRICS
================================================================================
Total Duration: {metrics.total_duration_ms}ms
Total Tokens: {metrics.total_tokens} ({metrics.total_input_tokens} in / {metrics.total_output_tokens} out)

Per-Step Breakdown:
{metrics_str}

================================================================================
MARKET RESEARCH
================================================================================
{market_research}

================================================================================
ANALYSIS
================================================================================
{analysis}

================================================================================
RECOMMENDATIONS
================================================================================
{recs_str}

================================================================================
OVERALL REASONING
================================================================================
{recommendations.overall_reasoning if recommendations else 'N/A'}
"""
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_content)

    def execute(
        self,
        config: PortfolioConfig,
        state: PortfolioState,
        on_progress: Callable[[StepProgress], None] | None = None,
    ) -> tuple[AgentRecommendation, ExecutionMetrics]:
        """Execute the LangGraph agent to get trading recommendations.

        Args:
            config: Portfolio configuration including strategy prompt
            state: Current portfolio state (cash, holdings, trades)
            on_progress: Optional callback for progress updates

        Returns:
            Tuple of (AgentRecommendation, ExecutionMetrics)

        Raises:
            RuntimeError: If agent fails after all retries
        """
        import time

        start_time = time.time()

        # Initialize state
        initial_state = {
            "portfolio_config": config,
            "portfolio_state": state,
            "market_research": "",
            "price_data": {},
            "analysis": "",
            "messages": [],
            "recommendations": None,
            "retry_count": 0,
            "error": None,
            "_metrics_research": None,
            "_metrics_analysis": None,
            "_metrics_generate": None,
            "_metrics_validate": None,
        }

        # Collect metrics
        metrics = ExecutionMetrics()

        # Execute graph with streaming to track progress
        result = None
        for event in self.graph.stream(initial_state):
            # event is a dict with node_name -> output
            for node_name, node_output in event.items():
                # Extract metrics from node output
                metrics_key = f"_metrics_{node_name}"
                if metrics_key in node_output:
                    step_metrics_data = node_output[metrics_key]
                    step_metrics = StepMetrics(
                        duration_ms=step_metrics_data.get("duration_ms", 0),
                        input_tokens=step_metrics_data.get("input_tokens", 0),
                        output_tokens=step_metrics_data.get("output_tokens", 0),
                    )
                    metrics.add_step(node_name, step_metrics)
                else:
                    step_metrics = None

                if on_progress and node_name in NODE_INFO:
                    info = NODE_INFO[node_name]

                    # Generate result preview based on node
                    preview = None
                    if node_name == "research" and node_output.get("market_research"):
                        research = node_output["market_research"]
                        preview = research[:200] + "..." if len(research) > 200 else research
                    elif node_name == "analysis" and node_output.get("analysis"):
                        analysis = node_output["analysis"]
                        preview = analysis[:200] + "..." if len(analysis) > 200 else analysis
                    elif node_name == "generate":
                        recs = node_output.get("recommendations")
                        if recs and recs.trades:
                            preview = f"Generated {len(recs.trades)} trade(s)"
                        elif node_output.get("error"):
                            preview = f"Error: {node_output['error'][:100]}"
                    elif node_name == "validate":
                        if node_output.get("error"):
                            preview = f"Validation failed: {node_output['error'][:100]}"
                        else:
                            preview = "Validation passed"

                    progress = StepProgress(
                        step=node_name,
                        label=info["label"],
                        description=info["description"],
                        icon=info["icon"],
                        status="completed",
                        result_preview=preview,
                        metrics=step_metrics,
                    )
                    on_progress(progress)

                # Keep track of latest state
                result = {**initial_state, **node_output} if result is None else {**result, **node_output}

        # If no streaming happened, fall back to invoke
        if result is None:
            result = self.graph.invoke(initial_state)

        # Extract metrics from final result (in case streaming didn't capture them)
        for node_name in ["research", "analysis", "generate", "validate"]:
            metrics_key = f"_metrics_{node_name}"
            if metrics_key in result and node_name not in metrics.steps:
                step_metrics_data = result[metrics_key]
                step_metrics = StepMetrics(
                    duration_ms=step_metrics_data.get("duration_ms", 0),
                    input_tokens=step_metrics_data.get("input_tokens", 0),
                    output_tokens=step_metrics_data.get("output_tokens", 0),
                )
                metrics.add_step(node_name, step_metrics)

        # Calculate total duration
        metrics.total_duration_ms = int((time.time() - start_time) * 1000)

        # Save log with metrics
        self._save_log(config.name, initial_state, result, metrics)

        # Store metrics on the recommendation for UI access
        self._last_metrics = metrics

        # Check for success
        if result.get("recommendations") is None:
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"Agent failed to generate recommendations: {error_msg}")

        return result["recommendations"], metrics
