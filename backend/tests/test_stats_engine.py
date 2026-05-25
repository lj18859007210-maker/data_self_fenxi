import polars as pl
import numpy as np
import pytest
from app.models.session import FieldType
from app.services.stats_engine import (
    compute_descriptive_stats,
    compute_histogram,
    compute_frequency,
    compute_outliers_iqr,
    compute_boxplot_data,
    compute_field_analysis,
)


class TestDescriptiveStats:
    def test_basic_numeric_series(self):
        series = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_descriptive_stats(series)

        assert result["count"] == 5
        assert result["missing"] == 0
        assert result["missing_rate"] == 0.0
        assert result["mean"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["q1"] == 2.0
        assert result["median"] == 3.0
        assert result["q3"] == 4.0

    def test_with_missing_values(self):
        series = pl.Series("x", [1.0, None, 3.0, None, 5.0])
        result = compute_descriptive_stats(series)

        assert result["count"] == 5
        assert result["missing"] == 2
        assert result["missing_rate"] == 0.4
        assert result["mean"] == 3.0

    def test_all_missing(self):
        series = pl.Series("x", [None, None, None])
        result = compute_descriptive_stats(series)

        assert result == {}

    def test_empty_series(self):
        series = pl.Series("x", [])
        result = compute_descriptive_stats(series)

        assert result == {}

    def test_single_value(self):
        series = pl.Series("x", [42.0])
        result = compute_descriptive_stats(series)

        assert result["count"] == 1
        assert result["mean"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0
        import math
        # std with ddof=1 is undefined for a single element (0/0)
        assert math.isnan(result["std"])

    def test_skewness_kurtosis(self):
        # Normal distribution-like data should have skewness near 0, kurtosis near 0
        np.random.seed(42)
        data = np.random.normal(0, 1, 1000).tolist()
        series = pl.Series("x", data)
        result = compute_descriptive_stats(series)

        assert abs(result["skewness"]) < 0.2
        assert abs(result["kurtosis"]) < 0.5


class TestHistogram:
    def test_basic_histogram(self):
        series = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_histogram(series)

        assert "bins" in result
        assert "counts" in result
        assert len(result["bins"]) == len(result["counts"]) + 1
        assert sum(result["counts"]) == 5

    def test_all_missing(self):
        series = pl.Series("x", [None, None])
        result = compute_histogram(series)

        assert result["bins"] == []
        assert result["counts"] == []

    def test_custom_bins(self):
        series = pl.Series("x", list(range(100)))
        result = compute_histogram(series, bins=10)

        assert len(result["bins"]) == 11
        assert len(result["counts"]) == 10
        assert sum(result["counts"]) == 100


class TestFrequency:
    def test_basic_frequency(self):
        series = pl.Series("cat", ["a", "b", "a", "c", "b", "a"])
        result = compute_frequency(series)

        assert len(result["categories"]) == 3
        assert len(result["counts"]) == 3
        assert result["total"] == 6
        # 'a' appears 3 times, 'b' appears 2 times, 'c' appears 1 time
        assert sum(result["counts"]) == 6

    def test_all_missing(self):
        series = pl.Series("cat", [None, None])
        result = compute_frequency(series)

        assert result["categories"] == []
        assert result["counts"] == []
        assert result["total"] == 0

    def test_top_n(self):
        values = [str(i % 5) for i in range(100)]
        series = pl.Series("cat", values)
        result = compute_frequency(series, top_n=3)

        assert len(result["categories"]) == 3
        # top_n=3 returns 3 categories, each with 20 items
        assert sum(result["counts"]) == 60


class TestOutliersIQR:
    def test_no_outliers(self):
        series = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_outliers_iqr(series)

        assert result["outlier_count"] == 0

    def test_with_outliers(self):
        # 99 is an obvious outlier against the rest
        series = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0, 99.0])
        result = compute_outliers_iqr(series)

        assert result["outlier_count"] >= 1
        assert 99.0 in result["outlier_values"]

    def test_too_few_values(self):
        series = pl.Series("x", [1.0, 2.0, 3.0])
        result = compute_outliers_iqr(series)

        assert result["outlier_count"] == 0
        assert result["outlier_values"] == []

    def test_all_missing(self):
        series = pl.Series("x", [None, None, None, None])
        result = compute_outliers_iqr(series)

        assert result["outlier_count"] == 0
        assert result["outlier_values"] == []


class TestBoxplot:
    def test_basic_boxplot(self):
        # 1..10 with no outliers
        series = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        result = compute_boxplot_data(series)

        assert result["min"] == 1.0
        assert result["q1"] == 3.25
        assert result["median"] == 5.5
        assert result["q3"] == 7.75
        assert result["max"] == 10.0
        assert result["outlier_count"] == 0
        assert result["outlier_values"] == []

    def test_with_outliers(self):
        # 1..10 with outliers at both ends
        series = pl.Series("x", [-100.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 200.0])
        result = compute_boxplot_data(series)

        # Whiskers should exclude outliers
        assert result["min"] >= 1.0
        assert result["max"] <= 10.0
        assert result["outlier_count"] == 2
        assert -100.0 in result["outlier_values"]
        assert 200.0 in result["outlier_values"]

    def test_too_few_values(self):
        series = pl.Series("x", [1.0, 2.0, 3.0])
        result = compute_boxplot_data(series)

        assert result["min"] is None
        assert result["q1"] is None
        assert result["median"] is None
        assert result["q3"] is None
        assert result["max"] is None
        assert result["outlier_values"] == []
        assert result["outlier_count"] == 0

    def test_all_missing(self):
        series = pl.Series("x", [None, None, None, None])
        result = compute_boxplot_data(series)

        assert result["min"] is None
        assert result["outlier_count"] == 0
        assert result["outlier_values"] == []

    def test_all_identical(self):
        series = pl.Series("x", [5.0, 5.0, 5.0, 5.0, 5.0])
        result = compute_boxplot_data(series)

        assert result["min"] == 5.0
        assert result["q1"] == 5.0
        assert result["median"] == 5.0
        assert result["q3"] == 5.0
        assert result["max"] == 5.0
        assert result["outlier_count"] == 0


class TestFieldAnalysis:
    def test_numeric_field(self):
        df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = compute_field_analysis(df, "x", FieldType.NUMERIC)

        assert result["field_name"] == "x"
        assert result["field_type"] == "numeric"
        assert "stats" in result
        assert "histogram" in result
        assert "outliers" in result
        assert "boxplot" in result
        assert result["boxplot"]["min"] == 1.0
        assert result["boxplot"]["max"] == 5.0

    def test_category_field(self):
        df = pl.DataFrame({"cat": ["a", "b", "a", "c"]})
        result = compute_field_analysis(df, "cat", FieldType.CATEGORY)

        assert result["field_type"] == "category"
        assert "frequency" in result
        assert "stats" not in result

    def test_text_field(self):
        df = pl.DataFrame({"txt": ["hello", "world", "foo"]})
        result = compute_field_analysis(df, "txt", FieldType.TEXT)

        assert result["field_type"] == "text"
        assert "frequency" in result

    def test_boolean_field(self):
        df = pl.DataFrame({"flag": [True, False, True, True]})
        result = compute_field_analysis(df, "flag", FieldType.BOOLEAN)

        assert result["field_type"] == "boolean"
        assert "frequency" in result

    def test_datetime_field(self):
        df = pl.DataFrame({
            "dt": ["2024-01-01", "2024-06-15", "2024-12-31", None]
        }).with_columns(pl.col("dt").str.strptime(pl.Datetime, "%Y-%m-%d"))
        result = compute_field_analysis(df, "dt", FieldType.DATETIME)

        assert result["field_type"] == "datetime"
        assert result["stats"]["count"] == 4
        assert result["stats"]["missing"] == 1
        assert result["stats"]["min"] is not None
        assert result["stats"]["max"] is not None
        assert "2024-01-01" in result["stats"]["min"]
        assert "2024-12-31" in result["stats"]["max"]
        assert "frequency" not in result
        assert "histogram" not in result
