"""Tests for chart_recommender.py — smart chart recommendation engine."""

from app.models.session import FieldInfo, FieldType
from app.services.chart_recommender import recommend_charts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _field(name: str, display_type: FieldType) -> FieldInfo:
    return FieldInfo(
        name=name,
        inferred_type=display_type,
        display_type=display_type,
    )


def _num(name: str) -> FieldInfo:
    return _field(name, FieldType.NUMERIC)


def _cat(name: str) -> FieldInfo:
    return _field(name, FieldType.CATEGORY)


def _text(name: str) -> FieldInfo:
    return _field(name, FieldType.TEXT)


def _dt(name: str) -> FieldInfo:
    return _field(name, FieldType.DATETIME)


def _bool(name: str) -> FieldInfo:
    return _field(name, FieldType.BOOLEAN)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_fields(self):
        """Empty fields list with no analyses returns empty list."""
        charts = recommend_charts([], {})
        assert charts == []

    def test_no_analysis_data(self):
        """Fields present but no analysis data should not crash."""
        fields = [_num("x"), _cat("g")]
        charts = recommend_charts(fields, {})
        # Crosstab charts don't need analysis data, so some charts will be produced
        assert isinstance(charts, list)
        assert len(charts) > 0

    def test_analysis_without_matching_field(self):
        """Analysis data for non-existent fields should be ignored."""
        fields = [_num("x")]
        analyses = {"phantom": {"histogram": {"bins": [1, 2]}}}
        charts = recommend_charts(fields, analyses)
        # "x" has no histogram data, so no numeric charts
        assert len(charts) == 0

    def test_single_numeric_no_analysis(self):
        """Single numeric field without analysis keys should not produce charts."""
        fields = [_num("x")]
        analyses = {"x": {"stats": {"mean": 5.0}}}
        charts = recommend_charts(fields, analyses)
        # No histogram or boxplot keys in analysis
        assert len(charts) == 0


# ---------------------------------------------------------------------------
# Numeric distribution — histogram
# ---------------------------------------------------------------------------

class TestHistogram:
    def test_single_numeric_with_histogram(self):
        """A single numeric field with histogram data should produce a histogram chart."""
        fields = [_num("x")]
        analyses = {
            "x": {
                "histogram": {"bins": [1, 2, 3], "counts": [4, 5]},
                "stats": {"mean": 2.0},
            }
        }
        charts = recommend_charts(fields, analyses)
        hist_charts = [c for c in charts if c["type"] == "histogram"]
        assert len(hist_charts) == 1
        assert hist_charts[0]["field"] == "x"
        assert hist_charts[0]["id"] == "hist_x"
        assert hist_charts[0]["priority"] == 90
        assert hist_charts[0]["stats"] == {"mean": 2.0}
        assert hist_charts[0]["data"] == {"bins": [1, 2, 3], "counts": [4, 5]}

    def test_multiple_numeric_fields_limited_to_three(self):
        """Only the first 3 numeric fields should produce histogram charts."""
        fields = [_num(f"x{i}") for i in range(5)]
        analyses = {
            f"x{i}": {"histogram": {"bins": [1], "counts": [1]}}
            for i in range(5)
        }
        charts = recommend_charts(fields, analyses)
        hist_charts = [c for c in charts if c["type"] == "histogram"]
        assert len(hist_charts) == 3
        ids = [c["field"] for c in hist_charts]
        assert ids == ["x0", "x1", "x2"]

    def test_numeric_without_histogram_skips(self):
        """Numeric field without histogram key should not produce histogram chart."""
        fields = [_num("x")]
        analyses = {"x": {"boxplot": {"min": 0, "max": 10}}}
        charts = recommend_charts(fields, analyses)
        hist_charts = [c for c in charts if c["type"] == "histogram"]
        assert len(hist_charts) == 0


# ---------------------------------------------------------------------------
# Numeric distribution — boxplot
# ---------------------------------------------------------------------------

class TestBoxplot:
    def test_numeric_with_boxplot(self):
        """A numeric field with boxplot data should produce a boxplot chart."""
        fields = [_num("x")]
        analyses = {"x": {"boxplot": {"min": 0, "q1": 2, "median": 5, "q3": 8, "max": 10}}}
        charts = recommend_charts(fields, analyses)
        box_charts = [c for c in charts if c["type"] == "boxplot"]
        assert len(box_charts) == 1
        assert box_charts[0]["field"] == "x"
        assert box_charts[0]["priority"] == 85

    def test_boxplot_without_histogram_still_appears(self):
        """Boxplot chart should appear even without histogram data."""
        fields = [_num("x")]
        analyses = {"x": {"boxplot": {"min": 0, "max": 10}}}
        charts = recommend_charts(fields, analyses)
        assert any(c["type"] == "boxplot" for c in charts)


# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------

class TestCorrelationHeatmap:
    def test_two_numeric_fields_produces_heatmap(self):
        """At least 2 numeric fields should produce a correlation heatmap entry."""
        fields = [_num("x"), _num("y")]
        charts = recommend_charts(fields, {})
        heatmaps = [c for c in charts if c["type"] == "heatmap"]
        assert len(heatmaps) == 1
        assert heatmaps[0]["id"] == "corr_matrix"
        assert heatmaps[0]["priority"] == 88

    def test_single_numeric_no_heatmap(self):
        """Only 1 numeric field should NOT produce a heatmap."""
        fields = [_num("x")]
        charts = recommend_charts(fields, {})
        heatmaps = [c for c in charts if c["type"] == "heatmap"]
        assert len(heatmaps) == 0

    def test_no_numeric_fields_no_heatmap(self):
        """No numeric fields should NOT produce a heatmap."""
        fields = [_cat("g"), _text("t")]
        charts = recommend_charts(fields, {})
        heatmaps = [c for c in charts if c["type"] == "heatmap"]
        assert len(heatmaps) == 0


# ---------------------------------------------------------------------------
# Category / Text frequency
# ---------------------------------------------------------------------------

class TestFrequency:
    def test_category_with_frequency_pie(self):
        """Category field with <=8 categories should produce a pie chart."""
        fields = [_cat("g")]
        analyses = {
            "g": {"frequency": {"categories": ["A", "B", "C"], "counts": [10, 20, 30]}}
        }
        charts = recommend_charts(fields, analyses)
        pie_charts = [c for c in charts if c["type"] == "pie"]
        assert len(pie_charts) == 1
        assert pie_charts[0]["field"] == "g"
        assert pie_charts[0]["priority"] == 80

    def test_text_with_frequency_pie(self):
        """Text field with frequency data should also produce a pie chart."""
        fields = [_text("t")]
        analyses = {
            "t": {"frequency": {"categories": ["hello", "world"], "counts": [15, 5]}}
        }
        charts = recommend_charts(fields, analyses)
        pie_charts = [c for c in charts if c["type"] == "pie"]
        assert len(pie_charts) == 1

    def test_many_categories_uses_bar(self):
        """Category field with >8 categories should produce a bar chart."""
        categories = [f"cat_{i}" for i in range(10)]
        fields = [_cat("g")]
        analyses = {
            "g": {"frequency": {"categories": categories, "counts": list(range(10, 0, -1))}}
        }
        charts = recommend_charts(fields, analyses)
        bar_charts = [c for c in charts if c["type"] == "bar"]
        assert len(bar_charts) == 1
        assert bar_charts[0]["priority"] == 70

    def test_exactly_eight_categories_uses_pie(self):
        """Category field with exactly 8 categories should use pie chart."""
        categories = [f"cat_{i}" for i in range(8)]
        fields = [_cat("g")]
        analyses = {
            "g": {"frequency": {"categories": categories, "counts": list(range(8))}}
        }
        charts = recommend_charts(fields, analyses)
        assert any(c["type"] == "pie" for c in charts)
        assert not any(c["type"] == "bar" for c in charts)

    def test_category_without_frequency_skips(self):
        """Category field without frequency key should not produce a frequency chart."""
        fields = [_cat("g")]
        analyses = {"g": {}}
        charts = recommend_charts(fields, analyses)
        freq_charts = [c for c in charts if c["type"] in ("pie", "bar")]
        assert len(freq_charts) == 0

    def test_at_most_five_category_fields(self):
        """Only the first 5 category/text fields should produce frequency charts."""
        fields = [_cat(f"g{i}") for i in range(7)]
        analyses = {
            f"g{i}": {"frequency": {"categories": ["A", "B"], "counts": [1, 2]}}
            for i in range(7)
        }
        charts = recommend_charts(fields, analyses)
        freq_charts = [c for c in charts if c["type"] in ("pie", "bar")]
        assert len(freq_charts) == 5


# ---------------------------------------------------------------------------
# Time series
# ---------------------------------------------------------------------------

class TestTimeSeries:
    def test_time_and_numeric_produces_timeseries(self):
        """At least one datetime and one numeric field should produce time series charts."""
        fields = [_dt("date"), _num("value")]
        charts = recommend_charts(fields, {})
        ts_charts = [c for c in charts if c["type"] == "timeseries"]
        assert len(ts_charts) == 1
        assert ts_charts[0]["id"] == "ts_date_value"
        assert ts_charts[0]["priority"] == 75

    def test_time_with_two_numerics(self):
        """One datetime with two numeric fields should produce two time series (at most)."""
        fields = [_dt("date"), _num("a"), _num("b")]
        charts = recommend_charts(fields, {})
        ts_charts = [c for c in charts if c["type"] == "timeseries"]
        assert len(ts_charts) == 2
        ids = {c["id"] for c in ts_charts}
        assert ids == {"ts_date_a", "ts_date_b"}

    def test_only_first_time_field_used(self):
        """Only the first datetime field should be used for time series."""
        fields = [_dt("date1"), _dt("date2"), _num("value")]
        charts = recommend_charts(fields, {})
        ts_charts = [c for c in charts if c["type"] == "timeseries"]
        assert all("date1" in c["id"] for c in ts_charts)
        assert not any("date2" in c["id"] for c in ts_charts)

    def test_no_numeric_no_timeseries(self):
        """Datetime field without numeric fields should not produce timeseries."""
        fields = [_dt("date")]
        charts = recommend_charts(fields, {})
        ts_charts = [c for c in charts if c["type"] == "timeseries"]
        assert len(ts_charts) == 0

    def test_no_datetime_no_timeseries(self):
        """Numeric fields without datetime should not produce timeseries."""
        fields = [_num("x")]
        charts = recommend_charts(fields, {})
        ts_charts = [c for c in charts if c["type"] == "timeseries"]
        assert len(ts_charts) == 0


# ---------------------------------------------------------------------------
# Category vs Numeric (crosstab)
# ---------------------------------------------------------------------------

class TestCategoryNumericCrosstab:
    def test_category_and_numeric_produces_crosstab(self):
        """At least one category and numeric should produce crosstab charts."""
        fields = [_cat("g"), _num("value")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 1
        assert cross_charts[0]["id"] == "cmp_g_value"
        assert cross_charts[0]["priority"] == 65

    def test_text_field_also_triggers_crosstab(self):
        """Text field (not just category) should also trigger crosstab charts."""
        fields = [_text("desc"), _num("score")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 1

    def test_boolean_does_not_trigger_crosstab(self):
        """Boolean field should NOT trigger crosstab charts (not in category/text list)."""
        fields = [_bool("flag"), _num("score")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 0

    def test_multiple_categories_and_numerics_limited(self):
        """At most 2 categories x 2 numerics = 4 crosstab charts."""
        fields = [_cat(f"g{i}") for i in range(3)] + [_num(f"v{i}") for i in range(3)]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) <= 4

    def test_no_numeric_no_crosstab(self):
        """Category without numeric should not produce crosstab."""
        fields = [_cat("g")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 0

    def test_no_category_no_crosstab(self):
        """Numeric without category should not produce crosstab."""
        fields = [_num("x")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 0


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_charts_sorted_by_priority_descending(self):
        """Charts should be sorted by priority descending."""
        fields = [_dt("date"), _num("x"), _cat("g")]
        analyses = {
            "x": {"histogram": {"bins": [1], "counts": [1]}},
            "g": {"frequency": {"categories": ["A", "B"], "counts": [1, 2]}},
        }
        charts = recommend_charts(fields, analyses)
        priorities = [c["priority"] for c in charts]
        assert priorities == sorted(priorities, reverse=True)

    def test_histogram_highest_priority(self):
        """Histogram (90) should be highest priority when present."""
        fields = [_num("x")]
        analyses = {"x": {"histogram": {"bins": [1], "counts": [1]}}}
        charts = recommend_charts(fields, analyses)
        assert charts[0]["priority"] == 90


# ---------------------------------------------------------------------------
# Boolean fields interaction
# ---------------------------------------------------------------------------

class TestBooleanFields:
    def test_boolean_does_not_produce_frequency_chart(self):
        """Boolean fields do not appear in cat_fields and thus no frequency chart."""
        fields = [_bool("flag")]
        analyses = {"flag": {"frequency": {"categories": [True, False], "counts": [5, 5]}}}
        charts = recommend_charts(fields, analyses)
        freq_charts = [c for c in charts if c["type"] in ("pie", "bar")]
        assert len(freq_charts) == 0

    def test_boolean_not_counted_as_category_for_flags(self):
        """Boolean-only fields should not set has_category for crosstab."""
        fields = [_bool("flag"), _num("x")]
        charts = recommend_charts(fields, {})
        cross_charts = [c for c in charts if c["type"] == "crosstab"]
        assert len(cross_charts) == 0


# ---------------------------------------------------------------------------
# Integration — mixed field types
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_rich_dataset_produces_multiple_chart_types(self):
        """A rich dataset should produce multiple distinct chart types."""
        fields = [
            _num("age"),
            _num("salary"),
            _cat("department"),
            _dt("date"),
            _text("notes"),
        ]
        analyses = {
            "age": {
                "histogram": {"bins": [20, 40, 60], "counts": [5, 10]},
                "boxplot": {"min": 18, "q1": 25, "median": 35, "q3": 45, "max": 65},
            },
            "salary": {
                "histogram": {"bins": [30, 50, 70], "counts": [7, 8]},
            },
            "department": {
                "frequency": {"categories": ["Eng", "Sales", "HR"], "counts": [20, 15, 10]},
            },
            "notes": {
                "frequency": {"categories": ["note1", "note2"], "counts": [3, 4]},
            },
        }
        charts = recommend_charts(fields, analyses)
        types = {c["type"] for c in charts}

        assert "histogram" in types
        assert "boxplot" in types
        assert "heatmap" in types
        assert "pie" in types  # department has 3 categories
        assert "timeseries" in types
        assert "crosstab" in types

        # 2 histogram + 1 boxplot + 1 heatmap + 2 pie (dept + notes) + 2 timeseries + 4 crosstab
        assert len(charts) == 12

    def test_boolean_field_does_not_crash_or_produce_charts(self):
        """Boolean fields should not cause errors or produce unwanted chart types."""
        fields = [_bool("flag"), _num("x")]
        analyses = {
            "flag": {"frequency": {"categories": [True, False], "counts": [10, 10]}},
            "x": {"histogram": {"bins": [1, 2], "counts": [3]}},
        }
        charts = recommend_charts(fields, analyses)
        types = {c["type"] for c in charts}
        assert "histogram" in types
        assert "pie" not in types
        assert "bar" not in types

    def test_only_text_fields(self):
        """Only text fields should produce only frequency charts."""
        fields = [_text("a"), _text("b")]
        analyses = {
            "a": {"frequency": {"categories": ["x", "y"], "counts": [1, 2]}},
            "b": {"frequency": {"categories": ["p", "q", "r"], "counts": [3, 2, 1]}},
        }
        charts = recommend_charts(fields, analyses)
        types = {c["type"] for c in charts}
        assert types == {"pie"}
        assert len(charts) == 2

    def test_chart_id_uniqueness(self):
        """All chart ids should be unique for a given dataset."""
        fields = [
            _num("age"),
            _num("salary"),
            _cat("dept"),
            _dt("date"),
        ]
        analyses = {
            "age": {
                "histogram": {"bins": [1], "counts": [1]},
                "boxplot": {"min": 0, "max": 10},
            },
            "salary": {
                "histogram": {"bins": [1], "counts": [1]},
            },
            "dept": {
                "frequency": {"categories": ["A", "B"], "counts": [5, 5]},
            },
        }
        charts = recommend_charts(fields, analyses)
        ids = [c["id"] for c in charts]
        assert len(ids) == len(set(ids)), f"Duplicate chart IDs found: {ids}"
