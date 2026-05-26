from app.routers import dashboard


class TestResolveResults:
    def teardown_method(self):
        dashboard.analysis_store.clear()

    def test_uses_in_memory_results_first(self, monkeypatch):
        dashboard.analysis_store["session-1"] = {
            "progress": 0.6,
            "results": {"summary": {"source": "memory"}},
        }
        monkeypatch.setattr(dashboard.storage, "get_results", lambda session_id: {"summary": {"source": "storage"}})

        result = dashboard._resolve_results("session-1")

        assert result == {"summary": {"source": "memory"}}

    def test_falls_back_to_storage(self, monkeypatch):
        monkeypatch.setattr(dashboard.storage, "get_results", lambda session_id: {"summary": {"source": "storage"}})

        result = dashboard._resolve_results("session-2")

        assert result == {"summary": {"source": "storage"}}
