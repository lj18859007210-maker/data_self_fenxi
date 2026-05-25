# 数据自分析大屏 — 第四阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 体验打磨 — 分析报告导出、历史记录管理、性能优化

**Architecture:** 前端导出（html2canvas + jsPDF），后端持久化（SQLite 替代内存存储），NL2SQL 规则引擎

---

### Task 1: 后端 — SQLite 持久化存储

**Files:**
- Modify: `backend/app/config.py` — 添加数据库路径
- Create: `backend/app/services/storage.py` — SQLite 存储引擎替代内存 sessions dict
- Modify: `backend/app/main.py` — 初始化数据库

当前 MVP 使用内存 dict 存储 session，重启后丢失。改用 SQLite 持久化。

### Task 2: 后端 — 历史记录管理

**Files:**
- Create: `backend/app/routers/history.py`
- Modify: `backend/app/main.py` — 注册路由

新增 API 端点：
- `GET /api/history` — 获取历史 session 列表
- `DELETE /api/sessions/{id}` — 删除历史记录

### Task 3: 前端 — 历史记录页面

**Files:**
- Modify: `frontend/src/pages/UploadPage.tsx` — 增加历史记录入口
- Create: `frontend/src/components/history/HistoryList.tsx`
- Modify: `frontend/src/App.tsx` — 增加历史记录路由

### Task 4: 前端 — 分析报告导出

**Files:**
- Modify: `frontend/package.json` — 添加 html2canvas + jsPDF
- Create: `frontend/src/components/dashboard/ExportButton.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx` — 添加导出按钮

### Task 5: 前端 — 性能优化

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx` — ECharts 按需加载
- Modify: `frontend/vite.config.ts` — 代码分割

### Task 6: 后端 — NL2SQL 规则引擎

**Files:**
- Create: `backend/app/services/nl2sql.py`
- Create: `backend/app/routers/query.py`
- Modify: `backend/app/main.py` — 注册路由

基于规则的自然语言查询转 SQL，支持常见查询模式。

---

## 执行顺序

1 → 2 → 3（持久化+历史）→ 4（导出）→ 5（性能）→ 6（NL2SQL）
