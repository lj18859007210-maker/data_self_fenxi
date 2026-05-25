# 项目结构报告

生成时间：2026-05-25  
项目路径：`D:\AAA-Project\wei\data-view\data-view`

## 1. 项目概览

这个仓库是一个典型的前后端分离数据分析平台，核心目标是支持用户上传 CSV/Excel 数据后，完成：

1. 数据预览
2. 字段类型修正
3. 自动分析
4. 仪表盘展示
5. AI 洞察与交叉分析

整体上可以看成三层：

- `frontend/`：React + TypeScript 前端
- `backend/`：FastAPI + Python 分析服务
- `docs/`：需求、方案和阶段性文档

---

## 2. 顶层目录结构

```text
data-view/
├─ backend/                  # Python 后端
├─ frontend/                 # React 前端
├─ docs/                     # 设计、计划和说明文档
├─ docker-compose.yml        # 一键编排
├─ package-lock.json         # 根目录 lock 文件（需确认是否仍在使用）
└─ .gitignore
```

从当前可见结构看，仓库的主要开发重心已经集中在 `frontend/` 和 `backend/` 两个目录。

---

## 3. 前端结构

### 3.1 技术栈

前端位于 `frontend/`，主要技术和依赖如下：

- React 18
- TypeScript
- Vite
- Ant Design
- React Router
- TanStack React Query
- Zustand
- ECharts / echarts-for-react
- html2canvas + jsPDF（用于导出）

入口配置在：

- [`frontend/package.json`](D:\AAA-Project\wei\data-view\data-view\frontend\package.json)
- [`frontend/src/main.tsx`](D:\AAA-Project\wei\data-view\data-view\frontend\src\main.tsx)
- [`frontend/src/App.tsx`](D:\AAA-Project\wei\data-view\data-view\frontend\src\App.tsx)

### 3.2 页面流

当前前端路由非常清晰，主流程是：

- `/`：上传页
- `/preview/:sessionId`：数据预览与字段修正
- `/dashboard/:sessionId`：分析结果仪表盘

对应实现位于：

- [`frontend/src/pages/UploadPage.tsx`](D:\AAA-Project\wei\data-view\data-view\frontend\src\pages\UploadPage.tsx)
- [`frontend/src/pages/PreviewPage.tsx`](D:\AAA-Project\wei\data-view\data-view\frontend\src\pages\PreviewPage.tsx)
- [`frontend/src/pages/DashboardPage.tsx`](D:\AAA-Project\wei\data-view\data-view\frontend\src\pages\DashboardPage.tsx)

这条链路可以概括为：

```text
上传文件 -> 预览数据 -> 修正字段类型 -> 触发分析 -> 查看仪表盘
```

### 3.3 组件分层

`frontend/src/components/` 下按功能拆分得比较细，主要包含：

- `upload/`：上传器
- `preview/`：数据预览、字段类型编辑
- `dashboard/`：KPI、字段列表、拖拽布局、导出
- `charts/`：图表封装
- `insights/`：AI 洞察展示
- `history/`：历史记录列表
- `layout/`：应用布局

这说明前端不是单纯的页面堆砌，而是围绕“分析工作流”做了较完整的功能拆分。

### 3.4 前端状态与数据流

前端的数据流主要依赖三类机制：

- React Query：管理服务端请求与缓存
- Zustand：保存当前 session 相关字段和筛选状态
- API Client：统一封装 `/api` 请求

API 封装位于：

- [`frontend/src/api/client.ts`](D:\AAA-Project\wei\data-view\data-view\frontend\src\api\client.ts)

从这个文件能看出前端直接对接的核心接口包括：

- 上传
- 预览
- 字段更新
- 分析触发
- 进度轮询
- 概览数据
- 字段分析
- 相关性分析
- 图表配置
- 样本数据
- 洞察
- 历史记录
- 删除会话

---

## 4. 后端结构

### 4.1 技术栈

后端位于 `backend/`，核心技术为：

- FastAPI
- Uvicorn
- Polars
- DuckDB
- SciPy
- NumPy
- StatsModels
- OpenPyXL
- Pydantic

依赖清单位于：

- [`backend/requirements.txt`](D:\AAA-Project\wei\data-view\data-view\backend\requirements.txt)

### 4.2 应用入口

后端入口是：

- [`backend/app/main.py`](D:\AAA-Project\wei\data-view\data-view\backend\app\main.py)

它做了几件关键事情：

- 初始化上传目录
- 初始化数据库
- 注册 CORS
- 挂载业务路由
- 在前端构建完成后，静态托管 `frontend/dist`
- 提供健康检查接口 `/api/health`

这说明后端不仅是分析 API，也是最终部署时的统一服务入口。

### 4.3 路由层

`backend/app/routers/` 下按业务拆分了接口：

- `upload.py`：文件上传
- `preview.py`：预览和字段信息
- `analyze.py`：分析触发
- `dashboard.py`：仪表盘数据
- `samples.py`：样本数据
- `history.py`：历史记录
- `query.py`：查询接口

整体上，路由层负责 HTTP 边界，业务逻辑集中在 `services/`。

### 4.4 服务层

`backend/app/services/` 是后端的核心分析能力所在，文件命名已经基本反映出职责：

- `data_loader.py`：数据加载和字段推断
- `stats_engine.py`：统计计算
- `correlation.py`：相关性分析
- `cross_tab.py`：交叉统计
- `timeseries.py`：时间序列分析
- `scatter.py`：散点分析
- `chart_recommender.py`：图表推荐
- `insight_engine.py`：AI 洞察生成
- `nl2sql.py`：自然语言查询到 SQL
- `storage.py`：会话与结果存储

这套命名说明后端已经不是“单一 API 服务”，而是一个分层的分析引擎：

1. 原始数据先被加载和推断
2. 再进入统计和分析模块
3. 最后输出图表配置、洞察和汇总结果

### 4.5 数据模型与存储

数据模型位于：

- [`backend/app/models/session.py`](D:\AAA-Project\wei\data-view\data-view\backend\app\models\session.py)

这里定义了：

- 字段类型枚举
- 字段信息模型
- 会话状态枚举
- 会话模型

存储实现位于：

- [`backend/app/services/storage.py`](D:\AAA-Project\wei\data-view\data-view\backend\app\services\storage.py)

从实现看，当前存储是基于 SQLite 的，主要表包括：

- `sessions`
- `analysis_results`
- `analysis_progress`

运行时配置位于：

- [`backend/app/config.py`](D:\AAA-Project\wei\data-view\data-view\backend\app\config.py)

其中可以看到：

- 上传目录：`backend/data/uploads`
- 数据库文件：`backend/data/sessions.db`
- 支持扩展名：CSV / XLSX / XLS
- 最大上传大小：500MB

---

## 5. 数据与运行时资源

当前仓库中已经能看到一些运行时数据文件：

- `backend/data/sessions.db`
- `backend/data/uploads/` 下的上传文件
- `backend/app/sample_data/test.csv`
- `backend/tests/` 下的测试用例

这说明项目不是纯代码仓库，而是已经带有一部分可运行状态和样例数据。

从部署角度看，建议把以下内容区分清楚：

- 代码：`frontend/`、`backend/`
- 配置：`docker-compose.yml`、`requirements.txt`、`package.json`
- 运行时数据：`backend/data/`
- 文档：`docs/`

---

## 6. 测试结构

后端测试位于：

- [`backend/tests/`](D:\AAA-Project\wei\data-view\data-view\backend\tests)

当前已有测试覆盖：

- `test_storage.py`
- `test_stats_engine.py`
- `test_nl2sql.py`
- `test_insight_engine.py`
- `test_cross_tab.py`
- `test_correlation.py`
- `test_chart_recommender.py`

这说明测试重点放在分析引擎、存储和结果生成层，而不是仅仅覆盖接口层。

---

## 7. 文档结构

`docs/` 目录下目前主要是项目规划和设计文档，包含：

- `docs/superpowers/specs/2026-05-24-data-analysis-dashboard-design.md`
- `docs/superpowers/plans/2026-05-24-data-analysis-dashboard-mvp.md`
- `docs/superpowers/plans/2026-05-24-data-analysis-dashboard-phase2.md`
- `docs/superpowers/plans/2026-05-24-data-analysis-dashboard-phase3.md`
- `docs/superpowers/plans/2026-05-24-data-analysis-dashboard-phase4.md`

从命名看，项目已经经历了：

1. 设计
2. MVP 规划
3. 分阶段演进

这类文档对后续梳理需求演进、确认版本边界很有帮助。

---

## 8. 总体评价

### 优点

- 前后端边界清晰
- 页面流和业务流一致，学习成本低
- 后端分析能力有明确分层
- 测试覆盖了核心分析模块
- 已经具备可部署形态，支持前端静态托管

### 可以继续确认的点

- 根目录 `package-lock.json` 是否仍然需要保留
- 运行时数据文件是否需要与代码仓库进一步隔离
- 是否需要补一个根级 `README.md` 作为入口说明

---

## 9. 一句话总结

这个项目是一个“上传数据 -> 自动分析 -> 大屏展示 -> 洞察输出”的前后端一体化数据分析平台，前端负责交互和可视化，后端负责数据处理、统计分析和洞察生成。

