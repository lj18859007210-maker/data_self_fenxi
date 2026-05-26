"""
Automatic insight discovery engine.

Scans all field combinations and produces structured insights:
- Distribution insights (skewed, uniform, sparse)
- Correlation insights (strong pairs)
- Outlier insights (fields with many outliers)
- Comparison insights (category differences)
- Missing data insights
- Time series insights (trends, seasonality)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from app.models.session import FieldType
from app.services.stat_utils import f_oneway, pearsonr, skew


class Insight:
    def __init__(
        self,
        insight_type: str,
        field: str,
        title: str,
        description: str,
        score: float,
        detail: dict | None = None,
    ):
        self.type = insight_type
        self.field = field
        self.title = title
        self.description = description
        self.score = round(float(score), 4)
        self.detail = detail or {}

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "field": self.field,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "detail": self.detail,
        }


def discover_insights(df: pl.DataFrame, fields_meta: list[Any]) -> list[dict]:
    """Run all discovery methods and return ranked insights."""
    insights: list[Insight] = []

    # 1. Distribution insights for numeric fields
    for field in [f for f in fields_meta if f.display_type == FieldType.NUMERIC]:
        series = df[field.name].drop_nulls()
        if len(series) < 10:
            continue
        arr = series.to_numpy()

        skewness = float(skew(arr))
        if abs(skewness) > 1.0:
            direction = "right" if skewness > 0 else "left"
            insights.append(
                Insight(
                    "distribution",
                    field.name,
                    f"{field.name} skewed distribution",
                    f"{field.name} shows a {direction}-skewed distribution with skewness {skewness:.2f}.",
                    min(abs(skewness) / 3, 1.0) * 0.7,
                    {"skewness": round(skewness, 4), "direction": direction},
                )
            )

        # Check high cardinality / spread
        mean = float(np.mean(arr))
        cv = float(np.std(arr) / mean) if mean != 0 else 0.0
        if cv > 2.0:
            insights.append(
                Insight(
                    "distribution",
                    field.name,
                    f"{field.name} highly variable",
                    f"Coefficient of variation is {cv:.2f}, suggesting a very wide spread.",
                    min(cv / 5, 1.0) * 0.5,
                    {"cv": round(cv, 4)},
                )
            )

    # 2. Outlier insights
    for field in [f for f in fields_meta if f.display_type == FieldType.NUMERIC]:
        series = df[field.name].drop_nulls()
        if len(series) < 10:
            continue
        arr = series.to_numpy()
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_ratio = float(np.mean((arr < lower) | (arr > upper)))

        if outlier_ratio > 0.05:
            insights.append(
                Insight(
                    "outlier",
                    field.name,
                    f"{field.name} outlier signal",
                    f"IQR-based outlier ratio is {outlier_ratio * 100:.1f}%.",
                    min(outlier_ratio * 2, 1.0) * 0.8,
                    {"outlier_ratio": round(outlier_ratio, 4)},
                )
            )

    # 3. Missing data insights
    for field in fields_meta:
        series = df[field.name]
        null_ratio = float(series.is_null().mean())
        if null_ratio > 0.05:
            insights.append(
                Insight(
                    "missing",
                    field.name,
                    f"{field.name} has missing values",
                    f"{int(series.is_null().sum())} values are missing ({null_ratio * 100:.1f}%).",
                    min(null_ratio * 2, 1.0) * 0.6,
                    {"missing_rate": round(null_ratio, 4), "missing_count": int(series.is_null().sum())},
                )
            )

    # 4. Correlation insights
    numeric_cols = [f.name for f in fields_meta if f.display_type == FieldType.NUMERIC]
    if len(numeric_cols) >= 2:
        num_df = df.select(numeric_cols).drop_nulls()
        if len(num_df) >= 10:
            corr_matrix = np.corrcoef(num_df.to_numpy().T)
            for i in range(len(numeric_cols)):
                for j in range(i + 1, len(numeric_cols)):
                    r = float(corr_matrix[i, j])
                    if not np.isfinite(r) or abs(r) < 0.7:
                        continue
                    direction = "positive" if r > 0 else "negative"
                    insights.append(
                        Insight(
                            "correlation",
                            f"{numeric_cols[i]},{numeric_cols[j]}",
                            f"{numeric_cols[i]} and {numeric_cols[j]} are strongly correlated",
                            f"Correlation coefficient is {r:.3f} ({direction}).",
                            abs(r) * 0.9,
                            {
                                "field1": numeric_cols[i],
                                "field2": numeric_cols[j],
                                "correlation": round(r, 4),
                                "direction": direction,
                            },
                        )
                    )

    # 5. Category imbalance insights
    for field in [f for f in fields_meta if f.display_type in (FieldType.CATEGORY, FieldType.TEXT, FieldType.BOOLEAN)]:
        series = df[field.name].drop_nulls()
        if len(series) < 10:
            continue
        freq = series.value_counts().sort("count", descending=True)
        top_ratio = freq["count"][0] / len(series)
        if top_ratio > 0.8:
            insights.append(
                Insight(
                    "imbalance",
                    field.name,
                    f"{field.name} is imbalanced",
                    f"The top category accounts for {top_ratio * 100:.1f}% of non-null values.",
                    top_ratio * 0.5,
                    {"top_category": str(freq[field.name][0]), "top_ratio": round(top_ratio, 4)},
                )
            )

    # 6. Category vs numeric comparison insights
    cat_fields = [f for f in fields_meta if f.display_type in (FieldType.CATEGORY, FieldType.TEXT)]
    num_fields = [f for f in fields_meta if f.display_type == FieldType.NUMERIC]
    for cat_f in cat_fields[:3]:
        for num_f in num_fields[:3]:
            grouped = (
                df.group_by(cat_f.name)
                .agg(
                    pl.col(num_f.name).mean().alias("mean"),
                    pl.col(num_f.name).count().alias("count"),
                )
                .filter(pl.col("count") >= 10)
                .sort("mean", descending=True)
            )

            if len(grouped) >= 2:
                means = grouped["mean"].to_numpy()
                top = grouped[cat_f.name][0]
                bottom = grouped[cat_f.name][-1]
                ratio = means[0] / means[-1] if means[-1] != 0 else 0

                if ratio > 2.0:
                    insights.append(
                        Insight(
                            "comparison",
                            f"{cat_f.name},{num_f.name}",
                            f"{top} outperforms {bottom}",
                            f"The highest group mean is {ratio:.1f}x the lowest group mean.",
                            min(ratio / 5, 1.0) * 0.75,
                            {
                                "category_field": cat_f.name,
                                "numeric_field": num_f.name,
                                "top_group": str(top),
                                "bottom_group": str(bottom),
                                "ratio": round(ratio, 2),
                            },
                        )
                    )

    # 7. Unique / cardinality insights
    for field in fields_meta:
        series = df[field.name].drop_nulls()
        if len(series) < 5:
            continue
        unique = len(series.unique())
        if unique == 1:
            insights.append(
                Insight(
                    "cardinality",
                    field.name,
                    f"{field.name} has only one value",
                    f"The field contains a single unique value: {series[0]}.",
                    0.3,
                    {"unique_count": 1, "value": str(series[0])},
                )
            )

    insights.sort(key=lambda x: x.score, reverse=True)
    return [i.to_dict() for i in insights]


def compute_key_drivers(df: pl.DataFrame, target_field: str) -> list[dict]:
    """
    Identify key drivers for a target numeric field.
    Uses correlation for numeric features and ANOVA for categorical features.
    """
    drivers = []
    series = df[target_field].drop_nulls()
    if len(series) < 10:
        return drivers

    for col in df.columns:
        if col == target_field:
            continue

        other = df[col].drop_nulls()
        if len(other) < 10:
            continue

        combined = df.select([target_field, col]).drop_nulls()
        if len(combined) < 10:
            continue

        dtype = combined[col].dtype
        is_num = dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)

        if is_num:
            x = combined[target_field].to_numpy()
            y = combined[col].to_numpy()
            if len(x) >= 10:
                r, p = pearsonr(x, y)
                if not np.isfinite(r):
                    continue
                drivers.append(
                    {
                        "field": col,
                        "type": "numeric",
                        "score": abs(r),
                        "correlation": round(float(r), 4),
                        "p_value": round(float(p), 6),
                        "direction": "positive" if r > 0 else "negative",
                        "description": f"Correlation coefficient r={r:.3f}, p={p:.4f}",
                    }
                )
        else:
            groups = []
            for cat in combined[col].unique():
                vals = combined.filter(pl.col(col) == cat)[target_field].drop_nulls().to_numpy()
                if len(vals) >= 3:
                    groups.append(vals)
            if len(groups) >= 2:
                f_stat, p_val = f_oneway(*groups)
                if not np.isfinite(f_stat):
                    continue
                n_total = sum(len(g) for g in groups)
                if n_total > 0:
                    eta_sq = f_stat * (len(groups) - 1) / (f_stat * (len(groups) - 1) + n_total - len(groups))
                    if not np.isfinite(eta_sq):
                        continue
                    drivers.append(
                        {
                            "field": col,
                            "type": "categorical",
                            "score": eta_sq,
                            "f_statistic": round(float(f_stat), 4),
                            "p_value": round(float(p_val), 6),
                            "eta_squared": round(float(eta_sq), 4),
                            "description": f"F={f_stat:.2f}, p={p_val:.4f}, eta^2={eta_sq:.3f}",
                        }
                    )

    drivers.sort(key=lambda x: x["score"], reverse=True)
    return drivers
