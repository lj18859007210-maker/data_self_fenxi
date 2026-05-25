import tempfile
import os
import pytest
from app.services.nl2sql import parse_nl_query, _find_column


class TestColumnMatching:
    def test_exact_match(self):
        assert _find_column("sales", ["sales", "profit", "date"]) == "sales"

    def test_partial_match(self):
        assert _find_column("销售", ["销售额", "利润", "日期"]) == "销售额"

    def test_case_insensitive(self):
        assert _find_column("SALES", ["sales", "profit"]) == "sales"

    def test_no_match(self):
        assert _find_column("xyz", ["sales", "profit"]) is None


class TestParseNlQuery:
    @pytest.fixture
    def csv_path(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w")
        tmp.write("name,sales,profit,category\n")
        tmp.write("A,100,20,cat1\n")
        tmp.write("B,200,50,cat2\n")
        tmp.write("C,150,30,cat1\n")
        tmp.write("D,300,80,cat3\n")
        tmp.write("E,250,60,cat2\n")
        tmp.close()
        yield tmp.name
        os.unlink(tmp.name)

    def test_top_n_by(self, csv_path):
        result = parse_nl_query("top 3 sales", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count == 3

    def test_top_n_by_desc(self, csv_path):
        result = parse_nl_query("top 2 by sales desc", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count == 2
        # First row should have highest sales (300 / D)
        assert result.rows[0][0] == "D"

    def test_aggregation_by_group(self, csv_path):
        result = parse_nl_query("平均 of sales by category", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count >= 2

    def test_describe_numeric(self, csv_path):
        result = parse_nl_query("describe sales", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count == 1
        assert result.columns == ["count", "avg", "min", "max", "stddev", "median"]

    def test_describe_category(self, csv_path):
        result = parse_nl_query("describe category", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count >= 2

    def test_filter_where(self, csv_path):
        result = parse_nl_query("sales > 200", ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count == 2

    def test_correlation(self, csv_path):
        result = parse_nl_query("correlation between sales and profit",
                                ["name", "sales", "profit", "category"],
                                ["sales", "profit"], csv_path)
        assert result.row_count == 1
        assert "correlation" in result.columns

    def test_unknown_query_raises(self, csv_path):
        with pytest.raises(ValueError, match="无法理解查询"):
            parse_nl_query("xyzzy nonsense query", ["name", "sales"],
                          ["sales"], csv_path)
