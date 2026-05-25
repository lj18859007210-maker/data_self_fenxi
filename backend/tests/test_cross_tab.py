import polars as pl
import numpy as np
import pytest
from app.services.cross_tab import (
    compute_cross_tabulation,
    _compute_contingency,
    _compute_group_stats,
)


class TestCrossTabulationDispatch:
    """Test the dispatch logic of compute_cross_tabulation."""

    def test_two_categorical_fields_dispatches_to_contingency(self):
        df = pl.DataFrame({
            "dept": ["A", "A", "B", "B", "A"],
            "role": ["x", "y", "x", "y", "x"],
        })
        result = compute_cross_tabulation(df, "dept", "role")
        assert result["type"] == "contingency"
        assert result["row_field"] == "dept"
        assert result["col_field"] == "role"

    def test_cat_and_num_dispatches_to_group_stats(self):
        df = pl.DataFrame({
            "dept": ["A", "A", "B", "B", "A"],
            "salary": [100.0, 200.0, 150.0, 250.0, 300.0],
        })
        result = compute_cross_tabulation(df, "dept", "salary")
        assert result["type"] == "group_stats"
        assert result["category_field"] == "dept"
        assert result["numeric_field"] == "salary"

    def test_cat_and_num_reverse_order(self):
        """Should auto-detect which is categorical regardless of parameter order."""
        df = pl.DataFrame({
            "dept": ["A", "A", "B", "B", "A"],
            "salary": [100.0, 200.0, 150.0, 250.0, 300.0],
        })
        result = compute_cross_tabulation(df, "salary", "dept")
        assert result["type"] == "group_stats"
        assert result["category_field"] == "dept"
        assert result["numeric_field"] == "salary"

    def test_both_numeric_returns_error(self):
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "b": [4.0, 5.0, 6.0],
        })
        result = compute_cross_tabulation(df, "a", "b")
        assert result["type"] == "error"

    def test_both_integer_numeric_returns_error(self):
        df = pl.DataFrame({
            "a": [1, 2, 3],
            "b": [4, 5, 6],
        })
        result = compute_cross_tabulation(df, "a", "b")
        assert result["type"] == "error"


class TestComputeContingency:
    """Test chi-square contingency table."""

    def test_basic_contingency(self):
        df = pl.DataFrame({
            "dept": ["A", "A", "B", "B", "A"],
            "role": ["x", "y", "x", "y", "x"],
        })
        result = _compute_contingency(df, "dept", "role", top_n=10)

        assert result["type"] == "contingency"
        assert result["row_field"] == "dept"
        assert result["col_field"] == "role"

        # row_categories: A(3), B(2) — sorted by freq desc
        assert result["row_categories"] == ["A", "B"]
        # col_categories: x(3), y(2)
        assert result["col_categories"] == ["x", "y"]

        # Matrix: A-x=2, A-y=1, B-x=1, B-y=1
        assert result["matrix"] == [[2, 1], [1, 1]]

        # chi2 should be a small positive number
        assert result["chi2"] is not None
        assert result["chi2"] >= 0
        assert result["p_value"] is not None
        assert result["cramers_v"] is not None
        assert 0 <= result["cramers_v"] <= 1

    def test_independent_fields(self):
        """Perfectly independent distribution -> low chi2, high p-value."""
        np.random.seed(42)
        rows = []
        for _ in range(200):
            rows.append({"a": np.random.choice(["X", "Y", "Z"]),
                         "b": np.random.choice(["P", "Q"])})
        df = pl.DataFrame(rows)
        result = _compute_contingency(df, "a", "b", top_n=10)

        # For random independent variables, p-value should be > 0.05 typically
        assert result["chi2"] is not None
        assert result["p_value"] is not None
        assert result["p_value"] > 0.01  # generous threshold

    def test_dependent_fields(self):
        """Fields with perfect dependency should yield high chi2."""
        df = pl.DataFrame({
            "a": ["X", "X", "Y", "Y", "Z", "Z"],
            "b": ["P", "P", "Q", "Q", "P", "P"],  # Z and P co-occur often
        })
        result = _compute_contingency(df, "a", "b", top_n=10)

        assert result["chi2"] is not None
        assert result["chi2"] > 0

    def test_single_category_returns_empty_stats(self):
        """When only one unique value per field, chi2 cannot be computed."""
        df = pl.DataFrame({
            "a": ["X", "X", "X"],
            "b": ["Y", "Y", "Y"],
        })
        result = _compute_contingency(df, "a", "b", top_n=10)

        assert result["row_categories"] == ["X"]
        assert result["col_categories"] == ["Y"]
        assert result["matrix"] == [[3]]
        assert result["chi2"] is None
        assert result["p_value"] is None
        assert result["cramers_v"] is None

    def test_top_n_limits_categories(self):
        """top_n should limit the number of categories used."""
        df = pl.DataFrame({
            "a": ["A", "B", "C", "D", "E"] + ["A"] * 10,
            "b": ["X", "X", "X", "X", "X"] + ["Y"] * 10,
        })
        result = _compute_contingency(df, "a", "b", top_n=3)

        # Only top 3 categories of 'a' by frequency: A(11), B(1), C(1)
        assert len(result["row_categories"]) <= 3
        assert "A" in result["row_categories"]

    def test_all_same_category(self):
        """All rows have the same category in both fields -> single cell matrix."""
        df = pl.DataFrame({
            "a": ["X", "X", "X"],
            "b": ["Y", "Y", "Y"],
        })
        result = _compute_contingency(df, "a", "b", top_n=10)

        assert len(result["row_categories"]) == 1
        assert len(result["col_categories"]) == 1
        assert result["matrix"] == [[3]]
        # chi2 requires at least 2x2, so should be None
        assert result["chi2"] is None

    def test_empty_dataframe(self):
        df = pl.DataFrame({"a": [], "b": []}, schema={"a": pl.Utf8, "b": pl.Utf8})
        result = _compute_contingency(df, "a", "b", top_n=10)

        assert result["row_categories"] == []
        assert result["col_categories"] == []
        assert result["matrix"] == []
        assert result["chi2"] is None


class TestComputeGroupStats:
    """Test ANOVA group statistics."""

    def test_basic_group_stats(self):
        df = pl.DataFrame({
            "group": ["A", "A", "A", "B", "B", "B"],
            "value": [10.0, 12.0, 11.0, 20.0, 22.0, 21.0],
        })
        result = _compute_group_stats(df, "group", "value", top_n=10)

        assert result["type"] == "group_stats"
        assert result["category_field"] == "group"
        assert result["numeric_field"] == "value"

        assert len(result["groups"]) == 2
        # Group A: mean=11, Group B: mean=21
        grp_a = next(g for g in result["groups"] if g["category"] == "A")
        grp_b = next(g for g in result["groups"] if g["category"] == "B")
        assert grp_a["mean"] == pytest.approx(11.0, abs=0.01)
        assert grp_b["mean"] == pytest.approx(21.0, abs=0.01)

        # ANOVA should show significant difference
        assert result["anova_f"] is not None
        assert result["anova_f"] > 0
        assert result["anova_p"] is not None
        assert result["anova_p"] < 0.05  # clearly different groups
        assert result["eta_squared"] is not None
        assert 0 < result["eta_squared"] <= 1

    def test_no_significant_difference(self):
        """Groups with similar means should yield low F, high p-value."""
        np.random.seed(42)
        rows = []
        for g in ["A", "B"]:
            for v in np.random.normal(0, 1, 50):
                rows.append({"group": g, "value": v})
        df = pl.DataFrame(rows)
        result = _compute_group_stats(df, "group", "value", top_n=10)

        assert result["anova_f"] is not None
        assert result["anova_p"] > 0.01  # no significant difference

    def test_single_group_no_anova(self):
        """With only one group, ANOVA is impossible."""
        df = pl.DataFrame({
            "group": ["A", "A", "A"],
            "value": [1.0, 2.0, 3.0],
        })
        result = _compute_group_stats(df, "group", "value", top_n=10)

        assert len(result["groups"]) == 1
        assert result["anova_f"] is None
        assert result["anova_p"] is None
        assert result["eta_squared"] is None

    def test_with_null_numeric_values(self):
        """Nulls in the numeric field should be dropped per group."""
        df = pl.DataFrame({
            "group": ["A", "A", "A", "B", "B", "B"],
            "value": [10.0, None, 12.0, 20.0, None, 22.0],
        })
        result = _compute_group_stats(df, "group", "value", top_n=10)

        grp_a = next(g for g in result["groups"] if g["category"] == "A")
        grp_b = next(g for g in result["groups"] if g["category"] == "B")
        assert grp_a["count"] == 2  # one null dropped
        assert grp_b["count"] == 2
        assert grp_a["mean"] == pytest.approx(11.0, abs=0.01)
        assert grp_b["mean"] == pytest.approx(21.0, abs=0.01)

    def test_group_with_all_nulls(self):
        """A group where all numeric values are null should be skipped."""
        df = pl.DataFrame({
            "group": ["A", "A", "B", "B", "B"],
            "value": [None, None, 20.0, 22.0, 21.0],
        })
        result = _compute_group_stats(df, "group", "value", top_n=10)

        # Group A should not appear (all nulls -> no valid values)
        categories = [g["category"] for g in result["groups"]]
        assert "A" not in categories
        assert "B" in categories

        # Only one group valid -> no ANOVA
        assert result["anova_f"] is None

    def test_top_n_limits_groups(self):
        df = pl.DataFrame({
            "g": ["A", "B", "C", "D", "E"] + ["A"] * 10,
            "v": [1.0, 2.0, 3.0, 4.0, 5.0] + [1.5] * 10,
        })
        result = _compute_group_stats(df, "g", "v", top_n=3)

        # Only top 3 groups by frequency
        categories = [g["category"] for g in result["groups"]]
        assert len(categories) <= 3
        assert "A" in categories

    def test_group_stats_std_deviation(self):
        """Group stats should include correct std, min, max."""
        df = pl.DataFrame({
            "group": ["A", "A", "A", "A"],
            "value": [1.0, 2.0, 3.0, 4.0],
        })
        result = _compute_group_stats(df, "group", "value", top_n=10)

        grp_a = result["groups"][0]
        assert grp_a["count"] == 4
        assert grp_a["mean"] == 2.5
        assert grp_a["min"] == 1.0
        assert grp_a["max"] == 4.0
        # std with ddof=1: sqrt(((1-2.5)^2 + (2-2.5)^2 + (3-2.5)^2 + (4-2.5)^2) / 3)
        assert grp_a["std"] == pytest.approx(1.29099, abs=0.01)
