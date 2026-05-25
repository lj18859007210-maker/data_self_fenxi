from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.session import sessions, FieldType
from app.services.nl2sql import parse_nl_query
from app.services import storage

router = APIRouter()


def _resolve_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        session = storage.get_session(session_id)
        if session:
            sessions[session_id] = session
    return session


class QueryRequest(BaseModel):
    query: str


@router.post("/api/sessions/{session_id}/query")
async def natural_language_query(session_id: str, body: QueryRequest):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    columns = [f.name for f in session.fields]
    numeric_cols = [f.name for f in session.fields if f.display_type == FieldType.NUMERIC]

    try:
        result = parse_nl_query(body.query, columns, numeric_cols, session.file_path)
        return {
            "success": True,
            "data": {
                "sql": result.sql,
                "columns": result.columns,
                "rows": result.rows[:200],
                "row_count": result.row_count,
            },
            "error": None,
        }
    except ValueError as e:
        return {"success": False, "data": None, "error": str(e)}
    except Exception as e:
        raise HTTPException(500, f"Query execution failed: {str(e)}")
