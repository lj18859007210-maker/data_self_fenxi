from fastapi import APIRouter, HTTPException
from app.models.session import sessions
from app.routers.analyze import analysis_store
from app.services.chart_recommender import recommend_charts
from app.services.cross_tab import compute_cross_tabulation
from app.services.data_loader import load_dataframe
from app.services.insight_engine import discover_insights, compute_key_drivers
from app.services.scatter import compute_scatter_data
from app.services.timeseries import compute_time_series_analysis, detect_time_fields
from app.services import storage

router = APIRouter()


def _resolve_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        session = storage.get_session(session_id)
        if session:
            sessions[session_id] = session
    return session


def _resolve_results(session_id: str):
    """Get analysis results from memory or SQLite."""
    results = _resolve_results(session_id)
    if not results:
        results = storage.get_results(session_id)
    return results


@router.get("/api/sessions/{session_id}/overview")
async def get_overview(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    results = _resolve_results(session_id)
    fields_results = results.get("fields", {})
    summary = results.get("summary", {})

    # Count total outliers
    total_outliers = sum(
        f.get("outliers", {}).get("outlier_count", 0)
        for f in fields_results.values()
        if "outliers" in f
    )

    return {
        "success": True,
        "data": {
            "filename": session.filename,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "numeric_count": summary.get("total_numeric", 0),
            "text_count": summary.get("total_text", 0),
            "total_missing": sum(f.missing_count for f in session.fields),
            "total_outliers": total_outliers,
        },
        "error": None,
    }


@router.get("/api/sessions/{session_id}/fields/{field_name}")
async def get_field_analysis(session_id: str, field_name: str):
    results = _resolve_results(session_id)
    field_data = results.get("fields", {}).get(field_name)

    if field_data is None:
        raise HTTPException(404, f"Field '{field_name}' analysis not found")

    return {"success": True, "data": field_data, "error": None}


@router.get("/api/sessions/{session_id}/correlation")
async def get_correlation(session_id: str):
    results = _resolve_results(session_id)
    corr = results.get("correlation", {"fields": [], "matrix": [], "pairs": []})

    return {"success": True, "data": corr, "error": None}


@router.get("/api/sessions/{session_id}/insights")
async def get_insights(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    from app.services.data_loader import load_dataframe

    df = load_dataframe(session.file_path)
    insights = discover_insights(df, session.fields)
    return {"success": True, "data": insights, "error": None}


@router.get("/api/sessions/{session_id}/drivers")
async def get_key_drivers(session_id: str, target: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    from app.services.data_loader import load_dataframe

    df = load_dataframe(session.file_path)
    drivers = compute_key_drivers(df, target)
    return {"success": True, "data": drivers, "error": None}


@router.get("/api/sessions/{session_id}/charts")
async def get_charts(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    df = load_dataframe(session.file_path)

    results = _resolve_results(session_id)
    fields_results = results.get("fields", {})
    corr = results.get("correlation", {})

    charts = recommend_charts(session.fields, fields_results)

    # Populate chart data for types that need it
    for chart in charts:
        if chart["type"] == "heatmap" and corr:
            chart["data"] = {"fields": corr.get("fields", []), "matrix": corr.get("matrix", [])}

    return {"success": True, "data": charts, "error": None}


@router.get("/api/sessions/{session_id}/timeseries")
async def get_timeseries(session_id: str, time_field: str, value_field: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    df = load_dataframe(session.file_path)
    result = compute_time_series_analysis(df, time_field, value_field)
    return {"success": True, "data": result, "error": None}


@router.get("/api/sessions/{session_id}/scatter")
async def get_scatter_data(session_id: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    df = load_dataframe(session.file_path)
    result = compute_scatter_data(df)
    return {"success": True, "data": result, "error": None}


@router.get("/api/sessions/{session_id}/cross-tab")
async def get_cross_tabulation(session_id: str, row_field: str, col_field: str):
    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    df = load_dataframe(session.file_path)
    result = compute_cross_tabulation(df, row_field, col_field)
    return {"success": True, "data": result, "error": None}
