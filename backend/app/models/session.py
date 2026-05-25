from pydantic import BaseModel, Field
from typing import Any
from enum import Enum
from datetime import datetime
import uuid


class FieldType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CATEGORY = "category"


class FieldInfo(BaseModel):
    name: str
    inferred_type: FieldType
    display_type: FieldType
    nullable: bool = False
    unique_count: int = 0
    missing_count: int = 0
    sample_values: list[Any] = []


class SessionState(str, Enum):
    UPLOADED = "uploaded"
    PREVIEW = "preview"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_path: str
    file_size: int
    row_count: int = 0
    column_count: int = 0
    fields: list[FieldInfo] = Field(default_factory=list)
    state: SessionState = SessionState.UPLOADED
    analysis_progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)

# In-memory session store (MVP only)
sessions: dict[str, Session] = {}
