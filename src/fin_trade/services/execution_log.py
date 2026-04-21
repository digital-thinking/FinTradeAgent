"""Execution log service for storing agent execution metrics in SQLite."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent.parent
_db_path = _project_root / "data" / "state" / "execution_logs.db"


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
