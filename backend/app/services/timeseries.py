import polars as pl
import numpy as np
from typing import Any
from statsmodels.tsa.seasonal import seasonal_decompose


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

    # Aggregate by date
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

    # Need at least 2*period data points for decomposition
    min_periods = 14
    if len(values) >= min_periods * 2:
        try:
            period = 7  # Weekly seasonality for daily data
            decomposition = seasonal_decompose(
                values, model=model, period=period, extrapolate_trend="freq"
            )

            result["trend"] = [
                round(float(v), 4) if not np.isnan(v) else None
                for v in decomposition.trend
            ]
            result["seasonal"] = [
                round(float(v), 4) if not np.isnan(v) else None
                for v in decomposition.seasonal
            ]
            result["residual"] = [
                round(float(v), 4) if not np.isnan(v) else None
                for v in decomposition.resid
            ]
            result["period"] = period
        except Exception as e:
            result["error"] = str(e)

    return result
