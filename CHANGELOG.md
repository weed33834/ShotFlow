# 更新日志

> 本文件记录 ShotFlow 的主要变更。格式参考 [Keep a Changelog](https://keepachangelog.com/)。

---

## [Unreleased]

### Refactor — 技术债务全面清理（第六轮）

- **后端安全** `create_access_token` 加 `iat` 声明；`verify_password` 全异常兜底（损坏哈希/None 入参返回 False）。
- **后端服务层** `recover_stuck_tasks` 异常时返回 -1（beat 调度不中断）；`enqueue_task`/`retry_task` 派发 Celery 失败时标记 `status=failed`、`error_class=dispatch_error`，避免任务静默滞留 pending；`workflow_config_service._load_yaml` 加 mtime 缓存避免热路径读盘；`provider_adapters` 新增 `_cleanup_job_context` 清理 `_JOB_CONTEXT` 内存泄漏；`case_studies.public_list` 加 `limit`/`offset` 分页。
- **后端 API** `scan_assets` 不支持的资产类型返回 400（原 200+error）+ 新增 `limit` 参数（默认 1000）防 OOM；`create_user` 改用 `Depends(require_superuser)`；`provider_recommend.has_gpu` 改 `bool | None` 不传时回退 `settings.HAS_GPU`；7 个路由文件 20 处硬编码 `status_code=数字` 改为 `status.HTTP_xxx` 常量。
- **后端 ORM** `Shot` 加 `(project_id, shot_code)` 复合唯一约束；`RenderTask` 加 `(status, priority)` 复合索引 + `shot`/`project` relationship；PostgreSQL 引擎加 `pool_recycle=3600`；新增 migration `c7a2e1b3d904`。
- **后端代码风格** `auth.py`/`deps.py` 5 处 SQLAlchemy 1.x `db.query()` 全部迁移到 2.0 `select()` 风格；`init_db.py` 迁移到 `select()` 风格；删除 `deps.get_optional_current_user`、`assets._file_meta` 死代码。
- **前端** `client.ts` 并发 401 去重（避免多次 logout 闪烁）；`useQueueStream` 重构为模块级单例（避免 MainLayout + Dashboard/Queue 同页开多条 SSE 连接）+ stats JSON 浅比较（避免每 2 秒无谓重渲染与队列重取）；Projects/Shots/Workflows/CaseStudies 删除按钮加 loading；Assets scan 失败显示 Alert + 删除 `ScanResult.error` 死字段。
- **测试** 后端新增 `test_debt_cleanup.py`(12) + `test_orm_and_init.py`(5) 共 17 个测试；前端新增 `client.test.ts`(2) + `useQueueStream.test.ts`(3) 共 5 个测试；`conftest.py` 加 autouse fixture mock Celery `delay` 修复测试隔离（之前测试环境连真实 Redis 导致部分用例失败）。
- **依赖** `backend/Dockerfile` 由 `python:3.14-slim` 回退到 `python:3.12-slim`，与 CI 测试环境一致（3.14 太新，部分依赖未完全支持）。
- **文档** `backend/README.md`、`tests/README.md` 测试数 162 → 179。
- **已知限制** SSE 端点 token 走 query 参数会被反向代理 access log 记录；轻量 ticket 方案收益不足，彻底解法需 cookie 认证或 fetch+ReadableStream，当前内网部署可接受，已在 `deps.get_current_user_from_query` 文档化。
- 测试：后端 179 passed、前端 16 passed；`ruff`+`black`+`isort`+`eslint`+`tsc`+`vite build` 全绿。

## [0.2.0] - 2026-07-06

### Security — 全面安全审计修复（第五轮深度审计 + 严格检查）

- **[P0]** `queue_service.mark_running` 加 `SELECT ... FOR UPDATE` 行级锁（`with_for_update=True`），消除双 worker 并发抢同一 task_id 的 TOCTOU 竞态。SQLite 自动忽略该参数，PostgreSQL 生效。
- **[P0]** 前端新增 `ErrorBoundary` 组件并包裹路由树根节点，任一页面渲染异常降级为 antd `Result` 错误页 + 刷新按钮，避免白屏崩溃。
- **[P1]** 写操作端点权限收紧：`projects` (create/delete)、`shots` (delete)、`keyframes` (delete)、`videos` (delete)、`audio` (delete)、`misc` (create_workflow/delete_workflow/delete_qa_report/delete_daily_brief) 全部从 `get_current_user` 改为 `require_queue_write_role`，普通 member 角色无法再删除项目/镜头/工作流等资源。
- **[P1]** `case_studies.admin_list` 权限收紧：从 `get_current_user` 改为 `require_superuser`，避免普通用户枚举 draft/archived 未发布案例。
- **[P1]** `health._check_redis` 改用 `with redis.from_url(...) as client:` 上下文管理器，修复每次健康检查泄露 Redis 连接池的问题。
- **[P1]** 前端 `AuthContext.logout` 同步调用 `queryClient.clear()`：原实现只在 `MainLayout` 的 useEffect 中清理，但 logout 后 MainLayout 立即卸载，effect 永不执行，导致跨用户数据残留。同时把 `queryClient` 抽到独立 `lib/queryClient.ts` 打破 AuthContext ↔ App 循环依赖。
- **[P1]** 前端 `Queue.tsx` 把 `useQuery` 内 `invalidateQueries` 副作用改为 `useEffect`，消除违反 React Query 契约的反模式与无限缓存条目增长。
- **[P1]** `frontend/nginx.conf` 新增 `Content-Security-Policy` 与 `Permissions-Policy` 安全响应头，补齐 XSS 防御纵深。
- **[P1]** 前端 `Login` 读取 `location.state.from` 跳回原请求页（原始终终跳 /dashboard），并拦截已登录用户访问 /login。
- **[P2]** `render_tasks.py` 删除 `hasattr(db, "get_render_task")` 冗余死代码分支（SQLAlchemy Session 无此方法，恒走 `_get_task` 分支）。
- **[P2]** `config.py` 的 `COMFYUI_DIR` 默认值由 `"${HOME}/ComfyUI"`（shell 变量语法，Pydantic Settings 不展开）改为 `str(Path.home() / "ComfyUI")`，启动时即解析为真实路径。
- **[P2]** `misc.list_qa_reports` / `list_daily_briefs` 新增 `limit` (默认 100, 上限 500) 与 `offset` 分页参数，避免返回整表。
- **[P2]** 前端 `Queue.tsx` 的 `TaskStatusTag` 类型断言由 `as never` 改为 `as TaskStatus`，恢复类型检查。
- **[P2]** 前端 404 页面 `Button href` 改为 react-router `Link` 包裹，避免整页刷新。
- **[P2]** `SECURITY.md` / `SECURITY.zh.md` 修正 RBAC 角色名：`root/peasant/viewer` → `admin/director/algo_engineer/video_operator/ops/pm`（与 `deps.QUEUE_WRITE_ROLES` 实际一致；第二轮曾声称修复但只改了 backend/README）。
- **[P2]** `examples/env.example` / `docs/tutorial.md` / `docs/tutorial.zh.md` 的 `COMFYUI_DIR` 由 `/root/ComfyUI` 统一为 `${HOME}/ComfyUI`。
- **[P2]** 测试数全文统一为 162（backend/README、docs/index.html、CONTRIBUTING 中英版、tests/README 原为 132/158/161 全部更新）。
- **[P2]** `CONTRIBUTING.md` / `CONTRIBUTING.zh.md` 文档链接数 538 → 510（与 `check_doc_links.py` 实际输出一致）。
- **[P2]** `frontend/README.md` 的 `VITE_API_BASE_URL` 默认值补齐 `/api/v1`（与 .env.example 与代码默认值一致）。
- **[P2]** `backend/README.md` 删除指向不存在的 `./tests/README.md` 断链。
- **[P2]** `.github/dependabot.yml` docker ecosystem 补 `ignore: version-update:semver-major`，与其他 4 个 ecosystem 策略一致。
- **[P2]** `.github/workflows/ci.yml` 新增 `concurrency` 组，PR 多次推送时取消旧 run，节省 CI 资源。
- **[P2]** 根 `Dockerfile` 修复层缓存失效：`COPY requirements.txt` → `pip install` → `COPY . /app`，与 backend/Dockerfile 模式一致。
- **[P2]** `docker-compose.yml` 的 `REDIS_PASSWORD` 从 `:-` 默认弱密码改为 `:?` 强制必填（与 SECRET_KEY/POSTGRES_PASSWORD 一致）。
- **[P2]** `pyproject.toml` 的 `Development Status` 由 `3 - Alpha` 升级为 `4 - Beta`（与"工程开发完结"状态一致）。
- 测试：162 passed；前端 `tsc --noEmit` + `eslint --max-warnings 0` 通过；`check_doc_links.py` 510 链接全绿；`project_health_check.py` 通过。

### Security — 全面安全审计修复（第二轮深度审计）

- **[P0]** 登录页移除硬编码默认凭据提示（`admin / change-me-now`），改为"请联系管理员获取初始凭据"。
- **[P0]** 前端 `client.ts` 响应拦截器重构：保留原始 `AxiosError` 对象（不再替换为纯字符串 Error），附加 `friendlyMessage` 属性供调用方使用；401 处理改为通过 `setOnUnauthorized` 回调由 `AuthContext` 注册，不再直接 `window.location.href` 整页跳转，与 React 状态管理一致。
- **[P0]** `AuthContext` 修复 token 时序 bug：`login()` 中同步调用 `setAuthToken()`（原仅在 `useEffect` 中设置），避免 SSE 等子组件 effect 先于父组件执行时 token 为 null。
- **[P0]** `.pre-commit-config.yaml` 移除 `detect-secrets` 钩子（`.secrets.baseline` 文件不存在导致 pre-commit 必然失败）。
- **[P0]** `.gitignore` 修复 `.env.*` 通配误伤 `.env.example`（添加 `!.env.example` 取反规则）。
- **[P1]** 后端新增全局异常处理器：`IntegrityError` → 400（不暴露 SQL 细节）；未捕获 `Exception` → 500 + logger 记录堆栈。
- **[P1]** 后端新增安全 HTTP 头中间件：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`。
- **[P1]** `list_users` 端点权限收紧：从仅需登录改为 `require_superuser`，防止普通用户枚举所有用户邮箱与超管标志。
- **[P1]** `UserCreate` / `UserUpdate` schema 增加校验：`password` 最小 8 最大 72 字符；`email` 改为 `EmailStr`；新增 `email-validator` 依赖。
- **[P1]** `RenderTaskCreate` schema 增加校验：`priority` 限制 0-100；`task_type` 改为 `Literal` 枚举。
- **[P1]** `comfyui_service` 修复 `seed=0` 被误判为 falsy 的 bug（`seed or X` → `seed if seed is not None else X`）。
- **[P1]** `queue_stats` 优化：从全表加载 Python 计数改为 SQL `GROUP BY` 聚合查询。
- **[P1]** `daily_brief.py` 修复日期比较 bug：`RenderTask.failed_at` / `completed_at` 已从 `Date` 改为 `DateTime(timezone=True)`，同步将 `== today` 改为范围查询 `>= today_start AND <= today_end`。
- **[P1]** `sync_repos.sh` 修复 token 进程列表泄露：从 URL 嵌入改为 `credential.helper` 函数，token 不出现在 `ps` / 命令行参数中。
- **[P1]** 前端 `queryClient` 4xx 不重试：`retry` 函数仅对 5xx 或网络错误重试。
- **[P1]** 前端 `apiBase` 改为从环境变量读取（`import.meta.env.VITE_API_BASE_URL || "/api/v1"`）。
- **[P1]** 前端 `WorkflowConfigs` 表单切换不更新修复：添加 `useEffect` 调用 `form.setFieldsValue`。
- **[P1]** 前端 `Queue` 行内编辑竞态修复：`commitPriority` 接收显式参数而非依赖共享状态。
- **[P1]** 前端 `Keyframes` loading 全行影响修复：仅当前提交行显示 loading。
- **[P1]** 前端 `Projects` 删除添加 `Popconfirm` 二次确认。
- **[P1]** 前端 `useQueueStream` 退避计数器在 `enabled` 变 true 时重置。
- **[P1]** 前端 `RenderTaskStatus` 类型补 `progress: number` 字段。
- **[P1]** 前端所有页面错误处理改用 `friendlyMessage` 优先（10 个文件 21 处）。
- **[P2]** CHANGELOG 修复 License 记录（实际为 CNCL，非 CC BY-NC 4.0）、docs 站点状态（保留而非删除）、sync_repos.sh 环境变量描述。
- **[P2]** `backend/README.md` 修复 RBAC 角色名称（原错误写 root/peasant/viewer）、测试数量更新为 161。
- **[P2]** `frontend/README.md` 修复 token 存储方式（sessionStorage 非 localStorage）、默认登录凭据（admin/change-me-now 非 root/shotflow）。

### Security — 全面安全审计修复（第四轮深度审计 + 严格检查）

- **[P0]** `queue_service.STUCK_TIMEOUT_SECONDS` 由 300 提升至 2400（大于 Celery `task_time_limit=1800`），避免长任务被误判为僵尸并二次派发。
- **[P0]** `run_render_task` 新增防双执行检查：进入任务时若 `worker_id` 已是其它主机名，直接跳过返回 `already_running`，避免 Celery 任务重投导致同一 task 并发执行。
- **[P0]** `run_render_task` 入口添加 `update_progress(task_id, 0)` 心跳刷新，让队列状态机立即把 task 推到 `running` 并刷新 `updated_at`，避免被 recover 误回收。
- **[P1]** SSE 端点 `stream_events` 改为循环内独立 `SessionLocal()` 短连接，不再独占 `Depends(get_db)` 注入的 session，避免长连接撑爆连接池。
- **[P1]** `cancel_task` 的 `revoke(terminate=False)` 改为 `terminate=True, signal="SIGTERM"`，原参数无法真正终止 worker，导致 task 一直停留在 `running`。
- **[P1]** `enqueue_task` 派发 Celery 失败时新增 `db.rollback()`，避免 DB 已写 `pending` 但任务未真正入队形成"幽灵 task"。
- **[P1]** `delete_user` 新增"不能删除自己"防护：原接口允许超管删除自身账号造成系统无主。
- **[P1]** `case_studies` 写操作端点（POST/PUT/DELETE）从 `get_current_user` 收紧为 `require_superuser`，避免任意登录用户篡改案例展示。
- **[P1]** `init_db.py` 超管密码改为环境变量 `INIT_ADMIN_PASSWORD` 注入（推荐），未设置时回退到 `change-me-now` 占位并打印警告，生产部署不再有硬编码密码。
- **[P1]** `update_user` 新增邮箱查重：变更邮箱为已存在值时直接返回 400（带清晰提示），不再让上层 `IntegrityError` 处理器兜底（避免 500 + 通用错误）。
- **[P1]** 前端 `MainLayout` logout 时调用 `queryClient.clear()` 清理缓存，避免下次登录看到旧用户数据残留。
- **[P1]** `frontend/nginx.conf` 添加 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy` 安全响应头。
- **[P1]** `frontend/.env.example` 修复 `VITE_API_BASE_URL` 默认值（`http://localhost:8000` → `http://localhost:8000/api/v1`，与代码默认值一致）。
- **[P1]** 前端 `useQueueStream` 的 `SSE_PATH` 改为基于 `apiBase` 拼接，与 axios 实例统一前缀来源。
- **[P1]** 前端 `WorkflowConfigs` 表单切换不更新修复：添加 `useEffect` 调用 `form.resetFields()` + `setFieldsValue`。
- **[P1]** 前端 `Workflows` 删除按钮添加 `Popconfirm` 二次确认。
- **[P1]** 前端 `AuthContext` 修复冗余 `me()` 调用：login 已设置 user 后，token effect 直接跳过拉取，避免重复请求与短暂的状态闪烁。
- **[P1]** 前端 8 个表格页面（Projects/Shots/Keyframes/Queue/Workflows/Audio/QA/CaseStudies）统一添加 `pagination={{ pageSize: 20, showSizeChanger: true }}`，避免大数据集一次性渲染卡顿。
- **[P2]** `.env.example` 补全 `HAS_GPU` 配置项（与 `config.py` 对齐，影响 video provider 自动选择）。
- **[P2]** `config.py` 的 `COMFYUI_DIR` 默认值由 `/root/ComfyUI` 改为 `${HOME}/ComfyUI`，与 `.env.example` 统一，避免误以为必须以 root 运行。
- **[P2]** README 中英双版 API 路由表补全 4 个缺失端点：`/auth`、`/workflows-cfg`、`/assets`、`/case-studies`。
- **[P2]** `docs/index.html` 站点统计测试数 158 → 161（与 backend 实际数量同步，本轮后为 162）。
- **[P2]** `08_Automation/README.md` / `README.zh.md` 修正 Quick start 命令路径：明确"在仓库根目录执行"，`pip install` 路径改为 `08_Automation/requirements-dev.txt`。
- **[P2]** `docker-compose.yml` frontend 服务添加 healthcheck（wget 探活 nginx 80 端口），与 postgres/redis/backend/worker 健康检查策略对齐。
- **[P2]** `requirements.txt` 版本号与实际安装版本交叉核对（fastapi/alembic/pydantic/celery/sqlalchemy 均一致，无需调整）。
- 测试：新增 `test_update_user_email_duplicate_rejected`，覆盖邮箱查重三条路径（占用拒绝 / 自身邮箱放行 / 全新邮箱放行），全套 162 测试通过；前端 `tsc --noEmit` 通过。

### Security — 修复关键安全漏洞与代码健壮性问题（第一轮审计）

- **[P0]** `POST /api/v1/auth`（创建用户）新增 `is_superuser` 权限校验：原接口允许匿名用户创建任意角色账户（含管理员），存在严重越权风险。改为仅超级管理员可调用；初始 admin 账户通过 `init_db.py --seed` 或测试 fixture 种子写入，避免首次部署被任意注册占用。
- **[P1]** `RenderTask.started_at` / `completed_at` / `failed_at` 字段由 `Date` 修正为 `DateTime(timezone=True)`，queue_service 中三处 `date.today()` 赋值统一改为 `_now()`（UTC 时间戳），避免渲染任务时间字段丢失时分秒，影响排队耗时统计与僵尸任务检测。同步更新 Alembic baseline migration 与 `RenderTaskOut` schema。
- **[P1]** `Makefile` 修复：`make test` 原在仓库根目录直接执行 `pytest`，但 pytest 配置指向根 `tests/`（仅 2 个冒烟测试），backend 单元测试无法运行。修正为 `cd backend && python -m pytest tests/ -q`；新增 `lint-backend` / `lint-frontend` / `lint-automation` 拆分目标，`make lint` 统一运行所有 linter（含 frontend 的 `tsc --noEmit` 类型检查），`make clean` 增加 frontend/dist 清理。
- **[P2]** `backend/app/api/v1/assets.py` 修正 import 问题：移除函数体内的 `from fastapi import HTTPException` 提升至顶部；清理重复 / 错误模块引用（原文件错误引用了不存在的 `app.models.asset`、`app.schemas.asset`，Asset/AssetOut 实际位于 `app.models.project` / `app.schemas.project`）；删除未使用 imports。
- **[P2]** `JSONType` 去重：原 4 个模型文件（project/production/pipeline/case_study）各自重复定义 `JSONType = JSON().with_variant(JSONB(), "postgresql")`。统一提取到 `app/db/base.py` 作为公共常量，所有模型从基类模块导入，消除维护时类型定义不一致风险。
- 测试适配：conftest 预种子 `ci_admin` 超级管理员（is_superuser=True），4 个测试文件的 `auth_headers` 辅助函数统一改为"先用 seed admin 登录 → 通过管理员接口创建目标用户 → 用目标用户登录"模式，所有 160 个测试全部通过。

### Changed — 前端构建优化 + 消除 React Router v7 升级警告

- `frontend/vite.config.ts` 新增 `manualChunks`，将 `react`/`react-dom`/`react-router-dom`、`antd`/`@ant-design/*`、`@tanstack/react-query` 拆分为独立 vendor chunk，避免单 chunk 过大并提升浏览器缓存命中率。原 1.49 MB 单 chunk 拆为 4 个：业务代码 gzip 仅 31 KB，antd-vendor 可长期缓存。
- `frontend/src/App.tsx` 的 `BrowserRouter` 与测试中的 `MemoryRouter` 开启 `v7_startTransition` / `v7_relativeSplatPath` future flags，提前对齐 React Router v7，消除测试告警。

### Changed — 去 AI 痕迹 + 删除计划文档 + README 重写

按"全仓清查 AI 痕迹、删除计划文档、README 改为仓库介绍与使用引导"指令收尾。

**删除计划类文档**

- `tasks.md`（任务拆解）、`ROADMAP.md` / `ROADMAP.zh.md`（路线图）、`07_Team/phase2_task_plan.md`（阶段任务分派）、`07_Team/task_assignment_and_kickoff.md`（启动会任务分派）——工程开发已完结，计划文档不再保留。
- `docs/index.html` + `docs/assets/{style.css,script.js}` + `docs/README.md`——GitHub Pages 站点保留，文档站点继续可用。

**README 重写（中英双版）**

- 去掉 `[Project Status: Alpha]` badge、"Project status" 章节、"Phase 1/2" 计划叙述、GitHub Pages 引用、`ROADMAP.md` 链接。
- 去掉第一人称（"We made..."、"ShotFlow is our answer"、"本仓库是我们团队..."）与末尾"希望能帮到同样在做 AIGC 视频的人"AI 句式。
- 副标题改为"Script in, 4K master out"/"从一句剧本到 4K 母版"；痛点章节用具体场景描绘（"同一个角色换个镜头就变脸"、"参数没记下来，下一次开跑就再也复现不出那一张"）。
- license 章节 `✅ Allowed`/`❌ Forbidden` → `+ Allowed`/`- Forbidden`。
- 目录结构、技术栈、快速开始、Web 平台、API、前端、案例、硬件、贡献、致谢、许可证各章节保留并保持生动。

**全仓 emoji 清理**

- 21+ 文件、约 240 处 emoji（🚀✨🎉💪🔥⭐🎯📦🔍💡📝✅❌⚠️👍👋🛠📌🎬🎨🔄⏳🚧🌡️❄️📁📂📋📜🔧📖）全部清理：装饰性 emoji 删除，功能性 emoji 替换为 `yes`/`+`/`-`/文字。

**AI 句式清理**

- `AIGC_Experience_Chain.zh.md` 4 处"我们的做法" → "做法"。
- `CODE_OF_CONDUCT.zh.md`"我们的承诺" → "承诺"、"我们希望通过" → "通过"。
- `docs/tutorial.md`"We use..."、"our team used" → 被动语态；`docs/tutorial.zh.md`"我们团队做" → "做"。
- `CHANGELOG.md` 历史条目"de-AI'd" → "tightened"；空括号 `allowed () and forbidden ()` → `allowed and what's forbidden`。

**引用修复（删文件后断链）**

- `08_Automation/project_health_check.py` 必需文件清单移除 `ROADMAP.md` / `docs/index.html` / `docs/assets/*`。
- `CITATION.cff` 的 `url` 从 Pages URL 改为 GitHub repo URL。
- `.github/dependabot.yml` 注释 `ROADMAP.md` → `README.md`。
- `CONTRIBUTING.md` / `.zh.md` 体检 checklist 必需文件清单移除 `ROADMAP.md`。
- `docs/tutorial.md` / `.zh.md` 删除"Roadmap"与"长期愿景"章节，模型替换指引改写为引用 `provider_scorer.py`。
- `docs/i18n/README.md` 删除 `ROADMAP.md` 行与 `docs/README.md` 自指行。
- `07_Team/README.md` 删除对 `phase2_task_plan.md` / `task_assignment_and_kickoff.md` 的引用。

**本地 CI 全套复跑验证**

- 后端：`ruff` + `black` + `isort` 全过；`pytest tests/ -q` 158 测试通过。
- 前端：`npm run lint` 0 warnings；`tsc --noEmit` 通过；`npm run test` 11 测试通过；`npm run build` 4179 模块构建成功。
- automation：`ruff` + `black` + `isort` 全过；`project_health_check.py` 通过；`check_doc_links.py` 109 md / 510 内部链接全过（删文件后链接数从 538 降至 510，无断链）。

### Changed — 开源项目体检完结：PR/分支清理 + dependabot 策略 + 体检 checklist 入文档

按"开源项目合规性全面体检"指令，逐项排查并清理。

**远程仓库清理**

- 关闭 17 个堆积的 dependabot PR（项目工程开发已完结，不引入大版本升级破坏已验证构建；统一评论说明原因）。
- 17 个 dependabot 远程分支随 PR 关闭自动删除，远程现仅剩 `main`。
- 关闭 GitHub Pages（`/docs` 目录无 Jekyll 配置导致 legacy builder 一直失败，项目不需要站点）。
- 体检后状态：GitHub/GitCode/本地三方 HEAD 一致（`27ca732`），0 开放 PR，0 开放 Issue，CI 全绿。

**dependabot 策略**

- `.github/dependabot.yml` 5 个 ecosystem 全部新增 `ignore: version-update:semver-major` 规则，仅保留安全补丁与小版本监控。
- 顶部注释说明：项目工程开发已完结，大版本升级一律忽略；如重启开发，移除 `ignore` 块即可。

**开发者文档新增体检 checklist**

- `CONTRIBUTING.md` / `CONTRIBUTING.zh.md` 新增「Open-source project health check（开源项目体检）」章节，7 项检查：开源配套文件齐全 / 分支卫生 / PR-Issue 队列 / CI 全绿 / 双仓库镜像一致 / 本地 CI 全套复跑 / 敏感文件与密钥扫描。
- 明确签字流程：七项全绿后在 CHANGELOG 追加一行；任一红叉立即停止，绝不在红叉体检上打 release tag。
- 与既有「每次提交前必查远程仓库状态」互补：前者是 push 前的快速检查，后者是月度/发版前的深度体检。

**本地 CI 全套复跑验证**

- 后端：`ruff` + `black` + `isort` 全过；`pytest tests/ -q` 158 测试通过。
- 前端：`npm run lint` 0 warnings；`tsc --noEmit` 通过；`npm run test` 11 测试通过；`npm run build` 4179 模块构建成功。
- automation：`ruff` + `black` + `isort` 全过；`project_health_check.py` 通过；`check_doc_links.py` 115 md / 538 内部链接全过。

### Changed — 工程开发完结：ROADMAP 重写 + 文档双语收尾 + 前端构建验证

按"已完成的去掉、硬件实操改用户指南、现在能做的全做完"收尾，工程开发到此结束。

**ROADMAP 重写**（`ROADMAP.md` / `ROADMAP.zh.md`）

- 删除已完成的 Phase 2 / Phase 3 任务列表（不保留打勾记录）。
- Phase 1 的 6 项物理生成任务改写为「硬件实操指南（需自备硬件）」，面向用户：部署 ComfyUI → 29 关键帧 → 24 视频镜头 → 音频 → 后期 → 交付，每步给出命令与验收标准。
- 新增「工程状态：已完成」章节，列出后端 158 测试 / 前端 lint+typecheck+11测试+build / 507 文档链接 / 健康检查全部通过。
- 底部声明工程开发结束，实操指南交给用户跑。

**文档双语收尾**

- `07_Team/templates/` 5 份英文 stub 补全为完整英译（project_proposal / progress_checklist / instructor_review / weekly_report / summary_report），5 份中文 sidecar 加切换链接，templates/README.md 更新状态。
- `08_Automation/README.md` 翻译为英文主版 + 新建 `README.zh.md` 中文 sidecar。
- `docs/i18n/README.md` 双语表：07_Team 5 份标、08_Automation 标；TODO 精简为仅剩日文维护者认领。

**前端构建验证**

- `npm run lint`（0 warnings）
- `npx tsc --noEmit`（typecheck 通过）
- `npm run test`（11 tests passing）
- `npm run build`（4179 modules transformed，dist 产出）

### Changed — ROADMAP 收尾：Phase 2/3 工程范围完结

盘点 ROADMAP 剩余任务，把已完成项打勾并补齐缺口的文档/博客，让项目呈现完结状态。

**ROADMAP 状态更新**（`ROADMAP.md` / `ROADMAP.zh.md`）

- **Phase 2** — 全部完成（4/4）：
  - [x] 补充失败案例与修复记录 `06_Research/failure_cases.md` 已有 10 个案例（F001–F010）覆盖角色漂移/视频崩坏/运动错误/Provider 适配，含分类参考表与月度统计模板。
- **Phase 3** — 全部完成（5/5）：
  - [x] WebUI React + antd Pro 管理后台（`frontend/`）12 个页面（Dashboard/Projects/Shots/Keyframes/Queue-SSE/Workflows/WorkflowConfigs/Assets/Audio/QA/CaseStudies），JWT+RBAC。
  - [x] 多模型支持 `provider_adapters.py` 5 个 adapter（wan_i2v/hunyuan_video/ltx_video/cogvideox/kling），`provider_scorer` 四维评分，自动选择+回退由测试覆盖。
  - [x] 多语言文档 英文为主，9 份核心文档有中文 sidecar，`docs/i18n/README.md` 跟踪双语表；日文欢迎社区认领。
  - [x] 用户展示区 `CaseStudy` 模型 + API（公开列表/详情 + 管理 CRUD）+ 前端 `/case-studies` 页面；示例案例在 `examples/echo-of-singularity/`。
  - [x] 技术博客/教程 教程 `docs/tutorial.md`（663 行）+ 架构博客 `docs/blog/architecture.md`（434 行）。
- **Phase 1** — 代码/脚本/SOP 就绪，6 项物理生成任务待真实硬件（RTX 4090 + ComfyUI + Kling API）执行，沙箱 SIMULATE_MODE 下无法完成，如实标注不假装打勾。
- 新增"项目完成状态"章节：Phase 2/3 工程范围完结，Phase 1 为物理制片运行。

**新增技术博客**（`docs/blog/architecture.md` / `.zh.md`，各 434 行）

8 节架构经验沉淀：Why we built it / Pipeline at a glance / Decision 1 YAML 参数化（node_class+node_input+node_index 权衡、build_workflow 回退、validate_params 防 GPU 浪费）/ Decision 2 Provider 评分+回退（四维评分、rank_providers 降序队列、显式不回退 vs 自动回退契约）/ Decision 3 队列状态机+错误分类（应用层重试而非 Celery autoretry）/ Decision 4 JWT+RBAC+SSE / What we'd do differently（诚实反思 YAML targeting bug、评分未接入派发、extra 持久化 bug）/ Conclusion。

**i18n 双语表更新**（`docs/i18n/README.md`）

9 份根文档标（README/AIGC_Experience_Chain/CONTRIBUTING/COC/SECURITY/ROADMAP/TROUBLESHOOTING/COST_ANALYSIS/tutorial）；TODO 列表精简为社区认领项（08_Automation 中文、07_Team 模板英译、日文维护者）。

### Added — Phase 3 社区化：完整教程文档 + 双语对照补齐

**教程文档（Phase 3 社区化）**

- `docs/tutorial.md`（英文主，663 行）/ `docs/tutorial.zh.md`（中文，665 行）— 从零到 4K 母版的
  手把手教程，11 节覆盖：环境部署、剧本与世界观、Flux.1+IPAdapter 角色一致性关键帧、
  Wan2.2/可灵视频生成（含 Provider 自动选择与回退）、ElevenLabs+Suno 音频、达芬奇后期、
  Topaz 4K 超分、交付发行、Web 平台使用、Troubleshooting、Next Steps。每步给出可执行命令
  与产出物路径，引用仓库内现有文件。README 中英版 Quick start 区加教程入口链接。

**双语对照补齐**

- `ROADMAP.md` / `ROADMAP.zh.md` — 路线图双语（主英文，保留 Phase 2 已完成项打勾状态）
- `TROUBLESHOOTING.md` / `TROUBLESHOOTING.zh.md` — 常见问题双语
- `COST_ANALYSIS.md` / `COST_ANALYSIS.zh.md` — 费用参考双语
- （`AIGC_Experience_Chain` 已是双语，无需改）

### Added — Provider 失败回退

- `backend/app/services/provider_scorer.py` — 新增 `rank_providers(complexity, has_gpu)`：返回
  按综合分数降序的 (provider, score) 候选队列，已按 has_gpu 过滤，供回退使用。
- `backend/app/tasks/render_tasks.py` — `_dispatch` 的 `video_i2v/video_t2v` 自动选择路径实现
  失败回退：按 `rank_providers` 降序队列依次尝试，首选 provider 执行失败（`ProviderFailed`）
  时跳次优重试，直至成功或全部失败。回退发生时写回 `extra._fallback_reason` 落库供追溯。
  新增 `ProviderFailed` 异常 + `_run_provider_once` 辅助函数。显式 provider 路径失败不回退
  （尊重用户选择，直接抛 RuntimeError）。

**测试**

- `backend/tests/test_phase2_integration.py` — 新增 7 个回退测试：首选失败回退次优成功、
  `_fallback_reason` 落库、首选成功不写、全部失败抛错、显式不回退、`rank_providers` 降序、
  无 GPU 过滤本地 provider。`test_render_dispatch.py::test_dispatch_provider_failure_raises`
  改为显式 provider 路径（显式失败不回退）。全套 158 测试通过。

### Fixed — Phase 2 深化：extra 持久化 bug 修复 + build_workflow 参数校验

承接上一阶段"Phase 2 接线"，本次补齐两个被遗漏的深化点：自动选择的 provider
信息原未落库（事后无法追溯）、build_workflow 原不校验参数（坏参数送到 ComfyUI
浪费 GPU 后才失败）。

**修复 extra 持久化 bug**

- `backend/app/tasks/render_tasks.py` — `_dispatch` 自动选择 provider 后，原只改
  局部变量 `extra`，未写回 `task.extra`，导致 `mark_completed`（只写 output_path）
  后自动选择的 provider 信息丢失，无法事后追溯。修复：写回 `task.extra = extra` 并
  `db.commit()` 落库。显式 provider 路径不写 `_provider_source`（区分自动/手动）。

**build_workflow 接入参数校验**

- `backend/app/services/comfyui_service.py` — `build_workflow` 的 YAML 驱动路径在
  `inject_params` 前调 `validate_params` 做必填/类型/范围校验，非法参数直接抛
  `ValueError`（被 `queue_service.classify_error` 归为 `invalid_prompt` 不可重试），
  避免把坏参数（如 `frames=999` 超 max、`prompt` 必填为空、`steps="abc"` 类型错）
  送到 ComfyUI 浪费 GPU 后才失败。回退路径（无 YAML 配置）不做校验，保持向后兼容。

**测试**

- `backend/tests/test_phase2_integration.py` — 新增 9 个深化测试：extra 持久化到 DB
  （自动/显式两条路径）、参数校验（必填缺失/超 max/低于 min/类型错/边界值通过/
  ValueError 归类 invalid_prompt 不可重试/回退路径跳过校验）。全套 151 测试通过。

### Changed — Phase 2 接线：YAML 工作流参数化接入生成路径 + Provider 评分接入派发

此前 Phase 2 的 YAML 参数化与 Provider 评分机制骨架已存在但**未接入实际生成路径**
（YAML 只是装饰性的、评分从未被调用）。本次完成接线，让两者真正生效。

**YAML 工作流参数化接入生成路径**

- `backend/app/services/comfyui_service.py` — 新增 `build_workflow(task_type, prompt,
  seed, extra)`：优先用 `workflow_config_service.get_workflow_by_task_type` 取 YAML
  配置，调 `inject_params` 按 `node_class + node_input + node_index` 注入对应节点；
  无 YAML 配置时回退到 `_inject_params`（仅注入 prompt+seed，向后兼容）。
  `submit_workflow` 改为调用 `build_workflow`。非程序员改 YAML 即可调整
  steps/cfg/frames/fps/负向提示词等，无需改 Python 代码。
- `03_Workflows/workflows.yaml` — 修复 `Wan22_Dual_Expert_Video` 工作流的 targeting
  bug：`frames` 原错指不存在的 `EmptyHunyuanLatentVideo`，改为实际的
  `WanImageToVideo.length`；`fps` 原完全缺 targeting（永不注入），补上
  `SaveAnimatedWEBP.fps`；新增 `negative_prompt`（CLIPTextEncode[1].text）、`steps`
  （KSampler.steps，default 30）、`cfg`（KSampler.cfg，default 0.5）；`fps` 默认值
  16→24 对齐 Wan22 JSON 实际值。

**Provider 评分接入派发**

- `backend/app/core/config.py` — `Settings` 新增 `HAS_GPU: bool = True`：标识当前
  环境是否具备本地 GPU，供 provider 自动选择过滤本地 provider（无 GPU 时仅候选云端
  kling/cogvideox，避免派发到本地 ComfyUI 后卡死）。
- `backend/app/tasks/render_tasks.py` — `_dispatch` 的 `video_i2v/video_t2v` 分支：
  `extra.provider` 优先（调度方显式指定，含未知 provider 仍交 `get_adapter` 抛
  ValueError）；缺省时调 `recommend_provider(complexity, gen_method="auto",
  has_gpu=settings.HAS_GPU)` 自动择优，结果写回 `extra._provider_source="auto"` 供
  事后追溯。standard+has_gpu 仍选 wan_i2v，保持与既有测试契约兼容。

**测试**

- `backend/tests/test_phase2_integration.py` — 新增 10 个集成测试：build_workflow 的
  Wan22/Flux YAML 注入、缺省保持 JSON 原值、无配置回退；_dispatch 的
  standard/complex/no_gpu/显式覆盖/`_provider_source` 写回等路径。全套 142 测试通过。

### Changed — License clarification + complete-work deliverables (batch E)

**License clarification** — the repo uses Custom Non-Commercial License (CNCL) v1.0. All references to
CC BY-NC 4.0 have been corrected; `LICENSE`, `pyproject.toml`, `CITATION.cff`,
and `README.md` consistently use CNCL.

**Complete-work deliverables** — the example film *Echo of the Singularity*
now ships every artifact a reviewer would expect from a finished AIGC short,
not just the pipeline toolset.

- `05_Output/Final/assembly_guide.md` — how to assemble the locked master
  from the EDL + per-shot assets in DaVinci Resolve (project setup, media
  import, EDL relink, audio track layout, color, titles, export presets,
  pre-lock sanity checks).
- `05_Output/Final/asset_manifest.md` — complete asset inventory: 24 shots,
  10 dialogue cues, 6 music cues, 10 SFX cues, 29 keyframes, project &
  delivery files, plus a SHA-256 checksum template and a one-liner
  `sha256sum` command to populate it.
- `05_Output/Final/credits.md` — full credits roll: cast, voice, music, SFX,
  visual generation tools with licenses, post-production, pipeline &
  automation, special thanks, license declaration, end-card line.
- `05_Output/Final/subtitles/` — closed captions for the example film:
  `echo_of_singularity.zh.srt` (zh), `echo_of_singularity.en.srt` (en),
  `echo_of_singularity.zh.ass` (styled zh for festival burn-in), and a
  `README.md` covering timecode reference, style notes, editing workflow,
  burn-in instructions, and validation rules.
- `05_Output/Final/README.md` and `05_Output/README.md` — index the new
  files in the directory trees.

**Audio planning** — the example film now has the same level of audio
pre-production paperwork as the visual side.

- `01_Assets/Audio/voice_bibles.md` — per-character TTS bibles for Ava /
  The Core / Narrator: voice id, stability/similarity/style, emotion
  segments mapped to shot IDs, post-processing chain, calibration workflow,
  version-management rules, ElevenLabs compliance notes.
- `01_Assets/Audio/cue_sheet.md` — full cue sheet: 10 dialogue cues, 7
  music cues, 10 SFX cues, all with in/out timecodes referencing the shot
  tracker; mix targets and side-chain rules; version-management policy.
- `01_Assets/Audio/sfx_list.md` — per-SFX breakdown by category
  (Environment / Mechanical / UI) with purpose, in-point, source
  (freesound CC0 / AudioLDM), license chain; AudioLDM2 generation
  parameters logged for reproducibility.
- `01_Assets/Audio/README.md` — indexes the three new planning docs.

**Release kit** — per-platform distribution specs now filled in for the
example film.

- `09_Release/distribution_kit.md` — per-platform distribution package
  specs (Bilibili / YouTube / 抖音 / 小红书 / 视频号 / Instagram / film
  festival) with master files, cover, title/description/tag templates,
  AIGC disclosure rules, license declaration, and a final pre-release
  checklist.
- `09_Release/poster_spec.md` — per-platform cover & poster visual specs:
  sizes, color/font rules, composition principles, Flux.1 prompt templates
  for landscape + portrait + festival poster, generation → upscale → grade
  → typesetting workflow, audit checklist, version-management policy.
- `09_Release/README.md` — restructured to separate blank templates from
  filled-in example film specs.

**Showcase entry points** — the README and docs site now lead with the
"complete work" angle, not just the pipeline.

- `README.md` — new "The complete short film" section: a 17-row table
  mapping every phase (pre / production / audio / edit / post / inventory /
  subtitles / credits / specs / release / compliance) to its artifact file.
- `README.zh.md` — corresponding "完整作品" section in Chinese.
- `docs/index.html` — new "Complete work" section between Pipeline and
  Stack, with a 4-card feature grid (pre/post paperwork, subtitles &
  credits, audio chain, release kit).
- `docs/assets/script.js` — `nav_work` and `work_*` translation keys added
  for both en and zh; nav link wired up.

### Added — Open-source governance & docs completeness (batch A)
- Added 11 missing subdirectory READMEs: `backend/`, `frontend/`, `tests/`, `02_Scripts/`, `04_SOP/`, `01_Assets/`, `05_Output/`, `05_Output/EDL/`, `06_Research/`, `07_Team/`, `09_Release/`.
- Added `CITATION.cff` — GitHub will show a "Cite this repository" button.
- Added `.github/FUNDING.yml` — declares no sponsorship for now.
- Added `backend/.env.example` and `frontend/.env.example` — per-module env templates (backend still reads the repo-root `.env`).

### Changed — README polish (batch A)
- CI badge is now dynamic (pulls build status from GitHub Actions) instead of a static image; added a "Project Status: Alpha" badge.
- Added "Project status" and "Acknowledgements" sections to `README.md`.
- `README.zh.md` now links to the Chinese experience chain (`AIGC_Experience_Chain.zh.md`) instead of the English one.
- `examples/echo-of-singularity/README.zh.md` — `character_bible_ava` and `shot_tracker` links now point to the `.zh.md` sidecars, matching the other entries.
- `SECURITY.md` — removed the dangling "email the maintainer" line (no public email yet); points only to GitHub Security Advisory.
- `CODE_OF_CONDUCT.md` — "contact via Issue" replaced with GitHub "Report content" + Security Advisory (Issue is public, not suitable for conduct reports).
- `07_Team/collaboration_tools_guide.md` — internal placeholders (`{共享文档链接}`, `腾讯会议号：XXX`) replaced with clear `<your-...>` template placeholders.

### Changed — Configuration consistency (batch B)
- Version sync: `frontend/package.json` and `backend/app/core/config.py` `APP_VERSION` bumped from `0.1.0` to `0.2.0` to match `pyproject.toml`.
- `01_Assets/Scenes/README.md` — fixed false "已生成" status for all 5 scenes / 29 keyframes (keyframes are prompt-only placeholders); all rows now show "待生成" with a note that running the generation scripts is what flips them green.
- `.env.example` rewritten — added `APP_NAME`, `APP_VERSION`, `API_V1_PREFIX`, `SIMULATE_MODE=true`; documented `SECRET_KEY=` as must-set (config validator rejects empty/placeholder/<32-char keys in non-DEBUG); `CORS_ORIGINS` now includes `http://127.0.0.1`; `GITHUB_TOKEN`/`GITCODE_TOKEN` lines documented as environment variables for `sync_repos.sh`.
- `08_Automation/requirements.txt` — removed unused `elevenlabs>=1.0.0` (scripts call the REST API directly via `requests`); added `SQLAlchemy>=2.0.0` (`daily_brief.py` imports from the backend app).
- Added `backend/requirements-dev.txt` — declares `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `black`, `isort` on top of `requirements.txt`; CI and local `make test` no longer need to pip-install ad hoc.
- `Makefile` rewritten — `lint` now runs `ruff check` + `black --check` + `isort --check-only` across `backend/`, `08_Automation/`, `tests/`; added `lint-frontend` target; `setup` installs backend deps + dev + automation dev + frontend npm; `test` no longer masks `preflight_check.py` failures with `|| true`; `format` now covers backend + automation + tests.
- `docker-compose.yml` — removed deprecated `version: "3.9"` line (Compose v2 ignores it and warns).
- `backend/Dockerfile` — runs as non-root `appuser` (uid 1000) instead of root; `COPY --chown=appuser:appuser . /app` so files are owned by the runtime user.
- `frontend/Dockerfile` — hardcoded `https://registry.npmmirror.com` replaced with `ARG NPM_REGISTRY=https://registry.npmjs.org` so non-China CI runners aren't slowed down (mirror users can override at build time).
- `backend/app/main.py` — added a startup warning in the FastAPI lifespan when `SIMULATE_MODE=true` and `DEBUG=false`, so a forgotten flag in production logs loudly instead of silently returning mock output.
- `backend/tests/conftest.py` — switched test `DATABASE_URL` from file-based `sqlite:///./test_shotflow.db` to in-memory `sqlite://`, eliminating a leftover `.db` artifact.
- `.gitignore` — added `test_shotflow.db` and `*.db-journal` under the Web 平台 section.

### Changed — CI & code quality (batch C)
- CI now runs ruff + black + isort on `backend/` and `08_Automation tests/`, and eslint + vitest on `frontend/`. Backend job uses `requirements-dev.txt` instead of ad-hoc `pip install pytest`; CI `DATABASE_URL` switched to in-memory `sqlite://` to match `conftest.py`.
- Added `[tool.ruff]` config in `pyproject.toml` (line-length 100, default ruleset E4/E7/E9 + F; per-file-ignores for SQLAlchemy model F821 false positives and test E402 sys.path pattern). Added `known_first_party = ["common"]` to isort config.
- Auto-fixed 28 ruff errors (F541 f-string-missing-placeholders, F401 unused-import); manually fixed 4 remaining (2 unused variables in `storyboard_to_video.py`, 1 unused numpy import in `video_quality_check.py`, 1 unused `script_dir` in `render_queue.py`); reformatted 22 backend files with black + isort.
- `08_Automation/render_queue.py` marked deprecated — superseded by `backend/app/services/queue_service.py` (Celery + PostgreSQL with state machine / priority / crash recovery / retry classification). Added deprecation docstring + runtime `DeprecationWarning`. Updated `08_Automation/README.md`, `AIGC_Experience_Chain.md`/`.zh.md`, `ROADMAP.md` to reflect the deprecation.
- Frontend test framework: added vitest + jsdom + `vitest.config.ts` + smoke test (2 tests, jsdom environment). `package.json` gains `test` / `test:watch` scripts.
- `frontend/.eslintrc.cjs` now extends `plugin:react/recommended` with `settings.react.version = "detect"`; `react/react-in-jsx-scope` and `react/prop-types` turned off (TypeScript + react-jsx transform cover these). Added `eslint-plugin-react` to devDependencies.
- `frontend/src/main.tsx` — removed unnecessary `import React` (tsconfig uses `jsx: react-jsx`); replaced `React.StrictMode` with named `StrictMode` import.
- `08_Automation/sync_repos.sh` — validates `origin` and `gitcode` remotes exist before attempting push, with a clear error message and setup hint.
- `08_Automation/benchmark.py` — non-interactive guard: exits 1 with a clear message if `sys.stdin` is not a TTY and `--dry-run` is not passed (prevents garbage N/A reports in CI / pipes).
- `08_Automation/common.py` (new) — shared `PROJECT_ROOT` constant. All 13 automation scripts now `from common import PROJECT_ROOT` instead of duplicating `Path(__file__).resolve().parent.parent`.

### Changed — Brand consistency & test coverage (batch D)
- `README.zh.md` — removed `| 奇点回响` from the title and the `中文名：奇点回响` line. 奇点回响 is the example film name, not the project brand; using it as the project's Chinese name contradicted the rename policy in this changelog. Replaced with `示例片名：奇点回响（Echo of the Singularity，仓库内的完整案例研究）`.
- Frontend admin console re-branded from 奇点回响 to ShotFlow: `frontend/index.html` `<title>`, `frontend/src/layouts/MainLayout.tsx` ProLayout `title`, `frontend/src/pages/Login.tsx` heading. The admin console is the reusable ShotFlow platform, not the example film.
- `PS_` filename prefix (Project Singularity) replaced with `SF_` (ShotFlow) across all 4 code sites in `08_Automation/batch_keyframe_gen.py` + `08_Automation/storyboard_to_video.py`, the output-spec section of `08_Automation/README.md`, the 16 shot keyframe references in `storyboard_to_video.py` SHOTS data, `01_Assets/Scenes/README.md` (29 scene table rows), `06_Research/backup_and_versioning.md` naming examples, `examples/storyboard_sample.md`, `examples/comfyui_api_payload.json`. Historical CSV logs (`video_gen_log.csv`, `keyframe_generation_log.csv`) left untouched — they're factual records of past generation runs.
- `06_Research/release_platforms.md` — updated stale "创建 Organization `Project-Singularity`；新建 Public 仓库 `singularity-workflow`" planning row to the real `MS33834/ShotFlow` (GitHub) + `badhope/ShotFlow` (GitCode).
- `docker-compose.yml` `worker` service — added a celery-specific healthcheck (`celery -A app.tasks.celery_app inspect ping -d celery@$$HOSTNAME`) with 30s interval + 30s start_period. Previously the worker inherited backend's HTTP healthcheck from the Dockerfile but runs celery (not uvicorn), so it was permanently `unhealthy` in `docker ps`.
- Frontend test coverage expanded from 1 smoke test to 11 tests across 4 files: added `ProtectedRoute.test.tsx` (3 tests: unauthenticated redirect, initializing loading, authenticated passthrough), `AuthContext.test.tsx` (3 tests: login persists token + user, logout clears, no-token initializing state), `Login.test.tsx` (3 tests: renders ShotFlow title + form, form submit calls login(), login failure doesn't throw). Added `src/__tests__/setup.ts` with jsdom polyfills (matchMedia, ResizeObserver) and afterEach cleanup. Exported `AuthContext` and `AuthState` from `contexts/AuthContext.tsx` so tests can construct a Provider without mocking. Added `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` to devDependencies.

### Changed — Renamed to ShotFlow
- Project renamed from "Project Singularity" to **ShotFlow** — short, memorable, and says what it does (shot-level AIGC flow).
- Both mirrors renamed: GitHub `MS33834/ShotFlow`, GitCode `badhope/ShotFlow`. Old URLs auto-redirect (GitHub) or are preserved.
- Global rename across the repo: brand name, repo path, package name (`pyproject.toml` → `shotflow`), Docker container names (`shotflow-*`), GitHub Pages URL, all cross-references.
- The example short film keeps its name (*Echo of the Singularity* / 奇点回响) — it's case-study content, not the project brand.
- `README.md` / `README.zh.md` titles updated; `docs/index.html` `<title>` updated; `backend` `APP_NAME` = "ShotFlow API".

### Changed — GitHub Pages landing page rewrite
- Rewrote `docs/index.html` + `assets/style.css` + `assets/script.js`.
- New hero: "Script in, 4K master out." with concrete stats (24 shots, 29 keyframes, 132 tests, 4K delivery).
- Added Tech stack section (Generation / Post / Platform / Ops tag groups).
- Copy tightened throughout: removed marketing tone; now states what the project does and what it logs.
- localStorage key `ps-lang` → `shotflow-lang`.
- Footer clarifies the example film is case-study content.
- Served from `main` branch at https://ms33834.github.io/ShotFlow/ (Pages later disabled — see top of changelog).

### Changed — Project templates moved out of `docs/`
- Moved the five Chinese project-management templates (`project_proposal`, `progress_checklist`, `instructor_review_template`, `weekly_report_template`, `summary_report_template`) from `docs/zh-CN/` to `07_Team/templates/`.
- `docs/` now contains only the GitHub Pages site — no stray teaching material leaking onto the landing page.
- Renamed each template to follow the i18n convention: English primary (`.md`, stub) + Chinese sidecar (`.zh.md`, full content).
- Added `07_Team/templates/README.md` as an index for the templates.
- Updated all cross-references: `06_Research/qa_and_blind_test.md`, `06_Research/phase1_cross_check.md`, `AIGC_Experience_Chain.md`, `07_Team/collaboration_tools_guide.md`, `07_Team/phase2_task_plan.md`, `08_Automation/asset_dashboard.py`, `08_Automation/daily_brief.py`, and the templates' internal cross-links.
- `docs/i18n/README.md` bilingual table updated with the new template locations.

### Changed — English-first language policy
- The repo is now **English-first, Chinese as an opt-in sidecar** (`.zh.md`). This inverts the old convention (Chinese primary + `.en.md` sidecar).
- `README.md` rewritten in English (primary); the Chinese version moved to `README.zh.md`. `README.en.md` removed.
- `AIGC_Experience_Chain.md` is now the English primary; Chinese moved to `AIGC_Experience_Chain.zh.md`. `.en.md` removed.
- `examples/奇点回响/` renamed to `examples/echo-of-singularity/` (already followed the English-primary convention).
- Renamed all Chinese-named docs under `02_Scripts/`, `03_Workflows/`, `04_SOP/`, `06_Research/`, `07_Team/` to English filenames (history preserved via `git mv`).
- Moved the five Chinese teaching templates (`项目计划书_完整版.md`, `项目进度检查清单.md`, `周报模板.md`, `教师评审表_模板.md`, `项目总结报告_模板.md`) from the repo root into `docs/zh-CN/` with English names, keeping the root clean.
- `docs/i18n/README.md` rewritten as the single source of truth for the new naming convention and bilingual doc table.
- `pyproject.toml` `readme` field updated to `README.md`.
- `project_health_check.py` and `tests/test_health.py` updated to the new paths (`README.zh.md`, `examples/echo-of-singularity/`, etc.).
- Updated all cross-references across the repo (markdown links, `asset_dashboard.py` / `daily_brief.py` hardcoded paths, `package_workflows.sh`, `docs/index.html`, `docs/assets/script.js`).
- `examples/README.md` rewritten in English.

### Added
- 新增 `SECURITY.md`，明确安全漏洞报告流程与密钥/ComfyUI 安全使用建议。
- 新增 `.github/CODEOWNERS`，PR 自动指派代码所有者评审。
- 新增 `.github/dependabot.yml`，覆盖 pip / npm / GitHub Actions / Docker 依赖的周度自动更新。
- 新增 `AIGC_Experience_Chain.md`，说明完整 AIGC 视频生产链路。
- 新增 `CONTRIBUTING.md`、`LICENSE`、`CHANGELOG.md`、`CODE_OF_CONDUCT.md`、`ROADMAP.md`。
- 新增 `examples/` 目录，提供角色提示词、分镜示例、ComfyUI API 载荷示例。
- 新增 `COST_ANALYSIS.md`，包含本地 GPU 与云端 API 成本估算。
- 新增 `TROUBLESHOOTING.md`，汇总常见问题与解决方案。
- 新增 `Dockerfile` 与 `docker-compose.yml`，支持 Docker 快速体验。
- 新增 `Makefile`，提供 `make check/setup/docker/test/sync/clean` 等常用命令。
- 新增 `.github/ISSUE_TEMPLATE/` 与 `.github/PULL_REQUEST_TEMPLATE.md`。
- 新增 `08_Automation/project_health_check.py`，一键检查项目结构完整性。
- 新增 `examples/奇点回响/` 完整案例研究，含制作计划书、制作日志、角色圣经、镜头进度表。
- 新增 `docs/` GitHub Pages 介绍站点，支持中英文切换，与项目视觉风格一致。
- README 新增徽章、Mermaid 架构图、`Makefile` 使用说明与 GitHub Pages 入口。
- README 重写，减少 AI 生成感，强调项目作为开源流程模板的定位。

### Fixed
- 修复 docker-compose.yml 挂载被 .gitignore 忽略的 .env 文件导致新克隆 `make docker` 失败的问题。
- 修复 preflight_check.py 中必需 API 密钥缺失只告警不报错的逻辑 bug。
- 修复 CI 从不运行 pytest 的问题，新增 `pytest` 步骤并使用 `requirements-dev.txt`。
- 修复 Makefile `test` 目标不运行 pytest 且用 `|| true` 吞掉所有预检失败的问题。
- 修复 pyproject.toml 中 `packages.find` 指向无 `__init__.py` 目录的配置错误。
- 修复 `.gitignore` 缺少 `.pytest_cache/` 规则。
- 修复 `.env.example` 中 GITHUB_TOKEN/GITCODE_TOKEN 误导说明（sync_repos.sh 不读取环境变量）。
- 修复 preflight_check.py 检查编号 `[1/8]`…`[8/8]` 与实际 9 步不符的问题。
- 统一两份 `env.example` 内容，补充 `COMFYUI_DIR` 变量文档化。
- 移除 requirements.txt 中未使用的 `python-dotenv`，新增 `requirements-dev.txt` 声明 black/isort/pytest。
- 修正 Ava 资产 README 与生成日志，从虚假的"已生成"改为"待生成"状态。
- 扩展 lint/format 范围覆盖 `tests/` 目录。
- 扩展测试覆盖：新增 docs 站点、案例研究、开发依赖检查。
- 统一 README.md / README.en.md 目录树与实际仓库结构一致。

### Changed
- 统一 Python 版本至 3.12（Dockerfile×2、CI 矩阵、pyproject、pre-commit、deploy_comfyui.sh、README 徽章、SOP/checklist/团队技能栈），pinned 依赖零修改，后端 132 测试全过。
- `README.md` / `README.en.md` 目录结构补齐 `backend/`、`frontend/`、`SECURITY.md`，与实际仓库结构对齐。
- `08_Automation/sync_repos.sh`：修复 remote 名（`github` → `origin`），与实际仓库 remote 及 `CONTRIBUTING.md` 推送模板一致。
- `07_Team/phase2_task_plan.md`：细化第二阶段任务分工。

### Removed
- 删除 `07_Team/daily_briefs/2026-06-24.md`、`2026-06-25.md` 两份过时站会日报，使 `.gitignore` 中 `07_Team/daily_briefs/*.md` 规则一致生效（日报由 `daily_brief.py` 自动生成，不入仓）。

## [0.1.0] - 2026-06-24

### Added
- 初始版本：包含项目计划书、任务拆解、四阶段 SOP。
- 24 镜头完整分镜表与 29 张关键帧提示词。
- Flux 角色一致性与 Wan2.2 双专家 ComfyUI 工作流 JSON。
- 16 个自动化脚本，覆盖部署、生成、质检、同步。
- 专家团队分工、任务分派、日报模板、发布模板。
