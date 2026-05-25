import polars as pl
import numpy as np
from scipy import stats
from typing import Any


def compute_cross_tabulation(
    df: pl.DataFrame,
    row_field: str,
    col_field: str,
) -> dict[str, Any]:
    """Compute cross-tabulation between two fields."""
    row_dtype = df[row_field].dtype
    col_dtype = df[col_field].dtype

    is_row_num = row_dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)
    is_col_num = col_dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)

    if not is_row_num and not is_col_num:
        return _compute_contingency(df, row_field, col_field)
    elif is_row_num != is_col_num:
        cat_field = col_field if is_row_num else row_field
        num_field = row_field if is_row_num else col_field
        return _compute_group_stats(df, cat_field, num_field)
    else:
        return {"type": "error", "message": "两个字段都是数值类型，建议使用相关性分析"}


def _compute_contingency(df: pl.DataFrame, row_field: str, col_field: str, top_n: int = 20) -> dict[str, Any]:
    """Chi-square test of independence between two categorical fields."""
    row_freq = df[row_field].value_counts().sort("count", descending=True).head(top_n)
    col_freq = df[col_field].value_counts().sort("count", descending=True).head(top_n)

    row_labels = row_freq[row_field].to_list()
    col_labels = col_freq[col_field].to_list()

    # Build matrix
    matrix = []
    for r in row_labels:
        row_data = []
        for c in col_labels:
            val = df.filter(pl.col(row_field) == r, pl.col(col_field) == c).height
            row_data.append(val)
        matrix.append(row_data)

    # Chi-square test
    observed = np.array(matrix)
    if observed.size > 0 and observed.shape[0] > 1 and observed.shape[1] > 1:
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)
        n = observed.sum()
        cramers_v = np.sqrt(chi2 / (n * min(observed.shape[0] - 1, observed.shape[1] - 1))) if n > 0 else None
    else:
        chi2, p_value, cramers_v = None, None, None

    return {
        "type": "contingency",
        "row_field": row_field,
        "col_field": col_field,
        "row_categories": [str(r) for r in row_labels],
        "col_categories": [str(c) for c in col_labels],
        "matrix": matrix,
        "chi2": round(float(chi2), 4) if chi2 is not None else None,
        "p_value": round(float(p_value), 6) if p_value is not None else None,
        "cramers_v": round(float(cramers_v), 4) if cramers_v is not None else None,
    }


def _compute_group_stats(df: pl.DataFrame, cat_field: str, num_field: str, top_n: int = 20) -> dict[str, Any]:
    """Compare numeric field across categories (ANOVA)."""
    freq = df[cat_field].value_counts().sort("count", descending=True).head(top_n)
    top_cats = set(freq[cat_field].to_list())

    groups = []
    group_data = []
    for cat in freq[cat_field].to_list():
        values = df.filter(pl.col(cat_field) == cat)[num_field].drop_nulls().to_numpy()
        if len(values) > 0:
            groups.append({
                "category": str(cat),
                "count": int(len(values)),
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values, ddof=1)), 4),
                "min": round(float(np.min(values)), 4),
                "max": round(float(np.max(values)), 4),
            })
            group_data.append(values)

    # One-way ANOVA
    if len(group_data) >= 2:
        f_stat, p_value = stats.f_oneway(*group_data)
        n_total = sum(len(g) for g in group_data)
        eta_sq = f_stat * (len(group_data) - 1) / (f_stat * (len(group_data) - 1) + n_total - len(group_data))
    else:
        f_stat, p_value, eta_sq = None, None, None

    return {
        "type": "group_stats",
        "category_field": cat_field,
        "numeric_field": num_field,
        "groups": groups,
        "anova_f": round(float(f_stat), 4) if f_stat is not None else None,
        "anova_p": round(float(p_value), 6) if p_value is not None else None,
        "eta_squared": round(float(eta_sq), 4) if eta_sq is not None else None,
    }
