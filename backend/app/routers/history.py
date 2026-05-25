import os
from fastapi import APIRouter, HTTPException
from app.services import storage

router = APIRouter()


@router.get("/api/history")
async def get_history(limit: int = 50):
    sessions = storage.list_sessions(limit)
    return {"success": True, "data": sessions, "error": None}


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if os.path.exists(session.file_path):
        os.remove(session.file_path)

    storage.delete_session(session_id)
    return {"success": True, "data": None, "error": None}
