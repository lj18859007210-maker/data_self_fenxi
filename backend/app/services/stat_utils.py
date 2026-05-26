from __future__ import annotations

import math
from typing import Iterable

import numpy as np

try:
    from scipy import stats as scipy_stats  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    scipy_stats = None


def _finite_array(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return arr
    return arr[np.isfinite(arr)]


def _normal_sf(z: float) -> float:
    """Two-sided normal survival approximation."""
    return math.erfc(abs(z) / math.sqrt(2.0))


def pearsonr(x: Iterable[float], y: Iterable[float]) -> tuple[float, float]:
    """Compute Pearson correlation with an optional scipy-backed exact p-value."""
    x_arr = _finite_array(x)
    y_arr = _finite_array(y)

    if len(x_arr) == 0 or len(y_arr) == 0:
        return float("nan"), 1.0

    n = min(len(x_arr), len(y_arr))
    if n < 2:
        return float("nan"), 1.0

    x_arr = x_arr[:n]
    y_arr = y_arr[:n]

    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return float("nan"), 1.0

    r = float(np.corrcoef(x_arr, y_arr)[0, 1])
    if not np.isfinite(r):
        return float("nan"), 1.0

    if scipy_stats is not None:
        try:
            _, p_value = scipy_stats.pearsonr(x_arr, y_arr)
            return r, float(p_value)
        except Exception:
            pass

    if n < 4 or abs(r) >= 1.0:
        return r, 0.0

    clipped_r = max(min(r, 0.999999999999), -0.999999999999)
    z = 0.5 * math.log((1.0 + clipped_r) / (1.0 - clipped_r)) * math.sqrt(n - 3)
    return r, min(1.0, max(0.0, _normal_sf(z)))


def skew(values: Iterable[float]) -> float:
    arr = _finite_array(values)
    if len(arr) < 3:
        return 0.0

    mean = float(np.mean(arr))
    std = float(np.std(arr))
    if std == 0:
        return 0.0

    centered = (arr - mean) / std
    return float(np.mean(centered**3))


def f_oneway(*groups: Iterable[float]) -> tuple[float, float]:
    """One-way ANOVA with a lightweight fallback when scipy is unavailable."""
    clean_groups = [_finite_array(group) for group in groups if len(_finite_array(group)) > 0]
    clean_groups = [group for group in clean_groups if len(group) > 0]

    if len(clean_groups) < 2:
        return float("nan"), 1.0

    if scipy_stats is not None:
        try:
            f_stat, p_value = scipy_stats.f_oneway(*clean_groups)
            return float(f_stat), float(p_value)
        except Exception:
            pass

    counts = [len(group) for group in clean_groups]
    total_n = sum(counts)
    if total_n <= len(clean_groups):
        return float("nan"), 1.0

    means = [float(np.mean(group)) for group in clean_groups]
    grand_mean = float(np.mean(np.concatenate(clean_groups)))

    ss_between = sum(n * (mean - grand_mean) ** 2 for n, mean in zip(counts, means))
    ss_within = sum(float(np.sum((group - mean) ** 2)) for group, mean in zip(clean_groups, means))

    df_between = len(clean_groups) - 1
    df_within = total_n - len(clean_groups)
    if df_between <= 0 or df_within <= 0:
        return float("nan"), 1.0

    if ss_within == 0:
        return float("inf") if ss_between > 0 else 0.0, 0.0 if ss_between > 0 else 1.0

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = float(ms_between / ms_within)

    # Lightweight monotonic approximation: large F values should yield very
    # small p-values, while small F values should stay near 1.
    p_value = math.exp(-0.5 * max(f_stat, 0.0) * df_between)
    return f_stat, min(1.0, max(0.0, p_value))


def chi2_contingency(observed: np.ndarray) -> tuple[float, float, int, np.ndarray]:
    """Chi-square test with a fallback approximation."""
    if scipy_stats is not None:
        try:
            return scipy_stats.chi2_contingency(observed)
        except Exception:
            pass

    observed = np.asarray(observed, dtype=float)
    if observed.size == 0:
        return float("nan"), 1.0, 0, np.asarray([])

    row_sums = observed.sum(axis=1, keepdims=True)
    col_sums = observed.sum(axis=0, keepdims=True)
    total = observed.sum()
    if total <= 0:
        return float("nan"), 1.0, 0, np.zeros_like(observed)

    expected = row_sums @ col_sums / total
    if np.any(expected == 0):
        return float("nan"), 1.0, 0, expected

    chi2 = float(np.sum((observed - expected) ** 2 / expected))
    dof = int((observed.shape[0] - 1) * (observed.shape[1] - 1))
    if dof <= 0:
        return chi2, 1.0, dof, expected

    # Wilson-Hilferty transform approximation for the chi-square survival
    # function. This is accurate enough for the ranking/thresholding used here.
    z = ((chi2 / dof) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * dof))) / math.sqrt(2.0 / (9.0 * dof))
    p_value = 0.5 * math.erfc(z / math.sqrt(2.0))
    return chi2, min(1.0, max(0.0, p_value)), dof, expected
