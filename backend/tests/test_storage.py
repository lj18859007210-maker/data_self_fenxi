"""Tests for SQLite persistent storage."""

import pytest
from datetime import datetime
from app.models.session import Session, SessionState, FieldInfo, FieldType
from app.services import storage
from app.config import DB_PATH


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure DB is initialized and clean before each test."""
    storage.init_db()
    # Clean all tables
    conn = storage.get_conn()
    conn.execute("DELETE FROM analysis_progress")
    conn.execute("DELETE FROM analysis_results")
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()
    yield
    # Cleanup after test
    conn = storage.get_conn()
    conn.execute("DELETE FROM analysis_progress")
    conn.execute("DELETE FROM analysis_results")
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()


class TestSessionStorage:
    def test_save_and_get_session(self):
        session = Session(
            id="test-1",
            filename="test.csv",
            file_path="/tmp/test.csv",
            file_size=100,
            row_count=10,
            column_count=3,
            fields=[
                FieldInfo(name="col1", inferred_type=FieldType.NUMERIC, display_type=FieldType.NUMERIC),
            ],
            state=SessionState.UPLOADED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        storage.save_session(session)
        retrieved = storage.get_session("test-1")
        assert retrieved is not None
        assert retrieved.id == "test-1"
        assert retrieved.filename == "test.csv"
        assert retrieved.row_count == 10
        assert retrieved.column_count == 3
        assert len(retrieved.fields) == 1
        assert retrieved.fields[0].name == "col1"
        assert retrieved.state == SessionState.UPLOADED

    def test_get_session_not_found(self):
        assert storage.get_session("nonexistent") is None

    def test_list_sessions(self):
        s1 = Session(id="s1", filename="a.csv", file_path="/tmp/a.csv", file_size=10)
        s2 = Session(id="s2", filename="b.csv", file_path="/tmp/b.csv", file_size=20)
        storage.save_session(s1)
        storage.save_session(s2)
        sessions = storage.list_sessions()
        assert len(sessions) >= 2
        ids = [s["id"] for s in sessions]
        assert "s1" in ids
        assert "s2" in ids

    def test_delete_session(self):
        session = Session(id="del-test", filename="d.csv", file_path="/tmp/d.csv", file_size=1)
        storage.save_session(session)
        assert storage.get_session("del-test") is not None
        storage.delete_session("del-test")
        assert storage.get_session("del-test") is None


class TestAnalysisResults:
    def test_save_and_get_results(self):
        storage.save_results("session-1", {"mean": 42.0, "std": 1.5})
        results = storage.get_results("session-1")
        assert results == {"mean": 42.0, "std": 1.5}

    def test_get_results_empty(self):
        assert storage.get_results("nonexistent") == {}

    def test_overwrite_results(self):
        storage.save_results("s", {"a": 1})
        storage.save_results("s", {"b": 2})
        assert storage.get_results("s") == {"b": 2}

    def test_cascade_delete_with_session(self):
        storage.save_results("cascade-test", {"key": "val"})
        storage.delete_session("cascade-test")
        assert storage.get_results("cascade-test") == {}


class TestAnalysisProgress:
    def test_save_and_get_progress(self):
        storage.save_progress("p1", 0.5)
        data = storage.get_progress_data("p1")
        assert data["progress"] == 0.5
        assert data["error"] is None

    def test_get_progress_default(self):
        data = storage.get_progress_data("nonexistent")
        assert data["progress"] == 0.0
        assert data["error"] is None

    def test_save_progress_with_error(self):
        storage.save_progress("p2", 0.0, "Something went wrong")
        data = storage.get_progress_data("p2")
        assert data["error"] == "Something went wrong"

    def test_overwrite_progress(self):
        storage.save_progress("p3", 0.3)
        storage.save_progress("p3", 0.9)
        data = storage.get_progress_data("p3")
        assert data["progress"] == 0.9

    def test_cascade_delete_with_session(self):
        storage.save_progress("cascade-progress", 0.8)
        storage.delete_session("cascade-progress")
        data = storage.get_progress_data("cascade-progress")
        assert data["progress"] == 0.0
