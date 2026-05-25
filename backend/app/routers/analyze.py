import threading
from fastapi import APIRouter, HTTPException
from app.services.data_loader import load_dataframe
from app.services.stats_engine import compute_field_analysis
from app.services.correlation import compute_correlation_matrix
from app.models.session import SessionState, sessions
from app.services import storage

router = APIRouter()

# In-memory analysis progress store: session_id -> {"progress": float, "results": dict}
analysis_store: dict[str, dict] = {}


def run_analysis(session_id: str):
    """Run full analysis in background thread."""
    session = _resolve_session(session_id)
    if not session:
        return

    store = analysis_store[session_id] = {"progress": 0.0, "results": {}}
    storage.save_progress(session_id, 0.0)
    session.state = SessionState.ANALYZING
    storage.save_session(session)

    try:
        df = load_dataframe(session.file_path)

        # Phase 1: Single field analysis (60% of progress)
        total_fields = len(session.fields)
        field_results = {}
        for i, field in enumerate(session.fields):
            field_results[field.name] = compute_field_analysis(df, field.name, field.display_type)
            store["progress"] = round((i + 1) / total_fields * 0.6, 2)
            storage.save_progress(session_id, store["progress"])

        store["results"]["fields"] = field_results

        # Phase 2: Correlation analysis (30% of progress)
        store["progress"] = 0.6
        storage.save_progress(session_id, 0.6)
        corr = compute_correlation_matrix(df)
        store["results"]["correlation"] = corr
        store["progress"] = 0.9

        # Phase 3: Summary (10%)
        store["results"]["summary"] = {
            "total_rows": session.row_count,
            "total_columns": session.column_count,
            "total_numeric": sum(1 for f in session.fields if f.display_type.value == "numeric"),
            "total_text": sum(1 for f in session.fields if f.display_type.value in ("text", "category")),
        }
        store["progress"] = 1.0
        storage.save_progress(session_id, 1.0)
        storage.save_results(session_id, store["results"])
        session.state = SessionState.COMPLETE
        storage.save_session(session)

    except Exception as e:
        session.state = SessionState.ERROR
        store["error"] = str(e)
        storage.save_progress(session_id, store.get("progress", 0.0), error=str(e))
        storage.save_session(session)


def _resolve_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        session = storage.get_session(session_id)
        if session:
            sessions[session_id] = session
    return session


@router.post("/api/sessions/{session_id}/analyze")
async def trigger_analysis(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.state == SessionState.ANALYZING:
        raise HTTPException(400, "Analysis already in progress")

    thread = threading.Thread(target=run_analysis, args=(session_id,), daemon=True)
    thread.start()

    return {"success": True, "data": {"session_id": session_id, "state": "analyzing"}, "error": None}


@router.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    store = analysis_store.get(session_id)
    if store is not None:
        progress = store["progress"]
        error = store.get("error")
    else:
        pd = storage.get_progress_data(session_id)
        progress = pd["progress"]
        error = pd.get("error")

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "state": session.state.value,
            "progress": progress,
            "error": error,
        },
        "error": None,
    }
