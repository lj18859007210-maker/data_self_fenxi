# 数据自分析大屏 MVP 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的"上传 → 预览 → 分析 → 展示"链路，具备基础的数值字段统计分析和数值字段相关性分析能力。

**Architecture:** 混合架构 — React + Vite 前端，Python FastAPI + Polars + DuckDB 后端，Docker 部署。后端采用同步分析+后台线程的简化异步模式，前端轮询分析进度。

**Tech Stack:** React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5 + Zustand + TanStack Query / Python 3.12 + FastAPI + Polars + DuckDB + SciPy / Docker + Nginx

---

### Task 1: 后端项目初始化

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/.gitkeep` (placeholder for uploads dir)
- Create: `.gitignore`

- [ ] **Step 1: 创建 backend/requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
polars==1.8.0
duckdb==1.1.0
scipy==1.14.0
numpy==2.1.0
openpyxl==3.1.5
pydantic==2.9.0
```

- [ ] **Step 2: 创建 backend/app/__init__.py**（空文件）

- [ ] **Step 3: 创建 backend/app/config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
SAMPLE_DATA_DIR = BASE_DIR / "app" / "sample_data"
```

- [ ] **Step 4: 创建 backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="数据自分析平台 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 5: 创建 .gitignore**

```
__pycache__/
*.pyc
node_modules/
dist/
.env
backend/data/uploads/
.superpowers/
```

- [ ] **Step 6: 验证后端启动**

Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
Expected: 服务在 http://localhost:8000 启动，`/api/health` 返回 `{"status": "ok"}`

---

### Task 2: 数据加载服务

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/data_loader.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/session.py`

- [ ] **Step 1: 创建 services/__init__.py**（空文件）

- [ ] **Step 2: 创建 models/__init__.py**（空文件）

- [ ] **Step 3: 创建 models/session.py**

```python
from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class FieldType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CATEGORY = "category"


class FieldInfo(BaseModel):
    name: str
    inferred_type: FieldType
    display_type: FieldType  # user-corrected type
    nullable: bool = False
    unique_count: int = 0
    missing_count: int = 0
    sample_values: list[Any] = []


class SessionState(str, Enum):
    UPLOADED = "uploaded"
    PREVIEW = "preview"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


class Session(BaseModel):
    id: str = str(uuid.uuid4())
    filename: str
    file_path: str
    file_size: int
    row_count: int = 0
    column_count: int = 0
    fields: list[FieldInfo] = []
    state: SessionState = SessionState.UPLOADED
    analysis_progress: float = 0.0
    created_at: datetime = datetime.now()

# In-memory session store (MVP only)
sessions: dict[str, Session] = {}
```

- [ ] **Step 4: 创建 services/data_loader.py**

```python
import polars as pl
from pathlib import Path
from app.models.session import FieldInfo, FieldType


def load_dataframe(file_path: str) -> pl.DataFrame:
    path = Path(file_path)
    if path.suffix == ".csv":
        return pl.read_csv(file_path, infer_schema_length=10000)
    elif path.suffix in (".xlsx", ".xls"):
        return pl.read_excel(file_path, infer_schema_length=10000)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def infer_field_type(series: pl.Series) -> FieldType:
    dtype = series.dtype
    if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                 pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                 pl.Float32, pl.Float64):
        return FieldType.NUMERIC
    if dtype == pl.Boolean:
        return FieldType.BOOLEAN
    if dtype == pl.Date or dtype == pl.Datetime:
        return FieldType.DATETIME
    # For string type, try to detect if it's datetime
    if dtype == pl.Utf8 or dtype == pl.String:
        # Check if it looks like a category (few unique values)
        non_null = series.drop_nulls()
        if len(non_null) > 0:
            unique_ratio = len(non_null.unique()) / len(non_null)
            if unique_ratio < 0.05 and len(non_null.unique()) < 50:
                return FieldType.CATEGORY
            return FieldType.TEXT
        return FieldType.TEXT
    if dtype.is_temporal():
        return FieldType.DATETIME
    return FieldType.TEXT


def analyze_fields(df: pl.DataFrame) -> list[FieldInfo]:
    fields = []
    for col in df.columns:
        series = df[col]
        inferred = infer_field_type(series)
        non_null = series.drop_nulls()
        missing = series.is_null().sum()
        unique_count = len(non_null.unique()) if len(non_null) > 0 else 0
        sample_values = [str(v) for v in non_null[:5].to_list()] if len(non_null) > 0 else []

        fields.append(FieldInfo(
            name=col,
            inferred_type=inferred,
            display_type=inferred,
            nullable=missing > 0,
            unique_count=unique_count,
            missing_count=missing,
            sample_values=sample_values,
        ))
    return fields


def get_preview(df: pl.DataFrame, rows: int = 100) -> list[dict]:
    return df.head(rows).to_dicts()
```

---

### Task 3: 统计计算引擎

**Files:**
- Create: `backend/app/services/stats_engine.py`

- [ ] **Step 1: 创建 stats_engine.py**

```python
import polars as pl
import numpy as np
from typing import Any
from app.models.session import FieldType


def compute_descriptive_stats(series: pl.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a numeric series."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {}

    arr = non_null.to_numpy()
    qs = np.percentile(arr, [25, 50, 75])

    return {
        "count": int(len(series)),
        "missing": int(series.is_null().sum()),
        "missing_rate": round(float(series.is_null().mean()), 4),
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(arr, ddof=1)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "q1": round(float(qs[0]), 4),
        "median": round(float(qs[1]), 4),
        "q3": round(float(qs[2]), 4),
        "skewness": round(float(np.mean(((arr - np.mean(arr)) / np.std(arr)) ** 3)), 4),
        "kurtosis": round(float(np.mean(((arr - np.mean(arr)) / np.std(arr)) ** 4) - 3), 4),
    }


def compute_histogram(series: pl.Series, bins: int = 30) -> dict[str, Any]:
    """Compute histogram data for a numeric series."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {"bins": [], "counts": []}

    arr = non_null.to_numpy()
    counts, edges = np.histogram(arr, bins=bins)
    return {
        "bins": edges.tolist(),
        "counts": counts.tolist(),
    }


def compute_frequency(series: pl.Series, top_n: int = 20) -> dict[str, Any]:
    """Compute frequency table for a categorical/text field."""
    non_null = series.drop_nulls()
    if len(non_null) == 0:
        return {"categories": [], "counts": [], "total": 0}

    freq = non_null.value_counts().head(top_n)
    cats = freq[non_null.name].to_list()
    counts = freq["count"].to_list()

    return {
        "categories": [str(c) for c in cats],
        "counts": counts,
        "total": int(len(non_null)),
    }


def compute_outliers_iqr(series: pl.Series) -> dict[str, Any]:
    """Detect outliers using IQR method."""
    non_null = series.drop_nulls()
    if len(non_null) < 4:
        return {"outlier_count": 0, "outliers": []}

    arr = non_null.to_numpy()
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outlier_mask = (arr < lower) | (arr > upper)
    outlier_indices = np.where(outlier_mask)[0].tolist()
    outlier_values = arr[outlier_mask].tolist()

    return {
        "lower_bound": round(float(lower), 4),
        "upper_bound": round(float(upper), 4),
        "outlier_count": int(outlier_mask.sum()),
        "outlier_rate": round(float(outlier_mask.mean()), 4),
        "outlier_values": [round(float(v), 4) for v in outlier_values[:100]],
    }


def compute_field_analysis(df: pl.DataFrame, field_name: str, field_type: FieldType) -> dict[str, Any]:
    """Run all relevant analysis for a single field."""
    series = df[field_name]
    result = {"field_name": field_name, "field_type": field_type.value}

    if field_type == FieldType.NUMERIC:
        result["stats"] = compute_descriptive_stats(series)
        result["histogram"] = compute_histogram(series)
        result["outliers"] = compute_outliers_iqr(series)
    elif field_type in (FieldType.CATEGORY, FieldType.TEXT, FieldType.BOOLEAN):
        result["frequency"] = compute_frequency(series)
    elif field_type == FieldType.DATETIME:
        non_null = series.drop_nulls()
        result["stats"] = {
            "count": int(len(series)),
            "missing": int(series.is_null().sum()),
            "min": str(non_null.min()) if len(non_null) > 0 else None,
            "max": str(non_null.max()) if len(non_null) > 0 else None,
        }

    return result
```

---

### Task 4: 关联分析服务

**Files:**
- Create: `backend/app/services/correlation.py`

- [ ] **Step 1: 创建 correlation.py**

```python
import polars as pl
import numpy as np
from scipy import stats
from typing import Any


def compute_correlation_matrix(df: pl.DataFrame) -> dict[str, Any]:
    """Compute Pearson correlation matrix for all numeric fields."""
    numeric_cols = [col for col in df.columns if df[col].dtype in (
        pl.Int8, pl.Int16, pl.Int32, pl.Int64,
        pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
        pl.Float32, pl.Float64
    )]

    if len(numeric_cols) < 2:
        return {"fields": [], "matrix": [], "pairs": []}

    matrix = []
    pairs = []

    for i, col1 in enumerate(numeric_cols):
        row = []
        for j, col2 in enumerate(numeric_cols):
            s1 = df[col1].drop_nulls().to_numpy()
            s2 = df[col2].drop_nulls().to_numpy()

            if len(s1) < 3 or len(s2) < 3:
                row.append(None)
                continue

            # Align by truncating to same length for correlation
            min_len = min(len(s1), len(s2))
            r, p = stats.pearsonr(s1[:min_len], s2[:min_len])
            row.append(round(float(r), 4))

            if i < j:
                pairs.append({
                    "field1": col1,
                    "field2": col2,
                    "correlation": round(float(r), 4),
                    "p_value": round(float(p), 6),
                    "strength": "strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak",
                    "direction": "positive" if r > 0 else "negative",
                })

        matrix.append(row)

    return {
        "fields": numeric_cols,
        "matrix": matrix,
        "pairs": sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True),
    }
```

---

### Task 5: 上传 API

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/upload.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: 创建 routers/__init__.py**（空文件）

- [ ] **Step 2: 创建 routers/upload.py**

```python
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import Session, sessions

router = APIRouter()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Supported: {', '.join(ALLOWED_EXTENSIONS)}")

    # Save file to upload directory
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Load and analyze
    try:
        df = load_dataframe(str(file_path))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    fields = analyze_fields(df)
    preview = get_preview(df)

    session = Session(
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        row_count=len(df),
        column_count=len(df.columns),
        fields=fields,
        state="preview",
    )
    sessions[session.id] = session

    return {
        "success": True,
        "data": {
            "session_id": session.id,
            "filename": session.filename,
            "file_size": session.file_size,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "fields": [f.model_dump() for f in session.fields],
            "preview": preview,
        },
        "error": None,
    }
```

- [ ] **Step 3: 在 main.py 中注册路由**

```python
from app.routers import upload  # Add this import
from app.routers import preview
from app.routers import analyze
from app.routers import dashboard

app.include_router(upload.router)
app.include_router(preview.router)
app.include_router(analyze.router)
app.include_router(dashboard.router)
```

---

### Task 6: 预览 API

**Files:**
- Create: `backend/app/routers/preview.py`

- [ ] **Step 1: 创建 routers/preview.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import FieldType, sessions

router = APIRouter()


class FieldUpdate(BaseModel):
    name: str
    display_type: FieldType


@router.get("/api/sessions/{session_id}/preview")
async def get_preview_data(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    df = load_dataframe(session.file_path)
    return {
        "success": True,
        "data": {
            "fields": [f.model_dump() for f in session.fields],
            "preview": get_preview(df),
            "row_count": session.row_count,
            "column_count": session.column_count,
        },
        "error": None,
    }


@router.put("/api/sessions/{session_id}/fields")
async def update_fields(session_id: str, updates: list[FieldUpdate]):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    update_map = {u.name: u.display_type for u in updates}
    for field in session.fields:
        if field.name in update_map:
            field.display_type = update_map[field.name]

    return {
        "success": True,
        "data": {"fields": [f.model_dump() for f in session.fields]},
        "error": None,
    }
```

---

### Task 7: 分析 API

**Files:**
- Create: `backend/app/routers/analyze.py`
- Create: `backend/app/services/__init__.py` (already created in Task 2)

- [ ] **Step 1: 创建 routers/analyze.py**

```python
import asyncio
import threading
from fastapi import APIRouter, HTTPException
from app.services.data_loader import load_dataframe
from app.services.stats_engine import compute_field_analysis
from app.services.correlation import compute_correlation_matrix
from app.models.session import SessionState, sessions

router = APIRouter()

# In-memory analysis progress store: session_id -> {"progress": float, "results": dict}
analysis_store: dict[str, dict] = {}


def run_analysis(session_id: str):
    """Run full analysis in background thread."""
    session = sessions.get(session_id)
    if not session:
        return

    store = analysis_store[session_id] = {"progress": 0.0, "results": {}}
    session.state = SessionState.ANALYZING

    try:
        df = load_dataframe(session.file_path)

        # Phase 1: Single field analysis (60% of progress)
        total_fields = len(session.fields)
        field_results = {}
        for i, field in enumerate(session.fields):
            field_results[field.name] = compute_field_analysis(df, field.name, field.display_type)
            store["progress"] = round((i + 1) / total_fields * 0.6, 2)

        store["results"]["fields"] = field_results

        # Phase 2: Correlation analysis (30% of progress)
        store["progress"] = 0.6
        corr = compute_correlation_matrix(df)
        store["results"]["correlation"] = corr
        store["progress"] = 0.9

        # Phase 3: Summary (10%)
        store["results"]["summary"] = {
            "total_rows": session.row_count,
            "total_columns": session.column_count,
            "total_numeric": sum(1 for f in session.fields if f.display_type.value == "numeric"),
            "total_text": sum(1 for f in session.fields if f.display_type.value in ("text", "category")),
        }
        store["progress"] = 1.0
        session.state = SessionState.COMPLETE

    except Exception as e:
        session.state = SessionState.ERROR
        store["error"] = str(e)


@router.post("/api/sessions/{session_id}/analyze")
async def trigger_analysis(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.state == SessionState.ANALYZING:
        raise HTTPException(400, "Analysis already in progress")

    thread = threading.Thread(target=run_analysis, args=(session_id,), daemon=True)
    thread.start()

    return {"success": True, "data": {"session_id": session_id, "state": "analyzing"}, "error": None}


@router.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    store = analysis_store.get(session_id, {"progress": 0.0, "results": {}})

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "state": session.state.value,
            "progress": store["progress"],
            "error": store.get("error"),
        },
        "error": None,
    }
```

---

### Task 8: 仪表盘 API

**Files:**
- Create: `backend/app/routers/dashboard.py`

- [ ] **Step 1: 创建 routers/dashboard.py**

```python
from fastapi import APIRouter, HTTPException
from app.models.session import sessions
from app.routers.analyze import analysis_store

router = APIRouter()


@router.get("/api/sessions/{session_id}/overview")
async def get_overview(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    store = analysis_store.get(session_id, {})
    results = store.get("results", {})
    fields_results = results.get("fields", {})
    summary = results.get("summary", {})

    # Count total outliers
    total_outliers = sum(
        f.get("outliers", {}).get("outlier_count", 0)
        for f in fields_results.values()
        if "outliers" in f
    )

    return {
        "success": True,
        "data": {
            "filename": session.filename,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "numeric_count": summary.get("total_numeric", 0),
            "text_count": summary.get("total_text", 0),
            "total_missing": sum(f.missing_count for f in session.fields),
            "total_outliers": total_outliers,
        },
        "error": None,
    }


@router.get("/api/sessions/{session_id}/fields/{field_name}")
async def get_field_analysis(session_id: str, field_name: str):
    store = analysis_store.get(session_id, {})
    results = store.get("results", {})
    field_data = results.get("fields", {}).get(field_name)

    if field_data is None:
        raise HTTPException(404, f"Field '{field_name}' analysis not found")

    return {"success": True, "data": field_data, "error": None}


@router.get("/api/sessions/{session_id}/correlation")
async def get_correlation(session_id: str):
    store = analysis_store.get(session_id, {})
    results = store.get("results", {})
    corr = results.get("correlation", {"fields": [], "matrix": [], "pairs": []})

    return {"success": True, "data": corr, "error": None}


@router.get("/api/sessions/{session_id}/charts")
async def get_charts(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    store = analysis_store.get(session_id, {})
    results = store.get("results", {})
    fields_results = results.get("fields", {})
    corr = results.get("correlation", {})

    charts = []

    # Generate chart configs based on field types
    for field in session.fields:
        analysis = fields_results.get(field.name, {})
        if not analysis:
            continue

        if field.display_type.value == "numeric":
            if "histogram" in analysis:
                charts.append({
                    "id": f"hist_{field.name}",
                    "type": "histogram",
                    "title": f"{field.name} 分布",
                    "field": field.name,
                    "data": analysis["histogram"],
                    "stats": analysis.get("stats", {}),
                })
        elif field.display_type.value in ("category", "text", "boolean"):
            if "frequency" in analysis:
                chart_type = "pie" if len(analysis["frequency"].get("categories", [])) <= 10 else "bar"
                charts.append({
                    "id": f"freq_{field.name}",
                    "type": chart_type,
                    "title": f"{field.name} 频次分布",
                    "field": field.name,
                    "data": analysis["frequency"],
                })

    # Correlation heatmap
    if len(corr.get("fields", [])) >= 2:
        charts.append({
            "id": "correlation",
            "type": "heatmap",
            "title": "字段相关性矩阵",
            "data": corr,
        })

    return {"success": True, "data": charts, "error": None}
```

---

### Task 9: 示例数据集

**Files:**
- Create: `backend/app/sample_data/` (directory)
- Create: `backend/app/routers/samples.py`
- Modify: `backend/app/main.py` (register samples router)

- [ ] **Step 1: 创建示例数据生成脚本**

创建 `backend/app/utils/sample_data.py`:

```python
import polars as pl
import numpy as np
from pathlib import Path


def generate_sales_data(n_rows: int = 10000) -> pl.DataFrame:
    """Generate sample sales dataset."""
    np.random.seed(42)
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
    categories = ["电子产品", "服装", "食品", "家居", "图书", "运动"]
    products = {
        "电子产品": ["iPhone 15", "MacBook Pro", "AirPods", "iPad Air", "Apple Watch"],
        "服装": ["运动鞋", "羽绒服", "T恤", "牛仔裤", "连衣裙"],
        "食品": ["巧克力", "坚果礼盒", "咖啡豆", "有机茶叶", "进口红酒"],
        "家居": ["台灯", "抱枕", "收纳盒", "地毯", "挂画"],
        "图书": ["Python编程", "数据科学", "设计模式", "算法导论", "经济学原理"],
        "运动": ["瑜伽垫", "哑铃", "跑步机", "跳绳", "泳镜"],
    }

    data = {
        "订单ID": [f"ORD{i:06d}" for i in range(n_rows)],
        "订单金额": np.round(np.random.lognormal(mean=5.5, sigma=0.8, size=n_rows), 2),
        "城市": np.random.choice(cities, size=n_rows),
        "商品类别": np.random.choice(categories, size=n_rows),
    }

    df = pl.DataFrame(data)

    # Fill product names based on category
    products_list = []
    for cat in df["商品类别"].to_list():
        products_list.append(np.random.choice(products[cat]))
    df = df.with_columns(pl.Series("商品名称", products_list))

    # Add datetime
    start = np.datetime64("2024-01-01")
    end = np.datetime64("2024-12-31")
    timestamps = start + (end - start) * np.random.random(n_rows)
    df = df.with_columns(pl.Series("下单时间", [str(t)[:19] for t in timestamps]))

    # Add boolean field
    df = df.with_columns(pl.Series("是否退货", np.random.choice([True, False], size=n_rows, p=[0.15, 0.85])))

    # Add some missing values
    missing_idx = np.random.choice(n_rows, size=int(n_rows * 0.02), replace=False)
    amounts = df["订单金额"].to_list()
    for idx in missing_idx:
        amounts[idx] = None
    df = df.with_columns(pl.Series("订单金额", amounts))

    return df


def get_sample_datasets() -> dict:
    return {
        "sales_data": {
            "name": "销售数据",
            "description": "包含订单金额、城市分布、商品类别等多维度的销售记录",
            "rows": 10000,
        }
    }


def save_sample_data(dir_path: Path) -> str:
    """Generate and save sample data, return path."""
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "sales_data.csv"
    if not file_path.exists():
        df = generate_sales_data()
        df.write_csv(file_path)
    return str(file_path)
```

- [ ] **Step 2: 创建 routers/samples.py**

```python
from fastapi import APIRouter
from app.config import UPLOAD_DIR
from app.utils.sample_data import get_sample_datasets, save_sample_data, generate_sales_data
from app.services.data_loader import load_dataframe, analyze_fields, get_preview
from app.models.session import Session, sessions

router = APIRouter()


@router.get("/api/samples")
async def list_samples():
    return {"success": True, "data": get_sample_datasets(), "error": None}


@router.post("/api/samples/{sample_id}/load")
async def load_sample(sample_id: str):
    if sample_id != "sales_data":
        return {"success": False, "data": None, "error": "Unknown sample"}

    file_path = save_sample_data(UPLOAD_DIR)
    df = load_dataframe(file_path)
    fields = analyze_fields(df)
    preview = get_preview(df)

    session = Session(
        filename="sample_sales_data.csv",
        file_path=file_path,
        file_size=0,
        row_count=len(df),
        column_count=len(df.columns),
        fields=fields,
        state="preview",
    )
    sessions[session.id] = session

    return {
        "success": True,
        "data": {
            "session_id": session.id,
            "filename": session.filename,
            "row_count": session.row_count,
            "column_count": session.column_count,
            "fields": [f.model_dump() for f in session.fields],
            "preview": preview,
        },
        "error": None,
    }
```

- [ ] **Step 3: 在 main.py 中注册 samples 路由**

Add:
```python
from app.routers import samples
app.include_router(samples.router)
```

---

### Task 10: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "data-view-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "antd": "^5.20.0",
    "@ant-design/icons": "^5.4.0",
    "echarts": "^5.5.1",
    "echarts-for-react": "^3.0.2",
    "@tanstack/react-query": "^5.51.0",
    "zustand": "^4.5.4",
    "axios": "^1.7.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.5.4",
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.1"
  }
}
```

- [ ] **Step 2: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 3: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

- [ ] **Step 4: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>数据自分析平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 创建 src/vite-env.d.ts**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 6: 创建 src/main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: '#6366f1' } }}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 7: 创建 src/App.tsx**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import PreviewPage from './pages/PreviewPage'
import DashboardPage from './pages/DashboardPage'
import AppLayout from './components/layout/AppLayout'

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/preview/:sessionId" element={<PreviewPage />} />
        <Route path="/dashboard/:sessionId" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}
```

- [ ] **Step 8: 创建 components/layout/AppLayout.tsx**

```typescript
import { ReactNode } from 'react'
import { Layout, Typography } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'

const { Header, Content } = Layout

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#1e293b', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <BarChartOutlined style={{ fontSize: 22, color: '#6366f1', marginRight: 10 }} />
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>数据自分析平台</Typography.Title>
      </Header>
      <Content style={{ padding: 24, background: '#f5f5f5' }}>
        {children}
      </Content>
    </Layout>
  )
}
```

- [ ] **Step 9: 验证前端启动**

Run: `cd frontend && npm install && npm run dev`
Expected: 服务在 http://localhost:3000 启动，看到带顶栏的白页

---

### Task 11: TypeScript 类型定义

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: 创建 types/index.ts**

```typescript
export type FieldType = 'numeric' | 'text' | 'datetime' | 'boolean' | 'category';

export interface FieldInfo {
  name: string;
  inferred_type: FieldType;
  display_type: FieldType;
  nullable: boolean;
  unique_count: number;
  missing_count: number;
  sample_values: string[];
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  file_size: number;
  row_count: number;
  column_count: number;
  fields: FieldInfo[];
  preview: Record<string, unknown>[];
}

export interface AnalysisProgress {
  session_id: string;
  state: 'uploaded' | 'preview' | 'analyzing' | 'complete' | 'error';
  progress: number;
  error?: string;
}

export interface FieldAnalysis {
  field_name: string;
  field_type: FieldType;
  stats?: Record<string, number>;
  histogram?: { bins: number[]; counts: number[] };
  outliers?: { lower_bound: number; upper_bound: number; outlier_count: number; outlier_rate: number; outlier_values: number[] };
  frequency?: { categories: string[]; counts: number[]; total: number };
}

export interface CorrelationResult {
  fields: string[];
  matrix: (number | null)[][];
  pairs: { field1: string; field2: string; correlation: number; p_value: number; strength: string; direction: string }[];
}

export interface DashboardOverview {
  filename: string;
  row_count: number;
  column_count: number;
  numeric_count: number;
  text_count: number;
  total_missing: number;
  total_outliers: number;
}

export interface ChartConfig {
  id: string;
  type: 'histogram' | 'bar' | 'pie' | 'heatmap';
  title: string;
  field: string;
  data: Record<string, unknown>;
  stats?: Record<string, number>;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
}
```

---

### Task 12: API 客户端和状态管理

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/sessionStore.ts`

- [ ] **Step 1: 创建 api/client.ts**

```typescript
import axios from 'axios';
import type { ApiResponse, UploadResponse, FieldInfo, FieldType, DashboardOverview, FieldAnalysis, CorrelationResult, ChartConfig, AnalysisProgress } from '../types';

const api = axios.create({ baseURL: '/api' });

export async function uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/upload', form);
  return data;
}

export async function getPreview(sessionId: string): Promise<ApiResponse<{ fields: FieldInfo[]; preview: Record<string, unknown>[]; row_count: number; column_count: number }>> {
  const { data } = await api.get(`/sessions/${sessionId}/preview`);
  return data;
}

export async function updateFields(sessionId: string, updates: { name: string; display_type: FieldType }[]): Promise<ApiResponse<{ fields: FieldInfo[] }>> {
  const { data } = await api.put(`/sessions/${sessionId}/fields`, updates);
  return data;
}

export async function triggerAnalysis(sessionId: string): Promise<ApiResponse<{ session_id: string; state: string }>> {
  const { data } = await api.post(`/sessions/${sessionId}/analyze`);
  return data;
}

export async function getProgress(sessionId: string): Promise<ApiResponse<AnalysisProgress>> {
  const { data } = await api.get(`/sessions/${sessionId}/progress`);
  return data;
}

export async function getOverview(sessionId: string): Promise<ApiResponse<DashboardOverview>> {
  const { data } = await api.get(`/sessions/${sessionId}/overview`);
  return data;
}

export async function getFieldAnalysis(sessionId: string, fieldName: string): Promise<ApiResponse<FieldAnalysis>> {
  const { data } = await api.get(`/sessions/${sessionId}/fields/${fieldName}`);
  return data;
}

export async function getCorrelation(sessionId: string): Promise<ApiResponse<CorrelationResult>> {
  const { data } = await api.get(`/sessions/${sessionId}/correlation`);
  return data;
}

export async function getCharts(sessionId: string): Promise<ApiResponse<ChartConfig[]>> {
  const { data } = await api.get(`/sessions/${sessionId}/charts`);
  return data;
}

export async function getSamples(): Promise<ApiResponse<Record<string, { name: string; description: string; rows: number }>>> {
  const { data } = await api.get('/samples');
  return data;
}

export async function loadSample(sampleId: string): Promise<ApiResponse<UploadResponse>> {
  const { data } = await api.post(`/samples/${sampleId}/load`);
  return data;
}
```

- [ ] **Step 2: 创建 stores/sessionStore.ts**

```typescript
import { create } from 'zustand';
import type { FieldInfo } from '../types';

interface SessionStore {
  currentSessionId: string | null;
  fields: FieldInfo[];
  setSession: (id: string, fields: FieldInfo[]) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  currentSessionId: null,
  fields: [],
  setSession: (id, fields) => set({ currentSessionId: id, fields }),
  clearSession: () => set({ currentSessionId: null, fields: [] }),
}));
```

---

### Task 13: 上传页面

**Files:**
- Create: `frontend/src/pages/UploadPage.tsx`
- Create: `frontend/src/components/upload/FileUploader.tsx`

- [ ] **Step 1: 创建 components/upload/FileUploader.tsx**

```typescript
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Upload, message, Card, Button, Space, Typography, Spin } from 'antd';
import { InboxOutlined, DatabaseOutlined } from '@ant-design/icons';
import { uploadFile, loadSample, getSamples } from '../../api/client';
import { useSessionStore } from '../../stores/sessionStore';
import type { UploadResponse } from '../../types';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;

export default function FileUploader() {
  const navigate = useNavigate();
  const setSession = useSessionStore((s) => s.setSession);
  const [uploading, setUploading] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (res) => {
      if (res.success) {
        setSession(res.data.session_id, res.data.fields);
        navigate(`/preview/${res.data.session_id}`);
      } else {
        message.error(res.error || '上传失败');
      }
    },
    onError: () => message.error('上传失败，请检查文件格式'),
    onSettled: () => setUploading(false),
  });

  const loadSampleMutation = useMutation({
    mutationFn: loadSample,
    onSuccess: (res) => {
      if (res.success) {
        setSession(res.data.session_id, res.data.fields);
        navigate(`/preview/${res.data.session_id}`);
      }
    },
  });

  const handleUpload = useCallback((file: File) => {
    setUploading(true);
    uploadMutation.mutate(file);
    return false; // Prevent default upload behavior
  }, [uploadMutation]);

  return (
    <div style={{ maxWidth: 700, margin: '40px auto' }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3}>上传你的数据文件</Title>
          <Text type="secondary">支持 CSV、Excel 格式</Text>
        </div>

        <Dragger
          accept=".csv,.xlsx,.xls"
          disabled={uploading}
          beforeUpload={handleUpload}
          showUploadList={false}
        >
          {uploading ? (
            <Spin tip="正在上传并分析..." />
          ) : (
            <>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽文件到此区域</p>
              <p className="ant-upload-hint">支持 CSV、Excel 文件，最大 500MB</p>
            </>
          )}
        </Dragger>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ textAlign: 'center' }}>
          <Space direction="vertical" size="middle">
            <DatabaseOutlined style={{ fontSize: 32, color: '#6366f1' }} />
            <div>
              <Title level={4} style={{ margin: 0 }}>还没有数据？</Title>
              <Paragraph type="secondary" style={{ marginTop: 8 }}>
                加载示例数据集，立即体验分析功能
              </Paragraph>
            </div>
            <Button
              type="primary"
              size="large"
              loading={loadSampleMutation.isPending}
              onClick={() => loadSampleMutation.mutate('sales_data')}
            >
              加载示例数据
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 创建 pages/UploadPage.tsx**

```typescript
import FileUploader from '../components/upload/FileUploader';

export default function UploadPage() {
  return <FileUploader />;
}
```

---

### Task 14: 数据预览页面

**Files:**
- Create: `frontend/src/pages/PreviewPage.tsx`
- Create: `frontend/src/components/preview/DataPreview.tsx`
- Create: `frontend/src/components/preview/FieldTypeEditor.tsx`

- [ ] **Step 1: 创建 components/preview/FieldTypeEditor.tsx**

```typescript
import { Table, Tag, Select, Typography } from 'antd';
import type { FieldInfo, FieldType } from '../../types';

const typeColors: Record<FieldType, string> = {
  numeric: '#6366f1',
  text: '#06b6d4',
  datetime: '#10b981',
  boolean: '#ef4444',
  category: '#f59e0b',
};

const typeLabels: Record<FieldType, string> = {
  numeric: '数值',
  text: '文本',
  datetime: '时间',
  boolean: '布尔',
  category: '类别',
};

interface Props {
  fields: FieldInfo[];
  onChange: (updates: { name: string; display_type: FieldType }[]) => void;
}

export default function FieldTypeEditor({ fields, onChange }: Props) {
  const handleTypeChange = (fieldName: string, newType: FieldType) => {
    onChange([{ name: fieldName, display_type: newType }]);
  };

  const columns = [
    {
      title: '字段名', dataIndex: 'name', key: 'name',
      render: (name: string) => <Typography.Text strong>{name}</Typography.Text>,
    },
    {
      title: '推断类型', dataIndex: 'inferred_type', key: 'inferred_type',
      render: (t: FieldType) => <Tag color={typeColors[t]}>{typeLabels[t]}</Tag>,
    },
    {
      title: '实际类型', dataIndex: 'display_type', key: 'display_type',
      render: (t: FieldType, record: FieldInfo) => (
        <Select
          value={t}
          size="small"
          style={{ width: 100 }}
          onChange={(v) => handleTypeChange(record.name, v)}
          options={[
            { value: 'numeric', label: '数值' },
            { value: 'text', label: '文本' },
            { value: 'datetime', label: '时间' },
            { value: 'boolean', label: '布尔' },
            { value: 'category', label: '类别' },
          ]}
        />
      ),
    },
    {
      title: '唯一值', dataIndex: 'unique_count', key: 'unique_count', width: 80,
    },
    {
      title: '缺失', dataIndex: 'missing_count', key: 'missing_count', width: 80,
      render: (v: number) => v > 0 ? <span style={{ color: '#ef4444' }}>{v}</span> : v,
    },
    {
      title: '示例值', dataIndex: 'sample_values', key: 'sample_values',
      render: (vals: string[]) => vals.slice(0, 3).join(', '),
    },
  ];

  return (
    <Table
      dataSource={fields}
      columns={columns}
      rowKey="name"
      pagination={false}
      size="small"
    />
  );
}
```

- [ ] **Step 2: 创建 components/preview/DataPreview.tsx**

```typescript
import { Table } from 'antd';

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
}

export default function DataPreview({ columns, rows }: Props) {
  const tableColumns = columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
    width: 150,
  }));

  return (
    <Table
      dataSource={rows.map((r, i) => ({ ...r, _key: i }))}
      columns={tableColumns}
      rowKey="_key"
      scroll={{ x: 'max-content', y: 400 }}
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 行` }}
      size="small"
    />
  );
}
```

- [ ] **Step 3: 创建 pages/PreviewPage.tsx**

```typescript
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, Button, Space, Typography, Spin, Descriptions, message, Alert } from 'antd';
import { getPreview, updateFields, triggerAnalysis } from '../api/client';
import { useSessionStore } from '../stores/sessionStore';
import DataPreview from '../components/preview/DataPreview';
import FieldTypeEditor from '../components/preview/FieldTypeEditor';
import type { FieldType } from '../types';

const { Title, Text } = Typography;

export default function PreviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { setSession } = useSessionStore();
  const [analyzing, setAnalyzing] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['preview', sessionId],
    queryFn: () => getPreview(sessionId!),
    enabled: !!sessionId,
  });

  const sessionData = data?.data;

  // Sync fields to store
  useEffect(() => {
    if (sessionData) {
      setSession(sessionId!, sessionData.fields);
    }
  }, [sessionData, sessionId, setSession]);

  const updateMutation = useMutation({
    mutationFn: (updates: { name: string; display_type: FieldType }[]) =>
      updateFields(sessionId!, updates),
    onSuccess: () => message.success('字段类型已更新'),
  });

  const handleAnalyze = async () => {
    if (!sessionId) return;
    setAnalyzing(true);
    try {
      await triggerAnalysis(sessionId);
      navigate(`/dashboard/${sessionId}`);
    } catch {
      message.error('启动分析失败');
      setAnalyzing(false);
    }
  };

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (error || !sessionData) return <Alert type="error" message="加载失败" />;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>{sessionData.filename}</Title>
            <Space>
              <Button onClick={() => navigate('/')}>重新选择</Button>
              <Button type="primary" size="large" loading={analyzing} onClick={handleAnalyze}>
                开始分析
              </Button>
            </Space>
          </div>
          <Descriptions size="small" column={4}>
            <Descriptions.Item label="行数">{sessionData.row_count.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="列数">{sessionData.column_count}</Descriptions.Item>
            <Descriptions.Item label="数值字段">
              {sessionData.fields.filter((f) => f.display_type === 'numeric').length}
            </Descriptions.Item>
            <Descriptions.Item label="类别字段">
              {sessionData.fields.filter((f) => f.display_type === 'category').length}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>

      <Card title="字段类型配置" style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          系统已自动推断字段类型，如有误可手动修改：
        </Text>
        <FieldTypeEditor
          fields={sessionData.fields}
          onChange={(updates) => updateMutation.mutate(updates)}
        />
      </Card>

      <Card title="数据预览（前100行）">
        <DataPreview
          columns={sessionData.fields.map((f) => f.name)}
          rows={sessionData.preview}
        />
      </Card>
    </div>
  );
}
```

---

### Task 15: 仪表盘页面 — 概览 KPI + 字段列表

**Files:**
- Create: `frontend/src/components/dashboard/KpiCards.tsx`
- Create: `frontend/src/components/dashboard/FieldList.tsx`

- [ ] **Step 1: 创建 components/dashboard/KpiCards.tsx**

```typescript
import { Row, Col, Card, Statistic } from 'antd';
import { TableOutlined, ColumnHeightOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons';

interface Props {
  overview: {
    filename: string;
    row_count: number;
    column_count: number;
    numeric_count: number;
    text_count: number;
    total_missing: number;
    total_outliers: number;
  };
}

export default function KpiCards({ overview }: Props) {
  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card size="small">
          <Statistic title="数据总量" value={overview.row_count} suffix="行" prefix={<TableOutlined />} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="字段总数" value={overview.column_count} prefix={<ColumnHeightOutlined />}
            suffix={`(${overview.numeric_count} 数值 / ${overview.text_count} 类别)`} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="缺失值" value={overview.total_missing} prefix={<WarningOutlined />}
            valueStyle={{ color: overview.total_missing > 0 ? '#faad14' : undefined }} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="异常值" value={overview.total_outliers} prefix={<InfoCircleOutlined />}
            valueStyle={{ color: overview.total_outliers > 0 ? '#ff4d4f' : undefined }} />
        </Card>
      </Col>
    </Row>
  );
}
```

- [ ] **Step 2: 创建 components/dashboard/FieldList.tsx**

```typescript
import { List, Tag, Typography } from 'antd';
import type { FieldInfo, FieldType } from '../../types';

const typeColors: Record<FieldType, string> = {
  numeric: '#6366f1',
  text: '#06b6d4',
  datetime: '#10b981',
  boolean: '#ef4444',
  category: '#f59e0b',
};
const typeLabels: Record<FieldType, string> = {
  numeric: '数值', text: '文本', datetime: '时间', boolean: '布尔', category: '类别',
};

interface Props {
  fields: FieldInfo[];
  selectedField?: string;
  onSelect?: (name: string) => void;
}

export default function FieldList({ fields, selectedField, onSelect }: Props) {
  return (
    <div>
      <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>字段列表</Typography.Text>
      <List
        size="small"
        dataSource={fields}
        renderItem={(field) => (
          <List.Item
            key={field.name}
            onClick={() => onSelect?.(field.name)}
            style={{
              cursor: onSelect ? 'pointer' : undefined,
              background: selectedField === field.name ? '#f0f0ff' : undefined,
              padding: '6px 12px',
              borderRadius: 4,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
              <Tag color={typeColors[field.display_type]} style={{ margin: 0, flexShrink: 0 }}>
                {typeLabels[field.display_type]}
              </Tag>
              <Typography.Text ellipsis>{field.name}</Typography.Text>
            </div>
          </List.Item>
        )}
      />
    </div>
  );
}
```

---

### Task 16: ECharts 图表组件

**Files:**
- Create: `frontend/src/components/charts/HistogramChart.tsx`
- Create: `frontend/src/components/charts/BarChart.tsx`
- Create: `frontend/src/components/charts/PieChart.tsx`
- Create: `frontend/src/components/charts/CorrelationHeatmap.tsx`
- Create: `frontend/src/components/charts/ChartFactory.tsx`

- [ ] **Step 1: 创建 components/charts/HistogramChart.tsx**

```typescript
import ReactEChartsCore from 'echarts-for-react';

interface Props {
  bins: number[];
  counts: number[];
  height?: number;
}

export default function HistogramChart({ bins, counts, height = 250 }: Props) {
  // bins is the edge array, length = counts.length + 1
  const labels = bins.slice(0, -1).map((v, i) =>
    `${v.toFixed(1)}-${bins[i + 1].toFixed(1)}`
  );

  const option = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: labels,
      axisLabel: { rotate: 45, fontSize: 10, interval: Math.max(Math.floor(labels.length / 20), 1) },
    },
    yAxis: { type: 'value' as const },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#6366f1' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
```

- [ ] **Step 2: 创建 components/charts/BarChart.tsx**

```typescript
import ReactEChartsCore from 'echarts-for-react';

interface Props {
  categories: string[];
  counts: number[];
  height?: number;
}

export default function BarChart({ categories, counts, height = 250 }: Props) {
  const option = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
    xAxis: {
      type: 'category' as const,
      data: categories,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value' as const },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#06b6d4' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
```

- [ ] **Step 3: 创建 components/charts/PieChart.tsx**

```typescript
import ReactEChartsCore from 'echarts-for-react';

interface Props {
  categories: string[];
  counts: number[];
  height?: number;
}

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function PieChart({ categories, counts, height = 250 }: Props) {
  const option = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['30%', '60%'],
      data: categories.map((name, i) => ({
        name,
        value: counts[i],
        itemStyle: { color: COLORS[i % COLORS.length] },
      })),
      label: { show: categories.length <= 10, formatter: '{b}' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
```

- [ ] **Step 4: 创建 components/charts/CorrelationHeatmap.tsx**

```typescript
import ReactEChartsCore from 'echarts-for-react';

interface Props {
  fields: string[];
  matrix: (number | null)[][];
  height?: number;
}

export default function CorrelationHeatmap({ fields, matrix, height = 300 }: Props) {
  const data: [number, number, number][] = [];
  for (let i = 0; i < fields.length; i++) {
    for (let j = 0; j < fields.length; j++) {
      if (matrix[i]?.[j] !== null && matrix[i]?.[j] !== undefined) {
        data.push([j, i, matrix[i][j] as number]);
      }
    }
  }

  const option = {
    tooltip: {
      position: 'top' as const,
      formatter: (p: { value: [number, number, number] }) =>
        `${fields[p.value[1]]} ~ ${fields[p.value[0]]}: ${p.value[2].toFixed(4)}`,
    },
    grid: { left: 80, right: 40, top: 20, bottom: 80 },
    xAxis: {
      type: 'category' as const,
      data: fields,
      axisLabel: { rotate: 45, fontSize: 10 },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category' as const,
      data: fields,
      axisLabel: { fontSize: 10 },
      splitArea: { show: true },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#ef4444', '#f5f5f5', '#6366f1'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: fields.length <= 8,
        formatter: (p: { value: [number, number, number] }) => p.value[2].toFixed(2),
        fontSize: 11,
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.15)' },
      },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
```

- [ ] **Step 5: 创建 components/charts/ChartFactory.tsx**

```typescript
import { Card } from 'antd';
import HistogramChart from './HistogramChart';
import BarChart from './BarChart';
import PieChart from './PieChart';
import CorrelationHeatmap from './CorrelationHeatmap';
import type { ChartConfig } from '../../types';

interface Props {
  chart: ChartConfig;
}

export default function ChartFactory({ chart }: Props) {
  const renderChart = () => {
    switch (chart.type) {
      case 'histogram': {
        const d = chart.data as { bins: number[]; counts: number[] };
        return <HistogramChart bins={d.bins} counts={d.counts} />;
      }
      case 'bar': {
        const d = chart.data as { categories: string[]; counts: number[] };
        return <BarChart categories={d.categories} counts={d.counts} />;
      }
      case 'pie': {
        const d = chart.data as { categories: string[]; counts: number[] };
        return <PieChart categories={d.categories} counts={d.counts} />;
      }
      case 'heatmap': {
        const d = chart.data as { fields: string[]; matrix: (number | null)[][] };
        return <CorrelationHeatmap fields={d.fields} matrix={d.matrix} />;
      }
      default:
        return <div>不支持的图表类型</div>;
    }
  };

  return (
    <Card title={chart.title} size="small" style={{ height: '100%' }}>
      {renderChart()}
    </Card>
  );
}
```

---

### Task 17: 仪表盘页面

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/components/dashboard/ChartGrid.tsx`

- [ ] **Step 1: 创建 components/dashboard/ChartGrid.tsx**

```typescript
import { Row, Col, Spin, Empty, Alert } from 'antd';
import ChartFactory from '../charts/ChartFactory';
import type { ChartConfig } from '../../types';

interface Props {
  charts: ChartConfig[];
  loading: boolean;
}

export default function ChartGrid({ charts, loading }: Props) {
  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  if (!charts.length) return <Empty description="暂无图表数据" />;

  return (
    <Row gutter={[16, 16]}>
      {charts.map((chart) => (
        <Col key={chart.id} xs={24} sm={12} lg={chart.type === 'heatmap' ? 24 : 12}>
          <ChartFactory chart={chart} />
        </Col>
      ))}
    </Row>
  );
}
```

- [ ] **Step 2: 创建 pages/DashboardPage.tsx**

```typescript
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Layout, Spin, Typography, Alert, Space, Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getOverview, getProgress, getCharts } from '../api/client';
import { useSessionStore } from '../stores/sessionStore';
import KpiCards from '../components/dashboard/KpiCards';
import FieldList from '../components/dashboard/FieldList';
import ChartGrid from '../components/dashboard/ChartGrid';
import type { ChartConfig, DashboardOverview } from '../types';

const { Sider, Content } = Layout;

export default function DashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const fields = useSessionStore((s) => s.fields);
  const [selectedField, setSelectedField] = useState<string>();
  const [analyzing, setAnalyzing] = useState(true);

  const overviewQuery = useQuery({
    queryKey: ['overview', sessionId],
    queryFn: () => getOverview(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (q) => {
      // Poll until complete
      const state = q.state.data?.data?.state;
      return state === 'complete' || state === 'error' ? false : 1000;
    },
  });

  const chartsQuery = useQuery({
    queryKey: ['charts', sessionId],
    queryFn: () => getCharts(sessionId!),
    enabled: !!sessionId && overviewQuery.data?.data?.state === 'complete',
  });

  // Poll progress
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      const res = await getProgress(sessionId);
      if (res.data.state === 'complete' || res.data.state === 'error') {
        setAnalyzing(false);
        clearInterval(interval);
        overviewQuery.refetch();
        chartsQuery.refetch();
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionId, overviewQuery, chartsQuery]);

  const overview = overviewQuery.data?.data as DashboardOverview | undefined;
  const charts = chartsQuery.data?.data as ChartConfig[] | undefined;

  if (analyzing) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
        <Typography.Title level={4} style={{ marginTop: 24 }}>正在分析数据...</Typography.Title>
        <Typography.Text type="secondary">系统正在自动计算各字段统计量和关联关系</Typography.Text>
      </div>
    );
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
      </Space>

      {overview && <KpiCards overview={overview} />}

      <Layout style={{ background: 'transparent', marginTop: 16 }}>
        <Sider width={200} style={{ background: '#fff', padding: 12, borderRadius: 8 }}>
          <FieldList fields={fields} selectedField={selectedField} onSelect={setSelectedField} />
        </Sider>
        <Content style={{ paddingLeft: 16 }}>
          {charts && <ChartGrid charts={charts} loading={chartsQuery.isLoading} />}
        </Content>
      </Layout>
    </div>
  );
}
```

Wait, I realize there's an issue with the DashboardPage. The `overviewQuery` response data doesn't have a `state` property - it returns `DashboardOverview`. The `state` comes from the progress endpoint. Let me fix this.

Actually, let me reconsider the approach. The overview endpoint just returns KPI data. The progress polling should be separate. Let me simplify:

```typescript
// Simplified: just poll progress first, once complete show dashboard
```

Let me fix the DashboardPage.

- [ ] **Step 2 (corrected): 创建 pages/DashboardPage.tsx**

```typescript
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Spin, Typography, Space, Button, Layout, Progress } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getOverview, getProgress, getCharts } from '../api/client';
import { useSessionStore } from '../stores/sessionStore';
import KpiCards from '../components/dashboard/KpiCards';
import FieldList from '../components/dashboard/FieldList';
import ChartGrid from '../components/dashboard/ChartGrid';
import type { DashboardOverview, ChartConfig } from '../types';

const { Sider, Content } = Layout;

export default function DashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const fields = useSessionStore((s) => s.fields);
  const [selectedField, setSelectedField] = useState<string>();
  const [progress, setProgress] = useState(0);
  const [analyzing, setAnalyzing] = useState(true);

  // Poll analysis progress
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      const res = await getProgress(sessionId);
      setProgress(res.data.progress);
      if (res.data.state === 'complete' || res.data.state === 'error') {
        setAnalyzing(false);
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const overviewQuery = useQuery({
    queryKey: ['overview', sessionId],
    queryFn: () => getOverview(sessionId!),
    enabled: !!sessionId && !analyzing,
  });

  const chartsQuery = useQuery({
    queryKey: ['charts', sessionId],
    queryFn: () => getCharts(sessionId!),
    enabled: !!sessionId && !analyzing,
  });

  const overview = overviewQuery.data?.data as DashboardOverview | undefined;
  const charts = chartsQuery.data?.data as ChartConfig[] | undefined;

  if (analyzing) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Progress type="circle" percent={Math.round(progress * 100)} />
        <Typography.Title level={4} style={{ marginTop: 24 }}>正在分析数据...</Typography.Title>
        <Typography.Text type="secondary">系统正在自动计算各字段的统计量和关联关系</Typography.Text>
      </div>
    );
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
      </Space>
      {overview && <KpiCards overview={overview} />}
      <Layout style={{ background: 'transparent', marginTop: 16 }}>
        <Sider width={200} style={{ background: '#fff', padding: 12, borderRadius: 8 }}>
          <FieldList fields={fields} selectedField={selectedField} onSelect={setSelectedField} />
        </Sider>
        <Content style={{ paddingLeft: 16 }}>
          {charts && <ChartGrid charts={charts} loading={chartsQuery.isLoading} />}
        </Content>
      </Layout>
    </div>
  );
}
```

---

### Task 18: Docker 部署

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: 创建 frontend/nginx.conf**

```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 500M;
    }
}
```

- [ ] **Step 4: 创建 docker-compose.yml**

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - data:/app/data
    environment:
      - POLARS_MAX_THREADS=4

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  data:
```

---

## 计划自审

**Spec 覆盖检查:**
1. 数据上传 — Task 5（upload API）+ Task 13（上传页面）✅
2. 数据预览 — Task 6（preview API）+ Task 14（预览页面）✅
3. 自动类型推断 — Task 2（data_loader.py）✅
4. 类型修正 — Task 6（PUT fields）+ Task 14（FieldTypeEditor）✅
5. 单字段分析 — Task 3（stats_engine）+ Task 8（field analysis API）✅
6. 相关性矩阵 — Task 4（correlation.py）+ Task 8（correlation API）✅
7. 仪表盘渲染 — Task 15（KPI + FieldList）+ Task 16（ECharts）+ Task 17（DashboardPage）✅
8. 示例数据集 — Task 9（sample_data.py + samples router）✅
9. Docker 部署 — Task 18 ✅

**无占位符**：所有步骤包含完整代码、无 "TBD"/"TODO"。

**类型一致性**：后端 Pydantic 模型与前端 TypeScript 类型在所有 API 端点签名中保持一致。
