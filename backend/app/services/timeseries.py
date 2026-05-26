from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

try:
    from statsmodels.tsa.seasonal import seasonal_decompose  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    seasonal_decompose = None


def detect_time_fields(df: pl.DataFrame) -> list[str]:
    """Detect datetime fields in the dataframe."""
    return [col for col in df.columns if df[col].dtype in (pl.Date, pl.Datetime)]


def _ensure_datetime(series: pl.Series) -> pl.Series:
    """Cast or parse a series to Datetime type."""
    if series.dtype in (pl.Date, pl.Datetime):
        return series.cast(pl.Datetime)
    if series.dtype in (pl.Utf8, pl.String):
        return series.str.to_datetime()
    return series.cast(pl.Datetime, strict=False)


def _fallback_decompose(values: np.ndarray, period: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple seasonal decomposition fallback used when statsmodels is unavailable."""
    n = len(values)
    if n == 0:
        empty = np.asarray([])
        return empty, empty, empty

    if period < 2 or n < period:
        nan_arr = np.full(n, np.nan)
        return nan_arr, np.zeros(n), values - np.nanmean(values)

    kernel = np.ones(period, dtype=float) / period
    trend = np.convolve(values, kernel, mode="same")
    detrended = values - trend

    seasonal_pattern = np.zeros(period, dtype=float)
    counts = np.zeros(period, dtype=float)
    for idx, value in enumerate(detrended):
        if np.isfinite(value):
            bucket = idx % period
            seasonal_pattern[bucket] += value
            counts[bucket] += 1

    seasonal_pattern = np.divide(
        seasonal_pattern,
        counts,
        out=np.zeros_like(seasonal_pattern),
        where=counts > 0,
    )
    seasonal = np.asarray([seasonal_pattern[idx % period] for idx in range(n)], dtype=float)
    residual = values - trend - seasonal
    return trend, seasonal, residual


def compute_time_series_analysis(
    df: pl.DataFrame,
    time_field: str,
    value_field: str,
    freq: str = "D",
    model: str = "additive",
) -> dict[str, Any]:
    """
    Decompose a time series into trend + seasonal + residual.

    Groups by date, aggregates value_field, then decomposes.
    """
    ts_df = df.select([time_field, value_field]).drop_nulls()
    ts_df = ts_df.with_columns(_ensure_datetime(ts_df[time_field]).alias(time_field))

    daily = (
        ts_df.group_by(pl.col(time_field).cast(pl.Date))
        .agg(pl.col(value_field).mean().alias(value_field))
        .sort(time_field)
    )

    dates = daily[time_field].cast(pl.Utf8).to_list()
    values = daily[value_field].to_numpy()

    result = {
        "time_field": time_field,
        "value_field": value_field,
        "dates": dates,
        "original": [round(float(v), 4) for v in values],
    }

    min_periods = 14
    if len(values) >= min_periods * 2:
        try:
            period = 7
            if seasonal_decompose is not None:
                decomposition = seasonal_decompose(
                    values, model=model, period=period, extrapolate_trend="freq"
                )
                trend = decomposition.trend
                seasonal = decomposition.seasonal
                resid = decomposition.resid
            else:
                trend, seasonal, resid = _fallback_decompose(values.astype(float), period)

            result["trend"] = [
                round(float(v), 4) if np.isfinite(v) else None
                for v in trend
            ]
            result["seasonal"] = [
                round(float(v), 4) if np.isfinite(v) else None
                for v in seasonal
            ]
            result["residual"] = [
                round(float(v), 4) if np.isfinite(v) else None
                for v in resid
            ]
            result["period"] = period
        except Exception as e:
            result["error"] = str(e)

    return result
