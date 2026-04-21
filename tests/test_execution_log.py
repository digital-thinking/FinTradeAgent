"""Tests for ExecutionLogService."""

import json
import sqlite3
from datetime import datetime, timedelta, date
import pytest
import pandas as pd

from fin_trade.services.execution_log import ExecutionLogService, ExecutionLogEntry


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_execution_logs.db"
    monkeypatch.setattr(
        "fin_trade.services.execution_log._db_path", db_path
    )
    return db_path


@pytest.fixture
def temp_dirs(tmp_path, monkeypatch):
    """Create temporary logs and state directories."""
    logs_dir = tmp_path / "logs"
    state_dir = tmp_path / "state"
    logs_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("fin_trade.services.execution_log._logs_dir", logs_dir)
    monkeypatch.setattr("fin_trade.services.execution_log._state_dir", state_dir)
    return logs_dir, state_dir


class TestExecutionLogServiceInit:
    """Tests for ExecutionLogService initialization."""

    def test_creates_database_and_table(self, temp_db):
        """Test creates database file and table on init."""
        assert not temp_db.exists()

        ExecutionLogService()

        assert temp_db.exists()

        # Verify table exists
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_logs'"
            )
            assert cursor.fetchone() is not None
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_notes'"
            )
            assert cursor.fetchone() is not None

    def test_creates_parent_directory(self, tmp_path, monkeypatch):
        """Test creates parent directories if needed."""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        monkeypatch.setattr("fin_trade.services.execution_log._db_path", db_path)

        ExecutionLogService()

        assert db_path.parent.exists()


class TestLogExecution:
    """Tests for log_execution method."""

    def test_inserts_log_entry(self, temp_db):
        """Test inserts a log entry into the database."""
        service = ExecutionLogService()

        log_id = service.log_execution(
            portfolio_name="Test Portfolio",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=5000,
            input_tokens=1000,
            output_tokens=500,
            num_trades=3,
            success=True,
        )

        assert log_id is not None
        assert log_id > 0

        # Verify entry exists
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT portfolio_name, agent_mode, success FROM execution_logs WHERE id = ?",
                (log_id,),
            )
            row = cursor.fetchone()
            assert row[0] == "Test Portfolio"
            assert row[1] == "langgraph"
            assert row[2] == 1  # True as integer

    def test_calculates_total_tokens(self, temp_db):
        """Test calculates total_tokens from input + output."""
        service = ExecutionLogService()

        log_id = service.log_execution(
            portfolio_name="Test",
            agent_mode="simple",
            model="gpt-4o",
            duration_ms=1000,
            input_tokens=2000,
            output_tokens=500,
            num_trades=1,
            success=True,
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT total_tokens FROM execution_logs WHERE id = ?",
                (log_id,),
            )
            assert cursor.fetchone()[0] == 2500

    def test_stores_error_message(self, temp_db):
        """Test stores error message for failed executions."""
        service = ExecutionLogService()

        log_id = service.log_execution(
            portfolio_name="Test",
            agent_mode="debate",
            model="claude-3",
            duration_ms=2000,
            input_tokens=500,
            output_tokens=0,
            num_trades=0,
            success=False,
            error_message="API rate limit exceeded",
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT success, error_message FROM execution_logs WHERE id = ?",
                (log_id,),
            )
            row = cursor.fetchone()
            assert row[0] == 0  # False
            assert row[1] == "API rate limit exceeded"

    def test_stores_step_details_as_json(self, temp_db):
        """Test stores step_details as JSON string."""
        service = ExecutionLogService()

        step_details = {
            "research": {"duration_ms": 1000, "tokens": 500},
            "generate": {"duration_ms": 2000, "tokens": 1000},
        }

        log_id = service.log_execution(
            portfolio_name="Test",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=3000,
            input_tokens=1500,
            output_tokens=500,
            num_trades=2,
            success=True,
            step_details=step_details,
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT step_details FROM execution_logs WHERE id = ?",
                (log_id,),
            )
            stored_json = cursor.fetchone()[0]
            parsed = json.loads(stored_json)
            assert parsed["research"]["duration_ms"] == 1000


class TestGetLogs:
    """Tests for get_logs method."""

    def test_returns_all_logs(self, temp_db):
        """Test returns all logs when no filter specified."""
        service = ExecutionLogService()

        # Insert multiple logs
        service.log_execution("Portfolio A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Portfolio B", "debate", "claude-3", 2000, 200, 100, 2, True)

        logs = service.get_logs()

        assert len(logs) == 2

    def test_filters_by_portfolio_name(self, temp_db):
        """Test filters logs by portfolio name."""
        service = ExecutionLogService()

        service.log_execution("Portfolio A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Portfolio A", "simple", "gpt-4o", 1500, 150, 75, 2, True)
        service.log_execution("Portfolio B", "debate", "claude-3", 2000, 200, 100, 2, True)

        logs = service.get_logs(portfolio_name="Portfolio A")

        assert len(logs) == 2
        assert all(log.portfolio_name == "Portfolio A" for log in logs)

    def test_respects_limit(self, temp_db):
        """Test respects limit parameter."""
        service = ExecutionLogService()

        for i in range(10):
            service.log_execution(f"Portfolio {i}", "simple", "gpt-4o", 1000, 100, 50, 1, True)

        logs = service.get_logs(limit=5)

        assert len(logs) == 5

    def test_respects_offset(self, temp_db):
        """Test respects offset parameter."""
        service = ExecutionLogService()

        for i in range(5):
            service.log_execution(f"Portfolio {i}", "simple", "gpt-4o", 1000, 100, 50, 1, True)

        all_logs = service.get_logs()
        offset_logs = service.get_logs(offset=2)

        assert len(offset_logs) == 3
        assert offset_logs[0].id == all_logs[2].id

    def test_returns_execution_log_entries(self, temp_db):
        """Test returns proper ExecutionLogEntry objects."""
        service = ExecutionLogService()

        service.log_execution(
            portfolio_name="Test",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=5000,
            input_tokens=1000,
            output_tokens=500,
            num_trades=3,
            success=True,
            step_details={"test": "data"},
        )

        logs = service.get_logs()

        assert len(logs) == 1
        log = logs[0]
        assert isinstance(log, ExecutionLogEntry)
        assert log.portfolio_name == "Test"
        assert log.agent_mode == "langgraph"
        assert log.model == "gpt-4o"
        assert log.duration_ms == 5000
        assert log.total_tokens == 1500
        assert log.success is True
        assert isinstance(log.timestamp, datetime)

    def test_orders_by_timestamp_descending(self, temp_db):
        """Test orders logs by timestamp descending (newest first)."""
        service = ExecutionLogService()

        service.log_execution("First", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Second", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Third", "simple", "gpt-4o", 1000, 100, 50, 1, True)

        logs = service.get_logs()

        assert logs[0].portfolio_name == "Third"
        assert logs[2].portfolio_name == "First"


class TestGetSummaryStats:
    """Tests for get_summary_stats method."""

    def test_returns_correct_totals(self, temp_db):
        """Test returns correct total statistics."""
        service = ExecutionLogService()

        service.log_execution("A", "simple", "gpt-4o", 1000, 100, 50, 2, True)
        service.log_execution("B", "debate", "claude-3", 2000, 200, 100, 3, True)
        service.log_execution("C", "simple", "gpt-4o", 1500, 150, 50, 1, False, "Error")

        stats = service.get_summary_stats(days=30)

        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert stats["total_tokens"] == 650  # 150 + 300 + 200
        assert stats["total_trades"] == 6

    def test_calculates_success_rate(self, temp_db):
        """Test calculates success rate correctly."""
        service = ExecutionLogService()

        service.log_execution("A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("B", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("C", "simple", "gpt-4o", 1000, 100, 50, 0, False)
        service.log_execution("D", "simple", "gpt-4o", 1000, 100, 50, 0, False)

        stats = service.get_summary_stats()

        assert stats["success_rate"] == 50.0

    def test_groups_by_portfolio(self, temp_db):
        """Test groups statistics by portfolio."""
        service = ExecutionLogService()

        service.log_execution("Portfolio A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Portfolio A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("Portfolio B", "simple", "gpt-4o", 1000, 100, 50, 1, True)

        stats = service.get_summary_stats()

        assert len(stats["by_portfolio"]) == 2
        portfolio_a = next(p for p in stats["by_portfolio"] if p["portfolio"] == "Portfolio A")
        assert portfolio_a["executions"] == 2

    def test_groups_by_agent_mode(self, temp_db):
        """Test groups statistics by agent mode."""
        service = ExecutionLogService()

        service.log_execution("A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("B", "debate", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("C", "debate", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("D", "langgraph", "gpt-4o", 1000, 100, 50, 1, True)

        stats = service.get_summary_stats()

        debate_mode = next(m for m in stats["by_agent_mode"] if m["mode"] == "debate")
        assert debate_mode["executions"] == 2

    def test_handles_empty_database(self, temp_db):
        """Test handles empty database gracefully."""
        service = ExecutionLogService()

        stats = service.get_summary_stats()

        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0
        assert stats["total_tokens"] == 0


class TestGetDailyStats:
    """Tests for get_daily_stats method."""

    def test_returns_daily_aggregates(self, temp_db):
        """Test returns daily aggregated statistics."""
        service = ExecutionLogService()

        # Add some executions
        service.log_execution("A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("B", "simple", "gpt-4o", 2000, 200, 100, 2, True)

        stats = service.get_daily_stats(days=7)

        assert len(stats) >= 1
        today_stats = stats[-1]
        assert "date" in today_stats
        assert today_stats["executions"] == 2
        assert today_stats["tokens"] == 450

    def test_counts_successes(self, temp_db):
        """Test counts successful executions per day."""
        service = ExecutionLogService()

        service.log_execution("A", "simple", "gpt-4o", 1000, 100, 50, 1, True)
        service.log_execution("B", "simple", "gpt-4o", 1000, 100, 50, 1, False)
        service.log_execution("C", "simple", "gpt-4o", 1000, 100, 50, 1, True)

        stats = service.get_daily_stats(days=7)

        today_stats = stats[-1]
        assert today_stats["successes"] == 2

    def test_handles_no_data(self, temp_db):
        """Test handles no data in time range."""
        service = ExecutionLogService()

        stats = service.get_daily_stats(days=7)

        assert stats == []


class TestExecutionContext:
    """Tests for execution context and outcomes."""

    def test_get_execution_with_context_parses_log(self, temp_db, temp_dirs):
        logs_dir, state_dir = temp_dirs
        service = ExecutionLogService()

        log_time = datetime(2025, 1, 2, 3, 4, 5)
        log_id = service.log_execution(
            portfolio_name="TestPortfolio",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=1000,
            input_tokens=100,
            output_tokens=50,
            num_trades=1,
            success=True,
            recommendations=[{
                "ticker": "AAPL",
                "name": "Apple",
                "action": "BUY",
                "quantity": 1,
                "reasoning": "Test",
            }],
        )

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "UPDATE execution_logs SET timestamp = ? WHERE id = ?",
                (log_time.isoformat(), log_id),
            )
            conn.commit()

        log_file = logs_dir / "TestPortfolio_20250102_030405_langgraph.md"
        log_file.write_text(
            """# LangGraph Agent Log - 2025-01-02T03:04:05

## Market Research

Research content here.

## Analysis

Analysis content here.
""",
            encoding="utf-8",
        )

        state_path = state_dir / "TestPortfolio.json"
        state_path.write_text(
            json.dumps({
                "cash": 10000,
                "initial_investment": 10000,
                "holdings": [],
                "trades": [
                    {
                        "timestamp": "2025-01-01T10:00:00",
                        "ticker": "AAPL",
                        "name": "Apple",
                        "action": "BUY",
                        "quantity": 1,
                        "price": 100,
                        "reasoning": "Initial buy",
                    }
                ],
            }),
            encoding="utf-8",
        )

        context = service.get_execution_with_context(log_id)
        assert context["recommendations"][0]["ticker"] == "AAPL"
        assert context["log_context"]["research"] == "Research content here."
        assert context["log_context"]["analysis"] == "Analysis content here."
        assert context["portfolio_state"]["holdings"][0]["ticker"] == "AAPL"

    def test_get_recommendation_outcomes(self, temp_db, temp_dirs, monkeypatch):
        _, state_dir = temp_dirs

        service = ExecutionLogService()

        log_time = datetime(2025, 1, 2, 3, 4, 5)
        log_id = service.log_execution(
            portfolio_name="TestPortfolio",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=1000,
            input_tokens=100,
            output_tokens=50,
            num_trades=1,
            success=True,
            recommendations=[{
                "ticker": "AAPL",
                "name": "Apple",
                "action": "BUY",
                "quantity": 10,
                "reasoning": "Test",
            }],
        )

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "UPDATE execution_logs SET timestamp = ? WHERE id = ?",
                (log_time.isoformat(), log_id),
            )
            conn.commit()

        service.mark_trades_executed(log_id, [0])

        state_path = state_dir / "TestPortfolio.json"
        state_path.write_text(
            json.dumps({
                "cash": 9000,
                "initial_investment": 10000,
                "holdings": [],
                "trades": [
                    {
                        "timestamp": "2025-01-02T03:05:00",
                        "ticker": "AAPL",
                        "name": "Apple",
                        "action": "BUY",
                        "quantity": 10,
                        "price": 100,
                        "reasoning": "Executed",
                    },
                    {
                        "timestamp": "2025-01-05T10:00:00",
                        "ticker": "AAPL",
                        "name": "Apple",
                        "action": "SELL",
                        "quantity": 10,
                        "price": 120,
                        "reasoning": "Exit",
                    },
                ],
            }),
            encoding="utf-8",
        )

        def fake_history(self, ticker, days=365):
            dates = pd.to_datetime([
                "2025-01-01",
                "2025-01-02",
            ])
            return pd.DataFrame({"Close": [95, 105]}, index=dates)

        def fake_price(self, ticker):
            return 130.0

        monkeypatch.setattr(
            "fin_trade.services.stock_data.StockDataService.get_history", fake_history
        )
        monkeypatch.setattr(
            "fin_trade.services.stock_data.StockDataService.get_price", fake_price
        )

        outcomes = service.get_recommendation_outcomes(log_id)
        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome["recommended_price"] == 105.0
        assert outcome["exit_price"] == 120.0
        assert outcome["hypothetical_pl"] == 150.0
        assert outcome["actual_pl"] == 200.0


class TestExecutionNotes:
    """Tests for execution note CRUD."""

    def test_add_get_update_delete_note(self, temp_db):
        service = ExecutionLogService()

        note_id = service.add_note(
            portfolio_name="TestPortfolio",
            note_text="Initial note",
            note_date=date(2025, 1, 1),
            tags=["Earnings"],
        )

        notes = service.get_notes("TestPortfolio")
        assert len(notes) == 1
        assert notes[0]["id"] == note_id
        assert notes[0]["tags"] == ["Earnings"]

        service.update_note(note_id, note_text="Updated note", tags=["Fed Decision"])
        updated = service.get_notes("TestPortfolio")[0]
        assert updated["note_text"] == "Updated note"
        assert updated["tags"] == ["Fed Decision"]

        service.delete_note(note_id)
        assert service.get_notes("TestPortfolio") == []

    def test_add_note_with_execution_id_uses_execution_date(self, temp_db):
        service = ExecutionLogService()

        log_id = service.log_execution(
            portfolio_name="TestPortfolio",
            agent_mode="langgraph",
            model="gpt-4o",
            duration_ms=1000,
            input_tokens=100,
            output_tokens=50,
            num_trades=0,
            success=True,
        )

        execution_time = datetime(2025, 2, 3, 10, 0, 0)
        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "UPDATE execution_logs SET timestamp = ? WHERE id = ?",
                (execution_time.isoformat(), log_id),
            )
            conn.commit()

        note_id = service.add_note(
            portfolio_name="TestPortfolio",
            note_text="Execution note",
            execution_id=log_id,
        )

        notes = service.get_notes("TestPortfolio")
        assert notes[0]["id"] == note_id
        assert notes[0]["note_date"] == date(2025, 2, 3)
