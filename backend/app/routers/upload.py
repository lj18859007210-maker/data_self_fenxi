import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import Session, sessions
from app.services import storage

router = APIRouter()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Supported: {', '.join(ALLOWED_EXTENSIONS)}")

    # Save file to upload directory
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Load and analyze
    try:
        df = load_dataframe(str(file_path))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    fields = analyze_fields(df)
    preview = get_preview(df)

    session = Session(
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
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
            "file_size": session.file_size,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "fields": [f.model_dump() for f in session.fields],
            "preview": preview,
        },
        "error": None,
    }
