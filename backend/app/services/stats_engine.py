import polars as pl
import numpy as np
from typing import Any
from app.models.session import FieldType


def compute_descriptive_stats(series: pl.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a numeric series."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {}

    arr = non_null.to_numpy()
    qs = np.percentile(arr, [25, 50, 75])

    return {
        "count": int(len(series)),
        "missing": int(series.is_null().sum()),
        "missing_rate": round(float(series.is_null().mean()), 4),
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(arr, ddof=1)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "q1": round(float(qs[0]), 4),
        "median": round(float(qs[1]), 4),
        "q3": round(float(qs[2]), 4),
        "skewness": round(float(np.mean(((arr - np.mean(arr)) / np.std(arr)) ** 3)), 4),
        "kurtosis": round(float(np.mean(((arr - np.mean(arr)) / np.std(arr)) ** 4) - 3), 4),
    }


def compute_histogram(series: pl.Series, bins: int = 30) -> dict[str, Any]:
    """Compute histogram data for a numeric series."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {"bins": [], "counts": []}

    arr = non_null.to_numpy()
    counts, edges = np.histogram(arr, bins=bins)
    return {
        "bins": edges.tolist(),
        "counts": counts.tolist(),
    }


def compute_frequency(series: pl.Series, top_n: int = 20) -> dict[str, Any]:
    """Compute frequency table for a categorical/text field."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {"categories": [], "counts": [], "total": 0}

    freq = non_null.value_counts().head(top_n)
    cats = freq[non_null.name].to_list()
    counts = freq["count"].to_list()

    return {
        "categories": [str(c) for c in cats],
        "counts": counts,
        "total": int(len(non_null)),
    }


def compute_outliers_iqr(series: pl.Series) -> dict[str, Any]:
    """Detect outliers using IQR method."""
    non_null = series.drop_nulls()
    if len(non_null) < 4:
        return {"outlier_count": 0, "outlier_values": [], "lower_bound": 0.0, "upper_bound": 0.0, "outlier_rate": 0.0}

    arr = non_null.to_numpy()
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outlier_mask = (arr < lower) | (arr > upper)
    outlier_values = arr[outlier_mask].tolist()

    return {
        "lower_bound": round(float(lower), 4),
        "upper_bound": round(float(upper), 4),
        "outlier_count": int(outlier_mask.sum()),
        "outlier_rate": round(float(outlier_mask.mean()), 4),
        "outlier_values": [round(float(v), 4) for v in outlier_values[:100]],
    }


def compute_boxplot_data(series: pl.Series) -> dict[str, Any]:
    """Compute boxplot data (five-number summary + outliers)."""
    non_null = series.drop_nulls()
    if len(non_null) < 4:
        return {
            "min": None, "q1": None, "median": None,
            "q3": None, "max": None,
            "outlier_values": [], "outlier_count": 0,
        }

    arr = non_null.to_numpy()
    q1, q2, q3 = np.percentile(arr, [25, 50, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    whisker_min = float(np.min(arr[arr >= lower]))
    whisker_max = float(np.max(arr[arr <= upper]))

    outlier_mask = (arr < lower) | (arr > upper)
    outliers = arr[outlier_mask].tolist()

    return {
        "min": round(float(whisker_min), 4),
        "q1": round(float(q1), 4),
        "median": round(float(q2), 4),
        "q3": round(float(q3), 4),
        "max": round(float(whisker_max), 4),
        "outlier_values": [round(float(v), 4) for v in outliers[:200]],
        "outlier_count": int(outlier_mask.sum()),
    }


def compute_field_analysis(df: pl.DataFrame, field_name: str, field_type: FieldType) -> dict[str, Any]:
    """Run all relevant analysis for a single field."""
    series = df[field_name]
    result = {"field_name": field_name, "field_type": field_type.value}

    if field_type == FieldType.NUMERIC:
        result["stats"] = compute_descriptive_stats(series)
        result["histogram"] = compute_histogram(series)
        result["outliers"] = compute_outliers_iqr(series)
        result["boxplot"] = compute_boxplot_data(series)
    elif field_type in (FieldType.CATEGORY, FieldType.TEXT, FieldType.BOOLEAN):
        result["frequency"] = compute_frequency(series)
    elif field_type == FieldType.DATETIME:
        non_null = series.drop_nulls()
        result["stats"] = {
            "count": int(len(series)),
            "missing": int(series.is_null().sum()),
            "min": str(non_null.min()) if len(non_null) > 0 else None,
            "max": str(non_null.max()) if len(non_null) > 0 else None,
        }

    return result
