"""
chart_recommender.py — Smart chart recommendation engine.

Recommends appropriate chart types based on field data types and
statistical characteristics (histograms, boxplots, correlations, etc.).
"""

from typing import Any
from app.models.session import FieldType


def recommend_charts(fields_meta: list[Any], field_analyses: dict) -> list[dict]:
    """Recommend charts based on field types and data characteristics.

    Parameters
    ----------
    fields_meta : list[FieldInfo]
        Metadata for each field in the session.
    field_analyses : dict
        Mapping of field name to analysis results (containing histogram,
        boxplot, frequency, etc.).

    Returns
    -------
    list[dict]
        Sorted list of chart configuration dicts, highest priority first.
    """
    from app.models.session import FieldType

    charts = []
    has_numeric = any(f.display_type == FieldType.NUMERIC for f in fields_meta)
    has_category = any(
        f.display_type in (FieldType.CATEGORY, FieldType.TEXT) for f in fields_meta
    )
    has_time = any(f.display_type == FieldType.DATETIME for f in fields_meta)

    # ------------------------------------------------------------------
    # Numeric distribution (always)
    # ------------------------------------------------------------------
    num_fields = [f for f in fields_meta if f.display_type == FieldType.NUMERIC]
    for f in num_fields[:3]:
        analysis = field_analyses.get(f.name, {})
        if "histogram" in analysis:
            charts.append(
                {
                    "id": f"hist_{f.name}",
                    "type": "histogram",
                    "title": f"{f.name} 分布",
                    "field": f.name,
                    "priority": 90,
                    "data": analysis["histogram"],
                    "stats": analysis.get("stats", {}),
                }
            )
        if "boxplot" in analysis:
            charts.append(
                {
                    "id": f"box_{f.name}",
                    "type": "boxplot",
                    "title": f"{f.name} 箱线图",
                    "field": f.name,
                    "priority": 85,
                    "data": analysis["boxplot"],
                }
            )

    # ------------------------------------------------------------------
    # Correlation heatmap
    # ------------------------------------------------------------------
    if has_numeric and len(num_fields) >= 2:
        charts.append(
            {
                "id": "corr_matrix",
                "type": "heatmap",
                "title": "数值字段相关性矩阵",
                "field": "all",
                "priority": 88,
                "data": {},
            }
        )

    # ------------------------------------------------------------------
    # Category / text frequency
    # ------------------------------------------------------------------
    cat_fields = [
        f
        for f in fields_meta
        if f.display_type in (FieldType.CATEGORY, FieldType.TEXT)
    ]
    for f in cat_fields[:5]:
        analysis = field_analyses.get(f.name, {})
        if "frequency" in analysis:
            cats = analysis["frequency"].get("categories", [])
            chart_type = "pie" if len(cats) <= 8 else "bar"
            charts.append(
                {
                    "id": f"freq_{f.name}",
                    "type": chart_type,
                    "title": f"{f.name} 分布",
                    "field": f.name,
                    "priority": 80 if chart_type == "pie" else 70,
                    "data": analysis["frequency"],
                }
            )

    # ------------------------------------------------------------------
    # Time series
    # ------------------------------------------------------------------
    if has_time and has_numeric:
        time_fields = [f for f in fields_meta if f.display_type == FieldType.DATETIME]
        for tf in time_fields[:1]:
            for nf in num_fields[:2]:
                charts.append(
                    {
                        "id": f"ts_{tf.name}_{nf.name}",
                        "type": "timeseries",
                        "title": f"{nf.name} 随时间变化",
                        "field": f"{tf.name},{nf.name}",
                        "priority": 75,
                        "data": {},
                    }
                )

    # ------------------------------------------------------------------
    # Category vs numeric (crosstab)
    # ------------------------------------------------------------------
    if has_category and has_numeric:
        for cf in cat_fields[:2]:
            for nf in num_fields[:2]:
                charts.append(
                    {
                        "id": f"cmp_{cf.name}_{nf.name}",
                        "type": "crosstab",
                        "title": f"{nf.name} 按 {cf.name} 分组",
                        "field": f"{cf.name},{nf.name}",
                        "priority": 65,
                        "data": {},
                    }
                )

    charts.sort(key=lambda x: x["priority"], reverse=True)
    return charts
