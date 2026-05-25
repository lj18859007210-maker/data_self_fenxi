import re
import duckdb
from dataclasses import dataclass, field


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[list]
    row_count: int


_AGG_WORDS = {
    "平均": "AVG", "均值": "AVG", "average": "AVG", "mean": "AVG",
    "总和": "SUM", "合计": "SUM", "sum": "SUM", "total": "SUM",
    "最大": "MAX", "最大值": "MAX", "max": "MAX", "maximum": "MAX",
    "最小": "MIN", "最小值": "MIN", "min": "MIN", "minimum": "MIN",
    "计数": "COUNT", "数量": "COUNT", "count": "COUNT",
    "标准差": "STDDEV", "stddev": "STDDEV",
}

_OP_MAP = {">=": ">=", "<=": "<=", "!=": "!=", ">": ">", "<": "=", "=": "=", "等于": "=", "大于": ">", "小于": "<",
           "不等于": "!=", "大于等于": ">=", "小于等于": "<="}


def parse_nl_query(query: str, columns: list[str], numeric_cols: list[str], file_path: str) -> QueryResult:
    """Parse a natural language query and execute it against the CSV file."""
    q = query.strip().rstrip("。.?？!！")
    q_lower = q.lower()

    # Pattern 1a: "top N [field] by [field]" — full pattern
    m = re.match(r"(?:top|前|显示前?|show)\s*(\d+)\s*(?:个|条)?\s*(.+?)\s*(?:按|按照|by|根据)\s*(.+?)(?:\s*(?:降序|升序|descending|ascending|desc|asc))?$", q_lower, re.IGNORECASE)
    if m:
        limit = int(m.group(1))
        target = _find_column(m.group(2).strip(), columns)
        order_by = _find_column(m.group(3).strip(), columns)
        if target and order_by:
            direction = "DESC" if any(w in q_lower for w in ["降序", "desc", "最大", "最高", "最多"]) else "ASC"
            sql = f'SELECT * FROM df ORDER BY "{order_by}" {direction} LIMIT {limit}'
            return _execute(sql, file_path)

    # Pattern 1b: "top N by [field]" — no target, just order
    m = re.match(r"(?:top|前|显示前?|show)\s*(\d+)\s*(?:个|条)?\s*(?:按|按照|by|根据)\s*(.+?)(?:\s*(?:降序|升序|descending|ascending|desc|asc))?$", q_lower, re.IGNORECASE)
    if m:
        limit = int(m.group(1))
        order_by = _find_column(m.group(2).strip(), columns)
        if order_by:
            direction = "DESC" if any(w in q_lower for w in ["降序", "desc", "最大", "最高", "最多"]) else "ASC"
            sql = f'SELECT * FROM df ORDER BY "{order_by}" {direction} LIMIT {limit}'
            return _execute(sql, file_path)

    # Pattern 1c: "top N [field]" — simple top N by field desc
    m = re.match(r"(?:top|前|显示前?|show)\s*(\d+)\s+(.+?)$", q_lower, re.IGNORECASE)
    if m:
        limit = int(m.group(1))
        order_by = _find_column(m.group(2).strip(), columns)
        if order_by:
            sql = f'SELECT * FROM df ORDER BY "{order_by}" DESC LIMIT {limit}'
            return _execute(sql, file_path)

    # Pattern 2: "agg of X by/grouped by Y" — aggregation with group by
    m = re.match(r"(?:show\s+)?(?:the\s+)?(平均|均值|average|mean|总和|合计|sum|total|最大|最大值|max|最小|最小值|min|计数|数量|count|标准差|stddev)\s*(?:of\s+)?(.+?)\s*(?:by|grouped\s+by|按|根据|分组)\s+(.+)", q_lower, re.IGNORECASE)
    if m:
        agg_word = m.group(1).lower()
        target = _find_column(m.group(2).strip(), columns)
        group_by = _find_column(m.group(3).strip(), columns)
        if agg_word and target and group_by:
            agg_func = _AGG_WORDS.get(agg_word, "AVG")
            sql = f'SELECT "{group_by}", {agg_func}("{target}") AS {agg_func.lower()}_{target[:8]} FROM df GROUP BY "{group_by}" ORDER BY {agg_func.lower()}_{target[:8]} DESC'
            return _execute(sql, file_path)

    # Pattern 3: "where X > value" — filter
    m = re.match(r"(?:show\s+)?(?:the\s+)?(.+?)\s*(>=|<=|!=|>|<|=|等于|大于|小于|不等于|大于等于|小于等于)\s*(.+?)(?:\s+(?:的|of))?\s*(?:数据|记录|records|data)?$", q_lower, re.IGNORECASE)
    op_match = m.group(2) if m else None
    if m and op_match:
        field = _find_column(m.group(1).strip(), columns)
        value = m.group(3).strip().strip("'\"")
        op = _OP_MAP.get(op_match, "=")
        if field:
            try:
                float(value)
                sql = f'SELECT * FROM df WHERE "{field}" {op} {value}'
            except ValueError:
                sql = f"SELECT * FROM df WHERE \"{field}\" {op} '{value}'"
            return _execute(sql, file_path)

    # Pattern 4: "correlation between X and Y"
    m = re.match(r"(?:show\s+)?(?:the\s+)?(?:correlation|相关性|关联)\s*(?:between|在|of)?\s*(.+?)\s*(?:and|和|与|,)\s*(.+)", q_lower, re.IGNORECASE)
    if m:
        f1 = _find_column(m.group(1).strip(), numeric_cols)
        f2 = _find_column(m.group(2).strip(), numeric_cols)
        if f1 and f2:
            sql = f'SELECT CORR("{f1}", "{f2}") AS correlation FROM df'
            return _execute(sql, file_path)

    # Pattern 5: "describe/show/distribution of X" — summary stats
    m = re.match(r"(?:show\s+)?(?:the\s+)?(?:describe|分布|distribution|统计|stats|概要|summary)\s*(?:of\s+)?(.+)", q_lower, re.IGNORECASE)
    if m:
        field = _find_column(m.group(1).strip(), columns)
        if field:
            if field in numeric_cols:
                sql = f'SELECT COUNT("{field}") AS count, AVG("{field}") AS avg, MIN("{field}") AS min, MAX("{field}") AS max, STDDEV("{field}") AS stddev, QUANTILE_CONT("{field}", 0.5) AS median FROM df'
            else:
                sql = f'SELECT "{field}", COUNT(*) AS count FROM df GROUP BY "{field}" ORDER BY count DESC LIMIT 20'
            return _execute(sql, file_path)

    raise ValueError(f"无法理解查询: '{query}'。支持的查询模式: top N 列 by 列, 聚合 of 列 by 列, where 条件, correlation between 列 and 列, describe 列")


def _find_column(token: str, columns: list[str]) -> str | None:
    """Find the best matching column name for a natural language token."""
    token_lower = token.strip().lower().strip("'\"")
    for col in columns:
        if col.lower() == token_lower:
            return col
    for col in columns:
        if token_lower in col.lower() or col.lower() in token_lower:
            return col
    return None


def _execute(sql: str, file_path: str) -> QueryResult:
    conn = duckdb.connect()
    try:
        ext = file_path.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            conn.execute(f"CREATE VIEW df AS SELECT * FROM read_csv_auto('{file_path}')")
        else:
            conn.execute(f"CREATE VIEW df AS SELECT * FROM read_excel('{file_path}')")
        result = conn.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
        return QueryResult(sql=sql, columns=columns, rows=[list(r) for r in rows], row_count=len(rows))
    finally:
        conn.close()
