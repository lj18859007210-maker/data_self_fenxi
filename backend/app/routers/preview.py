from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import FieldType, sessions
from app.services import storage

router = APIRouter()


class FieldUpdate(BaseModel):
    name: str
    display_type: FieldType


def _resolve_session(session_id: str):
    """Get session from memory or fall back to SQLite."""
    session = sessions.get(session_id)
    if not session:
        session = storage.get_session(session_id)
        if session:
            sessions[session_id] = session
    return session


@router.get("/api/sessions/{session_id}/preview")
async def get_preview_data(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    df = load_dataframe(session.file_path)
    return {
        "success": True,
        "data": {
            "fields": [f.model_dump() for f in session.fields],
            "preview": get_preview(df),
            "row_count": session.row_count,
            "column_count": session.column_count,
        },
        "error": None,
    }


@router.put("/api/sessions/{session_id}/fields")
async def update_fields(session_id: str, updates: list[FieldUpdate]):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    update_map = {u.name: u.display_type for u in updates}
    for field in session.fields:
        if field.name in update_map:
            field.display_type = update_map[field.name]

    storage.save_session(session)

    return {
        "success": True,
        "data": {"fields": [f.model_dump() for f in session.fields]},
        "error": None,
    }
