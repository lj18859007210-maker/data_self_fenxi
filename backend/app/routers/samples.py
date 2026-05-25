from fastapi import APIRouter
from app.config import UPLOAD_DIR
from app.utils.sample_data import get_sample_datasets, save_sample_data
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import Session, sessions
from app.services import storage

router = APIRouter()


@router.get("/api/samples")
async def list_samples():
    return {"success": True, "data": get_sample_datasets(), "error": None}


@router.post("/api/samples/{sample_id}/load")
async def load_sample(sample_id: str):
    if sample_id != "sales_data":
        return {"success": False, "data": None, "error": "Unknown sample"}

    file_path = save_sample_data(UPLOAD_DIR)
    df = load_dataframe(file_path)
    fields = analyze_fields(df)
    preview = get_preview(df)

    session = Session(
        filename="sample_sales_data.csv",
        file_path=file_path,
        file_size=0,
        row_count=len(df),
        column_count=len(df.columns),
        fields=fields,
        state="preview",
    )
    sessions[session.id] = session
    storage.save_session(session)

    return {
        "success": True,
        "data": {
            "session_id": session.id,
            "filename": session.filename,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "fields": [f.model_dump() for f in session.fields],
            "preview": preview,
        },
        "error": None,
    }
