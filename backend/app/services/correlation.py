import polars as pl
import numpy as np
from typing import Any
from app.services.stat_utils import pearsonr


def compute_correlation_matrix(df: pl.DataFrame) -> dict[str, Any]:
    """Compute Pearson correlation matrix for all numeric fields."""
    numeric_cols = [col for col in df.columns if df[col].dtype in (
        pl.Int8, pl.Int16, pl.Int32, pl.Int64,
        pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
        pl.Float32, pl.Float64
    )]

    if len(numeric_cols) < 2:
        return {"fields": [], "matrix": [], "pairs": []}

    matrix = []
    pairs = []

    for i, col1 in enumerate(numeric_cols):
        row = []
        for j, col2 in enumerate(numeric_cols):
            s1 = df[col1].drop_nulls().to_numpy()
            s2 = df[col2].drop_nulls().to_numpy()

            if len(s1) < 3 or len(s2) < 3:
                row.append(None)
                continue

            # Align by truncating to same length for correlation
            min_len = min(len(s1), len(s2))
            r, p = pearsonr(s1[:min_len], s2[:min_len])
            if not np.isfinite(r):
                row.append(None)
                continue
            row.append(round(float(r), 4))

            if i < j:
                pairs.append({
                    "field1": col1,
                    "field2": col2,
                    "correlation": round(float(r), 4),
                    "p_value": round(float(p), 6),
                    "strength": "strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak",
                    "direction": "positive" if r > 0 else "negative",
                })

        matrix.append(row)

    return {
        "fields": numeric_cols,
        "matrix": matrix,
        "pairs": sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True),
    }
