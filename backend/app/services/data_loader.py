import os
import tempfile
import polars as pl
from pathlib import Path
from app.config import UPLOAD_DIR
from app.models.session import FieldInfo, FieldType


def load_dataframe(file_path: str) -> pl.DataFrame:
    path = Path(file_path).resolve()
    upload_dir = Path(UPLOAD_DIR).resolve()
    if not str(path).startswith(str(upload_dir)):
        raise ValueError("File path must be within upload directory")
    ext = path.suffix.lower()
    if ext == ".csv":
        return _read_csv_with_encoding_fallback(str(path))
    elif ext in (".xlsx", ".xls"):
        return pl.read_excel(str(path), infer_schema_length=10000)
    raise ValueError(f"Unsupported file type: {ext}")


def _read_csv_with_encoding_fallback(path: str) -> pl.DataFrame:
    """Try UTF-8 first, then common Chinese encodings via Python decode."""
    with open(path, "rb") as f:
        raw = f.read()

    for enc in ["utf-8", "gbk", "gb2312", "gb18030"]:
        try:
            text = raw.decode(enc)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(text)
                tmp_path = tmp.name
            try:
                return pl.read_csv(tmp_path, infer_schema_length=10000)
            finally:
                os.unlink(tmp_path)
        except UnicodeDecodeError:
            continue

    return pl.read_csv(path, infer_schema_length=10000, encoding="utf8-lossy")


def infer_field_type(series: pl.Series) -> FieldType:
    dtype = series.dtype
    if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                 pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                 pl.Float32, pl.Float64):
        return FieldType.NUMERIC
    if dtype == pl.Boolean:
        return FieldType.BOOLEAN
    if dtype == pl.Date or dtype == pl.Datetime:
        return FieldType.DATETIME
    if dtype == pl.Utf8 or dtype == pl.String:
        non_null = series.drop_nulls()
        if len(non_null) > 0:
            unique_ratio = len(non_null.unique()) / len(non_null)
            if unique_ratio < 0.05 and len(non_null.unique()) < 50:
                return FieldType.CATEGORY
            return FieldType.TEXT
        return FieldType.TEXT
    if dtype.is_temporal():
        return FieldType.DATETIME
    return FieldType.TEXT


def analyze_fields(df: pl.DataFrame) -> list[FieldInfo]:
    fields = []
    for col in df.columns:
        series = df[col]
        inferred = infer_field_type(series)
        non_null = series.drop_nulls()
        missing = series.is_null().sum()
        unique_count = len(non_null.unique()) if len(non_null) > 0 else 0
        sample_values = [str(v) for v in non_null[:5].to_list()] if len(non_null) > 0 else []

        fields.append(FieldInfo(
            name=col,
            inferred_type=inferred,
            display_type=inferred,
            nullable=missing > 0,
            unique_count=unique_count,
            missing_count=missing,
            sample_values=sample_values,
        ))
    return fields


def get_preview(df: pl.DataFrame, rows: int = 100) -> list[dict]:
    return df.head(rows).to_dicts()
