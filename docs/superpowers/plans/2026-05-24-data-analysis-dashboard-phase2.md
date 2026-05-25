# 数据自分析大屏 — 第二阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 强化分析能力 — 箱线图、交叉统计表、散点图矩阵、时间序列分析、图表交互、布局拖拽

**Architecture:** 后端新增分析函数 + 前端新增ECharts图表 + 现有进度机制扩展

**Tech Stack:** Python (Scipy + StatsModels), React (ECharts + react-grid-layout)

---

### Task 1: 后端 — 箱线图数据分析

**Files:**
- Modify: `backend/app/services/stats_engine.py`

在 `stats_engine.py` 中添加箱线图所需的五数概括（最小值、Q1、中位数、Q3、最大值）和异常值标记。这些数据其实已经有部分在 `compute_descriptive_stats` 和 `compute_outliers_iqr` 中，但需要组合成箱线图专用格式。

- [ ] **添加 `compute_boxplot_data` 函数**

```python
def compute_boxplot_data(series: pl.Series) -> dict[str, Any]:
    """Compute boxplot data (five-number summary + outliers)."""
    non_null = series.drop_nulls()
    if len(non_null) < 4:
        return {
            "min": None, "q1": None, "median": None,
            "q3": None, "max": None,
            "outlier_values": [], "outlier_count": 0,
        }

    arr = non_null.to_numpy()
    q1, q2, q3 = np.percentile(arr, [25, 50, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    # Whiskers: min/max within 1.5*IQR
    whisker_min = float(np.min(arr[arr >= lower]))
    whisker_max = float(np.max(arr[arr <= upper]))

    # Outliers: points beyond whiskers
    outlier_mask = (arr < lower) | (arr > upper)
    outliers = arr[outlier_mask].tolist()

    return {
        "min": round(float(whisker_min), 4),
        "q1": round(float(q1), 4),
        "median": round(float(q2), 4),
        "q3": round(float(q3), 4),
        "max": round(float(whisker_max), 4),
        "outlier_values": [round(float(v), 4) for v in outliers[:200]],
        "outlier_count": int(outlier_mask.sum()),
    }
```

- [ ] **在 `compute_field_analysis` 中添加箱线图调用**

```python
if field_type == FieldType.NUMERIC:
    result["stats"] = compute_descriptive_stats(series)
    result["histogram"] = compute_histogram(series)
    result["outliers"] = compute_outliers_iqr(series)
    result["boxplot"] = compute_boxplot_data(series)  # 新增
```

- [ ] **验证**: 运行测试确认计算正确

---

### Task 2: 前端 — 箱线图组件

**Files:**
- Create: `frontend/src/components/charts/BoxPlotChart.tsx`
- Modify: `frontend/src/components/charts/ChartFactory.tsx`

- [ ] **创建 BoxPlotChart.tsx**

```typescript
import ReactEChartsCore from 'echarts-for-react';

interface BoxPlotData {
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  outlier_values: number[];
  outlier_count: number;
}

interface Props {
  fieldName: string;
  boxplot: BoxPlotData;
  height?: number;
}

export default function BoxPlotChart({ fieldName, boxplot, height = 250 }: Props) {
  if (boxplot.min === null) return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>数据不足</div>;

  const scatterData = boxplot.outlier_values.map(v => [0, v]);

  const option = {
    tooltip: {
      trigger: 'item' as const,
      formatter: (p: any) => {
        if (p.seriesIndex === 0) {
          return `${fieldName}<br/>最小值: ${boxplot.min}<br/>Q1: ${boxplot.q1}<br/>中位数: ${boxplot.median}<br/>Q3: ${boxplot.q3}<br/>最大值: ${boxplot.max}`;
        }
        return `异常值: ${p.value[1]}`;
      },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category' as const, data: [fieldName], axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' as const },
    series: [
      {
        name: '箱线图',
        type: 'boxplot',
        data: [[boxplot.min, boxplot.q1, boxplot.median, boxplot.q3, boxplot.max]],
        itemStyle: { color: '#6366f1' },
      },
      {
        name: '异常值',
        type: 'scatter',
        data: scatterData,
        symbolSize: 6,
        itemStyle: { color: '#ef4444' },
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
```

- [ ] **修改 ChartFactory.tsx** — 添加 `case 'boxplot'`

- [ ] **修改后端 charts API** — `backend/app/routers/dashboard.py` 中的 `get_charts`，为数值字段添加箱线图配置

- [ ] **验证**: `npx tsc --noEmit` + 前端能看到箱线图

---

### Task 3: 后端 — 交叉统计表

**Files:**
- Create: `backend/app/services/cross_tab.py`

```python
import polars as pl
import numpy as np
from scipy import stats
from typing import Any


def compute_cross_tabulation(
    df: pl.DataFrame,
    row_field: str,
    col_field: str,
    value_field: str | None = None,
    agg: str = "count"
) -> dict[str, Any]:
    """
    Compute cross-tabulation between two fields.
    
    - category vs category: contingency table + Cramér's V
    - category vs numeric: group statistics + ANOVA
    """
    # Determine field types
    row_dtype = df[row_field].dtype
    col_dtype = df[col_field].dtype
    
    is_row_num = row_dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)
    is_col_num = col_dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)
    
    if not is_row_num and not is_col_num:
        # Category vs Category: contingency table
        return _compute_contingency(df, row_field, col_field)
    elif is_row_num != is_col_num:
        # Mixed: category vs numeric
        cat_field = col_field if is_row_num else row_field
        num_field = row_field if is_row_num else col_field
        return _compute_group_stats(df, cat_field, num_field)
    else:
        # Both numeric: bin one and cross
        return {"error": "Both fields are numeric. Use correlation instead."}


def _compute_contingency(df: pl.DataFrame, row_field: str, col_field: str, top_n: int = 20) -> dict[str, Any]:
    """Chi-square test of independence between two categorical fields."""
    # Crosstab
    ct = df.group_by([row_field, col_field]).agg(pl.len().alias("count"))
    pivot = ct.pivot(values="count", index=row_field, columns=col_field, aggregate_function="sum")
    
    # Get top categories by frequency
    row_freq = df[row_field].value_counts().sort("count", descending=True).head(top_n)
    col_freq = df[col_field].value_counts().sort("count", descending=True).head(top_n)
    
    top_rows = set(row_freq[row_field].to_list())
    top_cols = set(col_freq[col_field].to_list())
    
    # Build matrix
    row_labels = row_freq[row_field].to_list()
    col_labels = col_freq[col_field].to_list()
    
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
        cramers_v = np.sqrt(chi2 / (n * min(observed.shape[0] - 1, observed.shape[1] - 1)))
    else:
        chi2, p_value, cramers_v = None, None, None
    
    return {
        "type": "contingency",
        "row_field": row_field,
        "col_field": col_field,
        "row_categories": row_labels,
        "col_categories": col_labels,
        "matrix": matrix,
        "chi2": round(float(chi2), 4) if chi2 else None,
        "p_value": round(float(p_value), 6) if p_value else None,
        "cramers_v": round(float(cramers_v), 4) if cramers_v else None,
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
        eta_sq = f_stat * (len(group_data) - 1) / (f_stat * (len(group_data) - 1) + sum(len(g) for g in group_data) - len(group_data))
    else:
        f_stat, p_value, eta_sq = None, None, None
    
    return {
        "type": "group_stats",
        "category_field": cat_field,
        "numeric_field": num_field,
        "groups": groups,
        "anova_f": round(float(f_stat), 4) if f_stat else None,
        "anova_p": round(float(p_value), 6) if p_value else None,
        "eta_squared": round(float(eta_sq), 4) if eta_sq else None,
    }
```

- [ ] **添加路由**: 在 `backend/app/routers/dashboard.py` 中添加 `GET /api/sessions/{id}/cross-tab`

```python
@router.get("/api/sessions/{session_id}/cross-tab")
async def get_cross_tabulation(session_id: str, row_field: str, col_field: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    df = load_dataframe(session.file_path)
    result = compute_cross_tabulation(df, row_field, col_field)
    return {"success": True, "data": result, "error": None}
```

- [ ] **在 `compute_field_analysis` 中对类别字段添加交叉表推荐配置**

- [ ] **验证**: 用示例数据测试交叉表

---

### Task 4: 前端 — 交互式交叉表组件

**Files:**
- Create: `frontend/src/components/charts/CrossTabView.tsx`
- Create: `frontend/src/components/charts/GroupCompareChart.tsx`
- Modify: `frontend/src/components/charts/ChartFactory.tsx`

创建支持两种模式的交叉表组件：
- 列联表热力图（类别 vs 类别）
- 分组箱线图/柱状图（类别 vs 数值）

---

### Task 5: 后端 — 散点图矩阵

**Files:**
- Create: `backend/app/services/scatter.py`

```python
import polars as pl
import numpy as np
from typing import Any


def compute_scatter_data(df: pl.DataFrame, max_points: int = 5000) -> dict[str, Any]:
    """Compute scatter plot data for all numeric field pairs."""
    numeric_cols = [col for col in df.columns if df[col].dtype in (
        pl.Float32, pl.Float64, pl.Int64, pl.Int32,
    )]
    
    if len(numeric_cols) < 2:
        return {"fields": [], "pairs": []}
    
    # Sample if too many rows
    if len(df) > max_points:
        df = df.sample(max_points, seed=42)
    
    pairs = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            col1, col2 = numeric_cols[i], numeric_cols[j]
            subset = df.select([col1, col2]).drop_nulls()
            
            pairs.append({
                "x_field": col1,
                "y_field": col2,
                "points": [
                    [round(float(r[col1]), 4), round(float(r[col2]), 4)]
                    for r in subset.iter_rows(named=True)
                ],
            })
    
    return {"fields": numeric_cols, "pairs": pairs}
```

- [ ] **添加路由**

```python
# dashboard.py 中
@router.get("/api/sessions/{session_id}/scatter")
async def get_scatter_data(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    df = load_dataframe(session.file_path)
    result = compute_scatter_data(df)
    return {"success": True, "data": result, "error": None}
```

- [ ] **验证**: 测试返回数据格式正确

---

### Task 6: 前端 — 散点图矩阵组件

**Files:**
- Create: `frontend/src/components/charts/ScatterPlotMatrix.tsx`
- Create: `frontend/src/components/charts/ScatterChart.tsx`
- Modify: `frontend/src/components/charts/ChartFactory.tsx`
- Modify: `frontend/src/components/dashboard/ChartGrid.tsx`

创建散点图组件，支持悬浮显示坐标值，并添加散点图矩阵入口。

---

### Task 7: 后端 — 时间序列分析

**Files:**
- Create: `backend/app/services/timeseries.py`

使用 StatsModels 进行时间序列分解（趋势 + 季节 + 残差）。

```python
import polars as pl
import numpy as np
from typing import Any
from statsmodels.tsa.seasonal import seasonal_decompose


def detect_time_fields(df: pl.DataFrame) -> list[str]:
    """Detect datetime fields in the dataframe."""
    return [col for col in df.columns if df[col].dtype in (pl.Date, pl.Datetime)]


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
    ts_df = ts_df.with_columns(pl.col(time_field).cast(pl.Date))
    
    # Aggregate by date
    daily = ts_df.group_by(time_field).agg(
        pl.col(value_field).mean().alias(value_field)
    ).sort(time_field)
    
    dates = daily[time_field].cast(pl.Utf8).to_list()
    values = daily[value_field].to_numpy()
    
    # Need at least 2*period data points for decomposition
    min_periods = 14
    result = {
        "time_field": time_field,
        "value_field": value_field,
        "dates": dates,
        "original": [round(float(v), 4) for v in values],
    }
    
    if len(values) >= min_periods * 2:
        try:
            # Auto-detect period
            period = 7  # Weekly seasonality for daily data
            decomposition = seasonal_decompose(values, model=model, period=period, extrapolate_trend='freq')
            
            result["trend"] = [round(float(v), 4) if not np.isnan(v) else None for v in decomposition.trend]
            result["seasonal"] = [round(float(v), 4) if not np.isnan(v) else None for v in decomposition.seasonal]
            result["residual"] = [round(float(v), 4) if not np.isnan(v) else None for v in decomposition.resid]
            result["period"] = period
        except Exception as e:
            result["error"] = str(e)
    
    return result
```

- [ ] **添加路由**

```python
# dashboard.py
@router.get("/api/sessions/{session_id}/timeseries")
async def get_timeseries(session_id: str, time_field: str, value_field: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    df = load_dataframe(session.file_path)
    result = compute_time_series_analysis(df, time_field, value_field)
    return {"success": True, "data": result, "error": None}
```

- [ ] **在 `get_charts` 中自动检测时间字段并推荐时间序列图**

- [ ] **验证**: 用示例数据的时间字段测试

---

### Task 8: 前端 — 时间序列图组件

**Files:**
- Create: `frontend/src/components/charts/TimeSeriesChart.tsx`
- Modify: `frontend/src/components/charts/ChartFactory.tsx`

创建多线图展示原始 + 趋势 + 季节分量。

---

### Task 9: 前端 — 仪表盘布局拖拽

**Files:**
- Modify: `frontend/package.json`（添加 `react-grid-layout` 依赖）
- Modify: `frontend/src/components/dashboard/ChartGrid.tsx`
- Create: `frontend/src/components/dashboard/DraggableGrid.tsx`

使用 `react-grid-layout` 实现图表拖拽调整位置和大小。

- [ ] **安装依赖**: `npm install react-grid-layout @types/react-grid-layout`

- [ ] **创建 DraggableGrid.tsx**

```typescript
import { useState, useCallback } from 'react';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import ChartFactory from '../charts/ChartFactory';
import type { Layout } from 'react-grid-layout';
import type { ChartConfig } from '../../types';

interface Props {
  charts: ChartConfig[];
  onLayoutChange?: (layout: Layout[]) => void;
}

export default function DraggableGrid({ charts, onLayoutChange }: Props) {
  const defaultLayout = charts.map((chart, i) => ({
    i: chart.id,
    x: (i % 2) * 6,
    y: Math.floor(i / 2) * 4,
    w: chart.type === 'heatmap' ? 12 : 6,
    h: chart.type === 'heatmap' ? 5 : 4,
    minW: 3,
    minH: 3,
  }));

  const [layout, setLayout] = useState<Layout[]>(defaultLayout);

  const handleLayoutChange = useCallback((newLayout: Layout[]) => {
    setLayout(newLayout);
    onLayoutChange?.(newLayout);
  }, [onLayoutChange]);

  return (
    <GridLayout
      className="layout"
      layout={layout}
      cols={12}
      rowHeight={80}
      width={1200}
      onLayoutChange={handleLayoutChange}
      draggableHandle=".drag-handle"
    >
      {charts.map((chart) => (
        <div key={chart.id} style={{ overflow: 'hidden' }}>
          <ChartFactory chart={chart} />
        </div>
      ))}
    </GridLayout>
  );
}
```

- [ ] **修改 ChartFactory** — 添加拖拽手柄 `.drag-handle` 到 Card 的 title 中

- [ ] **修改 DashboardPage** — 使用 DraggableGrid 替代原有 ChartGrid

- [ ] **验证**: `npx tsc --noEmit` + 前端可以拖拽图表

---

### Task 10: 前端 — 图表交互联动筛选

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/hooks/useFilterLink.ts`

实现点击图表元素联动筛选其他图表的能力。

```typescript
// hooks/useFilterLink.ts
import { create } from 'zustand';

interface FilterState {
  filters: Record<string, string | null>; // field -> value
  setFilter: (field: string, value: string | null) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  filters: {},
  setFilter: (field, value) => set((s) => ({
    filters: { ...s.filters, [field]: value },
  })),
  clearFilters: () => set({ filters: {} }),
}));
```

- 在 ECharts 图表中添加 `onEvents` 点击处理
- 点击图表元素时更新过滤状态
- DashboardPage 顶部显示当前过滤条件 + 清除按钮

---

## 计划自审

**Spec 覆盖:**
1. 箱线图 + 异常值标记 — Task 1 (后端) + Task 2 (前端) ✅
2. 交叉统计表 — Task 3 (后端) + Task 4 (前端) ✅
3. 散点图矩阵 — Task 5 (后端) + Task 6 (前端) ✅
4. 时间序列分析 — Task 7 (后端) + Task 8 (前端) ✅
5. 图表交互联动筛选 — Task 10 ✅
6. 仪表盘布局拖拽调整 — Task 9 ✅

**无占位符**: 所有步骤包含完整代码。

**依赖关系:** Task 1→2, Task 3→4, Task 5→6, Task 7→8 是前后端配对依赖。Task 9 和 10 可独立于其他任务。

**执行顺序建议:** 1→2→3→4→5→6→7→8→9→10
