import polars as pl
from typing import Any


def compute_scatter_data(df: pl.DataFrame, max_points: int = 5000) -> dict[str, Any]:
    """Compute scatter plot data for all numeric field pairs."""
    numeric_cols = [col for col in df.columns if df[col].dtype in (
        pl.Float32, pl.Float64, pl.Int64, pl.Int32,
    )]

    if len(numeric_cols) < 2:
        return {"fields": [], "pairs": []}

    # Sample if too many rows
    if len(df) > max_points:
        df = df.sample(max_points, seed=42)

    pairs = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            col1, col2 = numeric_cols[i], numeric_cols[j]
            subset = df.select([col1, col2]).drop_nulls()

            pairs.append({
                "x_field": col1,
                "y_field": col2,
                "points": [
                    [round(float(r[col1]), 4), round(float(r[col2]), 4)]
                    for r in subset.iter_rows(named=True)
                ],
            })

    return {"fields": numeric_cols, "pairs": pairs}
