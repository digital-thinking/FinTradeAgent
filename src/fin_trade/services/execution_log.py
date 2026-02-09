"""Execution log service for storing agent execution metrics in SQLite."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent.parent
_db_path = _project_root / "data" / "state" / "execution_logs.db"
_logs_dir = _project_root / "data" / "logs"
_state_dir = _project_root / "data" / "state"


@dataclass
class ExecutionLogEntry:
    """A single execution log entry."""

    id: int | None
    timestamp: datetime
    portfolio_name: str
    agent_mode: str
    model: str
    duration_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    num_trades: int
    success: bool
    error_message: str | None
    step_details: str  # JSON string of per-step metrics
    recommendations_json: str | None = None  # JSON string of trade recommendations
    executed_trades_json: str | None = None  # JSON string of executed trade indices
    rejected_trades_json: str | None = None  # JSON string of rejected trade indices


class ExecutionLogService:
    """Service for storing and retrieving execution logs."""

    def __init__(self):
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure the database and table exist."""
        _db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    portfolio_name TEXT NOT NULL,
                    agent_mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    num_trades INTEGER NOT NULL,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    step_details TEXT,
                    recommendations_json TEXT,
                    executed_trades_json TEXT,
                    rejected_trades_json TEXT
                )
            """)
            # Add new columns if they don't exist (migration for existing DBs)
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN recommendations_json TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN executed_trades_json TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute("ALTER TABLE execution_logs ADD COLUMN rejected_trades_json TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_notes (
                    id INTEGER PRIMARY KEY,
                    execution_id INTEGER,
                    portfolio_name TEXT NOT NULL,
                    note_date DATE NOT NULL,
                    note_text TEXT NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES execution_logs(id)
                )
            """)
            conn.commit()

    def log_execution(
        self,
        portfolio_name: str,
        agent_mode: str,
        model: str,
        duration_ms: int,
        input_tokens: int,
        output_tokens: int,
        num_trades: int,
        success: bool,
        error_message: str | None = None,
        step_details: dict | None = None,
        recommendations: list[dict] | None = None,
    ) -> int:
        """Log an execution to the database.

        Args:
            recommendations: List of trade recommendation dicts with keys:
                ticker, name, action, quantity, reasoning

        Returns:
            The ID of the inserted log entry.
        """
        import json

        step_details_json = json.dumps(step_details) if step_details else "{}"
        recommendations_json = json.dumps(recommendations) if recommendations else None

        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO execution_logs (
                    timestamp, portfolio_name, agent_mode, model,
                    duration_ms, input_tokens, output_tokens, total_tokens,
                    num_trades, success, error_message, step_details,
                    recommendations_json, executed_trades_json, rejected_trades_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    portfolio_name,
                    agent_mode,
                    model,
                    duration_ms,
                    input_tokens,
                    output_tokens,
                    input_tokens + output_tokens,
                    num_trades,
                    1 if success else 0,
                    error_message,
                    step_details_json,
                    recommendations_json,
                    None,  # executed_trades_json starts as None
                    None,  # rejected_trades_json starts as None
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def mark_trades_executed(self, log_id: int, executed_indices: list[int]) -> None:
        """Mark specific trades as executed for a log entry.

        Args:
            log_id: The execution log ID
            executed_indices: List of trade indices (0-based) that were executed
        """
        import json

        with sqlite3.connect(_db_path) as conn:
            conn.execute(
                "UPDATE execution_logs SET executed_trades_json = ? WHERE id = ?",
                (json.dumps(executed_indices), log_id),
            )
            conn.commit()

    def mark_trades_rejected(self, log_id: int, rejected_indices: list[int]) -> None:
        """Mark specific trades as rejected for a log entry.

        Args:
            log_id: The execution log ID
            rejected_indices: List of trade indices (0-based) that were rejected
        """
        import json

        with sqlite3.connect(_db_path) as conn:
            conn.execute(
                "UPDATE execution_logs SET rejected_trades_json = ? WHERE id = ?",
                (json.dumps(rejected_indices), log_id),
            )
            conn.commit()

    def get_log_by_id(self, log_id: int) -> ExecutionLogEntry | None:
        """Get a single execution log by ID."""
        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, portfolio_name, agent_mode, model,
                       duration_ms, input_tokens, output_tokens, total_tokens,
                       num_trades, success, error_message, step_details,
                       recommendations_json, executed_trades_json, rejected_trades_json
                FROM execution_logs
                WHERE id = ?
                """,
                (log_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return ExecutionLogEntry(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            portfolio_name=row[2],
            agent_mode=row[3],
            model=row[4],
            duration_ms=row[5],
            input_tokens=row[6],
            output_tokens=row[7],
            total_tokens=row[8],
            num_trades=row[9],
            success=bool(row[10]),
            error_message=row[11],
            step_details=row[12],
            recommendations_json=row[13],
            executed_trades_json=row[14],
            rejected_trades_json=row[15],
        )

    def get_execution_with_context(self, execution_id: int) -> dict:
        """Get execution record with recommendations, outcomes, and log context."""
        import json

        log = self.get_log_by_id(execution_id)
        if log is None:
            raise ValueError(f"Execution log not found: {execution_id}")

        recommendations = []
        if log.recommendations_json:
            recommendations = json.loads(log.recommendations_json)

        executed_indices = []
        if log.executed_trades_json:
            executed_indices = json.loads(log.executed_trades_json)

        rejected_indices = []
        if log.rejected_trades_json:
            rejected_indices = json.loads(log.rejected_trades_json)

        pending_indices = [
            i for i in range(len(recommendations))
            if i not in executed_indices and i not in rejected_indices
        ]

        portfolio_state = self._load_portfolio_state_at(
            log.portfolio_name,
            log.timestamp,
        )

        log_context = self._parse_log_context(log)

        return {
            "log": log,
            "recommendations": recommendations,
            "executed_indices": executed_indices,
            "rejected_indices": rejected_indices,
            "pending_indices": pending_indices,
            "portfolio_state": portfolio_state,
            "log_context": log_context,
        }

    def get_recommendation_outcomes(self, execution_id: int) -> list[dict]:
        """Calculate price outcomes for recommendations in an execution."""
        import json
        from fin_trade.services.stock_data import StockDataService
        from fin_trade.models import Trade

        log = self.get_log_by_id(execution_id)
        if log is None:
            raise ValueError(f"Execution log not found: {execution_id}")
        if not log.recommendations_json:
            return []

        recommendations = json.loads(log.recommendations_json)

        executed_indices = []
        if log.executed_trades_json:
            executed_indices = json.loads(log.executed_trades_json)

        rejected_indices = []
        if log.rejected_trades_json:
            rejected_indices = json.loads(log.rejected_trades_json)

        trades = []
        state_path = _state_dir / f"{log.portfolio_name}.json"
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            for t in state_data.get("trades", []):
                trades.append(
                    Trade(
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                        ticker=t.get("ticker", t.get("isin", "UNKNOWN")),
                        name=t.get("name", t.get("ticker", "Unknown")),
                        action=t["action"],
                        quantity=float(t["quantity"]),
                        price=float(t["price"]),
                        reasoning=t.get("reasoning", ""),
                        stop_loss_price=t.get("stop_loss_price"),
                        take_profit_price=t.get("take_profit_price"),
                    )
                )
        trades = sorted(trades, key=lambda t: t.timestamp)

        stock_data_service = StockDataService()
        outcomes = []

        for idx, rec in enumerate(recommendations):
            ticker = rec.get("ticker")
            action = rec.get("action")
            rec_quantity = float(rec.get("quantity", 0))

            status = "pending"
            if idx in executed_indices:
                status = "applied"
            elif idx in rejected_indices:
                status = "rejected"

            rec_price = self._get_price_at_time(
                stock_data_service,
                ticker,
                log.timestamp,
            )

            current_price = None
            try:
                current_price = stock_data_service.get_price(ticker)
            except Exception:
                current_price = None

            exit_price = self._get_exit_price(
                trades,
                ticker,
                log.timestamp,
                rec_quantity,
            )

            price_for_outcome = exit_price if exit_price is not None else current_price

            hypothetical_pl = None
            hypothetical_pl_pct = None
            if rec_price is not None and price_for_outcome is not None and rec_quantity:
                if action == "BUY":
                    hypothetical_pl = (price_for_outcome - rec_price) * rec_quantity
                else:
                    hypothetical_pl = (rec_price - price_for_outcome) * rec_quantity
                hypothetical_pl_pct = (hypothetical_pl / (rec_price * rec_quantity)) * 100

            actual_execution_price = None
            actual_quantity = None
            actual_pl = None
            actual_pl_pct = None

            if status == "applied":
                actual_trade = self._find_actual_trade(
                    trades,
                    ticker,
                    action,
                    log.timestamp,
                )
                if actual_trade:
                    actual_execution_price = actual_trade.price
                    actual_quantity = actual_trade.quantity
                    if price_for_outcome is not None and actual_quantity:
                        if action == "BUY":
                            actual_pl = (price_for_outcome - actual_execution_price) * actual_quantity
                        else:
                            actual_pl = (actual_execution_price - price_for_outcome) * actual_quantity
                        actual_pl_pct = (
                            (actual_pl / (actual_execution_price * actual_quantity)) * 100
                        )

            outcomes.append({
                "index": idx,
                "ticker": ticker,
                "action": action,
                "recommended_quantity": rec_quantity,
                "recommended_price": rec_price,
                "current_price": current_price,
                "exit_price": exit_price,
                "status": status,
                "hypothetical_pl": hypothetical_pl,
                "hypothetical_pl_pct": hypothetical_pl_pct,
                "actual_execution_price": actual_execution_price,
                "actual_quantity": actual_quantity,
                "actual_pl": actual_pl,
                "actual_pl_pct": actual_pl_pct,
            })

        return outcomes

    def add_note(
        self,
        portfolio_name: str,
        note_text: str,
        execution_id: int | None = None,
        note_date: date | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """Add a note to an execution or date."""
        import json

        if not note_text or not note_text.strip():
            raise ValueError("Note text cannot be empty")

        if execution_id is not None and note_date is None:
            log = self.get_log_by_id(execution_id)
            if log is None:
                raise ValueError(f"Execution log not found: {execution_id}")
            note_date = log.timestamp.date()

        if note_date is None:
            note_date = date.today()

        tags_json = json.dumps(tags) if tags else None

        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO execution_notes (
                    execution_id, portfolio_name, note_date, note_text, tags
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    portfolio_name,
                    note_date.isoformat(),
                    note_text.strip(),
                    tags_json,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_notes(
        self,
        portfolio_name: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Get notes for a portfolio, optionally filtered by date range."""
        import json

        conditions = ["portfolio_name = ?"]
        params: list = [portfolio_name]

        if start_date:
            conditions.append("note_date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("note_date <= ?")
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions)

        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                f"""
                SELECT id, execution_id, portfolio_name, note_date, note_text, tags, created_at
                FROM execution_notes
                WHERE {where_clause}
                ORDER BY note_date DESC, created_at DESC
                """,
                params,
            )
            rows = cursor.fetchall()

        notes = []
        for row in rows:
            tags = json.loads(row[5]) if row[5] else []
            notes.append({
                "id": row[0],
                "execution_id": row[1],
                "portfolio_name": row[2],
                "note_date": date.fromisoformat(row[3]),
                "note_text": row[4],
                "tags": tags,
                "created_at": row[6],
            })
        return notes

    def update_note(
        self,
        note_id: int,
        note_text: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Update an existing note."""
        import json

        if note_text is None and tags is None:
            raise ValueError("Must provide note_text or tags to update")

        updates = []
        params: list = []

        if note_text is not None:
            if not note_text.strip():
                raise ValueError("Note text cannot be empty")
            updates.append("note_text = ?")
            params.append(note_text.strip())

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags) if tags else None)

        params.append(note_id)
        update_clause = ", ".join(updates)

        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                f"UPDATE execution_notes SET {update_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"Note not found: {note_id}")

    def delete_note(self, note_id: int) -> None:
        """Delete a note."""
        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM execution_notes WHERE id = ?",
                (note_id,),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"Note not found: {note_id}")

    def get_logs(
        self,
        portfolio_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionLogEntry]:
        """Get execution logs, optionally filtered by portfolio."""

        with sqlite3.connect(_db_path) as conn:
            if portfolio_name:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, portfolio_name, agent_mode, model,
                           duration_ms, input_tokens, output_tokens, total_tokens,
                           num_trades, success, error_message, step_details,
                           recommendations_json, executed_trades_json, rejected_trades_json
                    FROM execution_logs
                    WHERE portfolio_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (portfolio_name, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, portfolio_name, agent_mode, model,
                           duration_ms, input_tokens, output_tokens, total_tokens,
                           num_trades, success, error_message, step_details,
                           recommendations_json, executed_trades_json, rejected_trades_json
                    FROM execution_logs
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            rows = cursor.fetchall()

        return [
            ExecutionLogEntry(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                portfolio_name=row[2],
                agent_mode=row[3],
                model=row[4],
                duration_ms=row[5],
                input_tokens=row[6],
                output_tokens=row[7],
                total_tokens=row[8],
                num_trades=row[9],
                success=bool(row[10]),
                error_message=row[11],
                step_details=row[12],
                recommendations_json=row[13],
                executed_trades_json=row[14],
                rejected_trades_json=row[15],
            )
            for row in rows
        ]

    def get_summary_stats(self, days: int = 30) -> dict:
        """Get summary statistics for the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with sqlite3.connect(_db_path) as conn:
            # Total executions
            cursor = conn.execute(
                "SELECT COUNT(*) FROM execution_logs WHERE timestamp >= ?",
                (cutoff,),
            )
            total_executions = cursor.fetchone()[0]

            # Success rate
            cursor = conn.execute(
                "SELECT COUNT(*) FROM execution_logs WHERE timestamp >= ? AND success = 1",
                (cutoff,),
            )
            successful = cursor.fetchone()[0]

            # Total tokens
            cursor = conn.execute(
                "SELECT SUM(total_tokens) FROM execution_logs WHERE timestamp >= ?",
                (cutoff,),
            )
            total_tokens = cursor.fetchone()[0] or 0

            # Average duration
            cursor = conn.execute(
                "SELECT AVG(duration_ms) FROM execution_logs WHERE timestamp >= ?",
                (cutoff,),
            )
            avg_duration = cursor.fetchone()[0] or 0

            # Total trades
            cursor = conn.execute(
                "SELECT SUM(num_trades) FROM execution_logs WHERE timestamp >= ?",
                (cutoff,),
            )
            total_trades = cursor.fetchone()[0] or 0

            # By portfolio
            cursor = conn.execute(
                """
                SELECT portfolio_name, COUNT(*), SUM(total_tokens), AVG(duration_ms)
                FROM execution_logs
                WHERE timestamp >= ?
                GROUP BY portfolio_name
                ORDER BY COUNT(*) DESC
                """,
                (cutoff,),
            )
            by_portfolio = [
                {
                    "portfolio": row[0],
                    "executions": row[1],
                    "tokens": row[2] or 0,
                    "avg_duration_ms": row[3] or 0,
                }
                for row in cursor.fetchall()
            ]

            # By agent mode
            cursor = conn.execute(
                """
                SELECT agent_mode, COUNT(*), SUM(total_tokens), AVG(duration_ms)
                FROM execution_logs
                WHERE timestamp >= ?
                GROUP BY agent_mode
                ORDER BY COUNT(*) DESC
                """,
                (cutoff,),
            )
            by_agent_mode = [
                {
                    "mode": row[0],
                    "executions": row[1],
                    "tokens": row[2] or 0,
                    "avg_duration_ms": row[3] or 0,
                }
                for row in cursor.fetchall()
            ]

        return {
            "total_executions": total_executions,
            "successful_executions": successful,
            "success_rate": (successful / total_executions * 100) if total_executions > 0 else 0,
            "total_tokens": total_tokens,
            "avg_duration_ms": avg_duration,
            "total_trades": total_trades,
            "by_portfolio": by_portfolio,
            "by_agent_mode": by_agent_mode,
        }

    def get_daily_stats(self, days: int = 14) -> list[dict]:
        """Get daily aggregated stats for charting."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with sqlite3.connect(_db_path) as conn:
            cursor = conn.execute(
                """
                SELECT DATE(timestamp) as day,
                       COUNT(*) as executions,
                       SUM(total_tokens) as tokens,
                       AVG(duration_ms) as avg_duration,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM execution_logs
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY day ASC
                """,
                (cutoff,),
            )
            return [
                {
                    "date": row[0],
                    "executions": row[1],
                    "tokens": row[2] or 0,
                    "avg_duration_ms": row[3] or 0,
                    "successes": row[4],
                }
                for row in cursor.fetchall()
            ]

    def _load_portfolio_state_at(self, portfolio_name: str, as_of: datetime) -> dict:
        """Load portfolio state at a specific timestamp by replaying trades."""
        import json
        from fin_trade.services.portfolio import PortfolioService

        state_path = _state_dir / f"{portfolio_name}.json"
        if not state_path.exists():
            return {"cash": None, "holdings": [], "trades": []}

        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        portfolio_service = PortfolioService(state_dir=_state_dir)
        try:
            config, _ = portfolio_service.load_portfolio(portfolio_name)
            start_cash = float(data.get("initial_investment") or config.initial_amount)
        except Exception:
            start_cash = float(data.get("initial_investment") or data.get("cash", 0))

        holdings = {}
        cash = start_cash
        trades = []

        trade_records = data.get("trades", [])
        for t in trade_records:
            trade_time = datetime.fromisoformat(t["timestamp"])
            if trade_time > as_of:
                continue

            action = t["action"]
            quantity = float(t["quantity"])
            price = float(t["price"])
            ticker = t.get("ticker", t.get("isin", "UNKNOWN"))
            name = t.get("name", ticker)

            trade_cost = price * quantity

            if action == "BUY":
                cash -= trade_cost
                if ticker in holdings:
                    existing = holdings[ticker]
                    total_qty = existing["quantity"] + quantity
                    avg_price = (
                        existing["avg_price"] * existing["quantity"] + trade_cost
                    ) / total_qty
                    holdings[ticker] = {
                        "ticker": ticker,
                        "name": name,
                        "quantity": total_qty,
                        "avg_price": avg_price,
                    }
                else:
                    holdings[ticker] = {
                        "ticker": ticker,
                        "name": name,
                        "quantity": quantity,
                        "avg_price": price,
                    }
            else:
                cash += trade_cost
                if ticker in holdings:
                    holdings[ticker]["quantity"] -= quantity
                    if holdings[ticker]["quantity"] <= 0:
                        del holdings[ticker]

            trades.append({
                "timestamp": trade_time,
                "ticker": ticker,
                "name": name,
                "action": action,
                "quantity": quantity,
                "price": price,
                "reasoning": t.get("reasoning", ""),
            })

        return {
            "cash": cash,
            "holdings": list(holdings.values()),
            "trades": trades,
        }

    def _find_log_file(self, log: ExecutionLogEntry) -> Path | None:
        """Find the markdown log file for an execution entry."""
        if not _logs_dir.exists():
            return None

        suffix = ""
        if log.agent_mode == "langgraph":
            suffix = "_langgraph"
        elif log.agent_mode == "debate":
            suffix = "_debate"

        candidates = list(_logs_dir.glob(f"{log.portfolio_name}_*{suffix}.md"))
        if not candidates:
            return None

        best_match = None
        best_delta = None

        for candidate in candidates:
            timestamp = self._extract_log_timestamp(candidate.stem, log.portfolio_name, suffix)
            if timestamp is None:
                continue
            delta = abs((timestamp - log.timestamp).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_match = candidate

        return best_match

    def _extract_log_timestamp(
        self,
        stem: str,
        portfolio_name: str,
        suffix: str,
    ) -> datetime | None:
        """Extract timestamp from a log filename stem."""
        prefix = f"{portfolio_name}_"
        if not stem.startswith(prefix):
            return None
        timestamp_part = stem[len(prefix):]
        if suffix and timestamp_part.endswith(suffix):
            timestamp_part = timestamp_part[: -len(suffix)]
        timestamp_part = timestamp_part.strip("_")
        try:
            return datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    def _parse_log_context(self, log: ExecutionLogEntry) -> dict:
        """Parse markdown log file for research, analysis, and debate sections."""
        log_file = self._find_log_file(log)
        if log_file is None or not log_file.exists():
            return {"error": "Log file not found"}

        try:
            content = log_file.read_text(encoding="utf-8")
        except Exception as exc:
            return {"error": f"Failed to read log file: {exc}"}

        sections = self._parse_markdown_sections(content)

        return {
            "prompt": sections.get("Prompt") or sections.get("Prompts Sent to Agent"),
            "response": sections.get("Response"),
            "research": sections.get("Market Research") or sections.get("Research"),
            "analysis": sections.get("Analysis"),
            "bull_case": sections.get("Bull Case"),
            "bear_case": sections.get("Bear Case"),
            "neutral_analysis": sections.get("Neutral Analysis"),
            "debate": sections.get("Debate Rounds"),
            "moderator_verdict": sections.get("Moderator Verdict"),
            "overall_reasoning": sections.get("Overall Reasoning"),
        }

    def _parse_markdown_sections(self, content: str) -> dict:
        """Parse top-level markdown sections into a dictionary."""
        sections: dict[str, list[str]] = {}
        current_section = None

        for line in content.splitlines():
            if line.startswith("## "):
                current_section = line[3:].strip()
                sections[current_section] = []
                continue
            if current_section is not None:
                sections[current_section].append(line)

        return {
            name: "\n".join(lines).strip()
            for name, lines in sections.items()
        }

    def _get_price_at_time(
        self,
        stock_data_service,
        ticker: str,
        target_time: datetime,
    ) -> float | None:
        """Get price closest to a specific time from history."""
        import pandas as pd

        if not ticker:
            return None

        days = max(5, (datetime.now() - target_time).days + 5)
        try:
            history = stock_data_service.get_history(ticker, days=days)
        except Exception:
            return None

        if history is None or history.empty:
            return None

        if not isinstance(history.index, pd.DatetimeIndex):
            history.index = pd.to_datetime(history.index)

        history = history.sort_index()
        history = history[history.index <= target_time]
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])

    def _get_exit_price(
        self,
        trades: list,
        ticker: str,
        after_time: datetime,
        quantity: float,
    ) -> float | None:
        """Get weighted exit price for a quantity if later sells occurred."""
        if not ticker or quantity <= 0:
            return None

        remaining = quantity
        total_proceeds = 0.0

        for trade in trades:
            if trade.ticker != ticker:
                continue
            if trade.timestamp <= after_time:
                continue
            if trade.action != "SELL":
                continue

            sell_qty = min(trade.quantity, remaining)
            total_proceeds += sell_qty * trade.price
            remaining -= sell_qty
            if remaining <= 0:
                break

        if remaining > 0:
            return None
        return total_proceeds / quantity

    def _find_actual_trade(
        self,
        trades: list,
        ticker: str,
        action: str,
        after_time: datetime,
    ):
        """Find the first matching trade after a timestamp."""
        for trade in trades:
            if trade.timestamp <= after_time:
                continue
            if trade.ticker != ticker:
                continue
            if trade.action != action:
                continue
            return trade
        return None
