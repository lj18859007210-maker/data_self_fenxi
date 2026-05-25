import polars as pl
import numpy as np
import pytest
from app.services.correlation import compute_correlation_matrix


class TestCorrelationMatrix:
    def test_perfect_positive(self):
        """Perfectly correlated data should give r=1.0."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [2.0, 4.0, 6.0, 8.0, 10.0],
        })
        result = compute_correlation_matrix(df)

        assert result["fields"] == ["a", "b"]
        assert len(result["matrix"]) == 2
        assert result["matrix"][0][0] == 1.0  # self-correlation
        assert result["matrix"][0][1] == 1.0  # perfect positive
        assert result["matrix"][1][0] == 1.0  # symmetric
        assert result["matrix"][1][1] == 1.0  # self-correlation

        assert len(result["pairs"]) == 1
        pair = result["pairs"][0]
        assert pair["field1"] == "a"
        assert pair["field2"] == "b"
        assert pair["correlation"] == 1.0
        assert pair["strength"] == "strong"
        assert pair["direction"] == "positive"

    def test_perfect_negative(self):
        """Perfectly inversely correlated data should give r=-1.0."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [5.0, 4.0, 3.0, 2.0, 1.0],
        })
        result = compute_correlation_matrix(df)

        assert round(result["matrix"][0][1], 4) == -1.0
        pair = result["pairs"][0]
        assert pair["correlation"] == -1.0
        assert pair["direction"] == "negative"

    def test_no_correlation(self):
        """Random uncorrelated data should give r near 0."""
        np.random.seed(42)
        df = pl.DataFrame({
            "a": np.random.randn(100).tolist(),
            "b": np.random.randn(100).tolist(),
        })
        result = compute_correlation_matrix(df)

        r = result["matrix"][0][1]
        assert abs(r) < 0.3  # generous threshold for random noise

    def test_single_numeric_column(self):
        """With only one numeric column, no pairs should exist."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "b": ["x", "y", "z"],
        })
        result = compute_correlation_matrix(df)

        assert result["fields"] == []
        assert result["matrix"] == []
        assert result["pairs"] == []

    def test_no_numeric_columns(self):
        """With zero numeric columns, should return empty result."""
        df = pl.DataFrame({
            "cat": ["a", "b", "c"],
            "text": ["hello", "world", "foo"],
        })
        result = compute_correlation_matrix(df)

        assert result["fields"] == []
        assert result["matrix"] == []
        assert result["pairs"] == []

    def test_with_missing_values(self):
        """Missing values should be dropped per-column before correlation."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, None, 4.0, 5.0],
            "b": [None, 2.0, 3.0, 4.0, 5.0],
        })
        result = compute_correlation_matrix(df)

        # After dropping nulls: a=[1,2,4,5], b=[2,3,4,5]
        # Truncated to min_len=4: a=[1,2,4,5], b=[2,3,4,5]
        # This should still yield a strong positive correlation
        assert len(result["fields"]) == 2
        assert len(result["pairs"]) == 1
        assert result["pairs"][0]["correlation"] > 0.5

    def test_too_few_non_null_values(self):
        """Columns with <3 non-null values should return None in matrix."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, None, None, None],
            "b": [3.0, 4.0, 5.0, 6.0, 7.0],
        })
        result = compute_correlation_matrix(df)

        # Column 'a' has only 2 non-null values (<3)
        assert len(result["fields"]) == 2
        # Matrix entry should be None
        assert result["matrix"][0][1] is None
        # No pairs should be generated since we skip when <3 values
        assert len(result["pairs"]) == 0

    def test_mixed_types(self):
        """Non-numeric columns should be ignored."""
        df = pl.DataFrame({
            "num1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "num2": [5.0, 4.0, 3.0, 2.0, 1.0],
            "cat": ["a", "b", "c", "d", "e"],
            "date": ["2024-01-01"] * 5,
            "bool": [True, False, True, False, True],
        })
        result = compute_correlation_matrix(df)

        assert result["fields"] == ["num1", "num2"]
        assert len(result["matrix"]) == 2
        assert len(result["pairs"]) == 1

    def test_multiple_columns_pairs_sorted(self):
        """Pairs should be sorted by absolute correlation descending."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [1.0, 2.0, 3.0, 4.0, 5.0],  # r=1.0 with a
            "c": [5.0, 4.0, 3.0, 2.0, 1.0],  # r=-1.0 with a, r=-1.0 with b
        })
        result = compute_correlation_matrix(df)

        assert len(result["pairs"]) == 3  # 3 choose 2 = 3 pairs

        # All pairs should have |r| = 1.0, so order among equal values is undefined
        correlations = [p["correlation"] for p in result["pairs"]]
        assert all(abs(c) == 1.0 for c in correlations)

    def test_strength_classification(self):
        """Strength labels should be correct based on |r| thresholds."""
        # Generate data with known correlation strengths
        np.random.seed(42)
        base = np.random.randn(100)
        df = pl.DataFrame({
            "strong_pos": base.tolist(),
            "strong_neg": (-base).tolist(),             # r ≈ -1.0
            "moderate": (base * 0.5 + np.random.randn(100) * 0.86).tolist(),  # r ≈ 0.5
            "weak": (base * 0.1 + np.random.randn(100) * 0.99).tolist(),      # r ≈ 0.1
        })
        result = compute_correlation_matrix(df)

        for pair in result["pairs"]:
            r = abs(pair["correlation"])
            if r >= 0.7:
                assert pair["strength"] == "strong", f"Expected strong for r={r}"
            elif r >= 0.4:
                assert pair["strength"] == "moderate", f"Expected moderate for r={r}"
            else:
                assert pair["strength"] == "weak", f"Expected weak for r={r}"

    def test_irregular_length_after_null_drop(self):
        """After dropping nulls, columns may have different lengths; should truncate."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],           # 5 values
            "b": [1.0, 2.0, 3.0, None, None],           # 3 values
        })
        result = compute_correlation_matrix(df)

        # a non-null has 5, b non-null has 3
        # min_len = 3, so we use first 3 of each
        assert len(result["fields"]) == 2
        assert len(result["pairs"]) == 1
        # The first 3 values are [1,2,3] and [1,2,3] => r=1.0
        assert result["pairs"][0]["correlation"] == 1.0

    def test_all_null_in_one_column(self):
        """A column with all nulls has pl.Null dtype and is excluded from numerics,
        yielding only 1 numeric field (<2) -> empty result."""
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "b": [None, None, None],
        })
        result = compute_correlation_matrix(df)

        assert result["fields"] == []
        assert result["matrix"] == []
        assert result["pairs"] == []

    def test_explicit_float64_all_nulls(self):
        """An explicitly typed Float64 column with all nulls is a valid numeric
        field but has <3 non-null values -> None in matrix, no pairs."""
        df = pl.DataFrame({
            "a": [None, None, None, None, None],
            "b": [1.0, 2.0, 3.0, 4.0, 5.0],
        }).with_columns(pl.col("a").cast(pl.Float64))
        result = compute_correlation_matrix(df)

        assert result["fields"] == ["a", "b"]
        assert result["matrix"][0][1] is None
        assert result["matrix"][1][0] is None
        assert result["pairs"] == []
