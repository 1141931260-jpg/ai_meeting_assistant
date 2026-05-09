# AI 会议纪要与任务跟踪系统设计

日期：2026-05-09

## 目标

从零实现一个可本地运行、可接真实第三方 API 的 AI 会议助手。系统支持上传会议音频或文本，生成转写、摘要、决策、风险、行动项，并提供 Speaker 与参会人映射、SSE 处理进度、历史会议语义检索和行动项管理。

首版以真实 API 为主路径，Mock 仅用于缺少 Key 或显式配置 `mock` 时的兜底演示。

## 已确认的技术方向

- 后端：Python 3.10+、FastAPI、SQLAlchemy、SQLite、Pydantic、LangGraph、ChromaDB、SSE、Uvicorn。
- 前端：React 19、TypeScript、Vite、TailwindCSS、React Router、Fetch API、EventSource。
- Provider：三类 AI 能力解耦为 ASR、LLM、Embedding。
- 自定义 API 方案：LLM 和 Embedding 采用 OpenAI-compatible 接口；ASR 采用通用 HTTP JSON 映射。
- 视觉风格：参考用户提供的图片，采用深色左侧栏、暖米色内容区、金色强调色的“AI 会议知识工作台”风格。

## 架构

前端负责页面展示、文件上传、SSE 监听、Speaker 映射编辑、行动项编辑和搜索交互。后端按 `routers -> services -> providers` 分层，避免路由层直接写业务逻辑或第三方 API 调用。

核心数据保存在 SQLite。会议内容向量索引保存在 ChromaDB。搜索时由 ChromaDB 返回候选结果，再回查 SQLite 补充会议标题、内容类型、Speaker 映射后的展示名等最新信息。

工作流由 `meeting_workflow` 编排，节点包括加载会议、加载参会人、音频转写或文本切分、Speaker 检测、摘要生成、决策提取、风险提取、行动项提取、向量索引构建和完成状态标记。每个节点写入 `processing_events`，SSE 接口向前端推送进度。

## 后端设计

### 数据模型

实现以下表：

- `meetings`：会议基础信息、文件路径、来源类型、处理状态、是否启用说话人分离。
- `participants`：参会人姓名、角色、邮箱。
- `speaker_mappings`：将 `Speaker 1`、`Speaker 2` 等标签映射为参会人或手动显示名。
- `transcript_segments`：转写片段，包含顺序、起止时间、原始 speaker、文本内容。
- `meeting_summaries`：会议总览、关键点、结论、按说话人摘要。
- `decisions`：关键决策、原因、证据、相关说话人。
- `risks`：风险类型、描述、等级、负责人、证据、建议。
- `action_items`：任务标题、描述、负责人、截止时间、优先级、状态、证据、来源说话人。
- `processing_events`：workflow 进度事件。

所有主键使用 UUID 字符串。所有表包含 `created_at`；需要编辑的表包含 `updated_at`。删除会议时级联删除关联数据。

### API

实现需求文档中的接口：

- 会议：`POST /api/meetings`、`GET /api/meetings`、`GET /api/meetings/{meeting_id}`、`DELETE /api/meetings/{meeting_id}`。
- 处理：`POST /api/meetings/{meeting_id}/process`、`POST /api/meetings/{meeting_id}/regenerate`、`GET /api/meetings/{meeting_id}/events`。
- 参会人：`GET /api/meetings/{meeting_id}/participants`、`POST /api/meetings/{meeting_id}/participants`、`PATCH /api/participants/{participant_id}`、`DELETE /api/participants/{participant_id}`。
- Speaker 映射：`GET /api/meetings/{meeting_id}/speaker-mappings`、`PATCH /api/meetings/{meeting_id}/speaker-mappings`。
- 结果：`GET /api/meetings/{meeting_id}/transcript`、`summary`、`decisions`、`risks`、`action-items`。
- 行动项：`PATCH /api/action-items/{action_item_id}`。
- 搜索：`POST /api/search`。

`POST /api/meetings` 保存上传文件并创建会议；新建页提交后自动启动处理流程。

### Provider

`ASRProvider` 抽象：

- `CustomASRProvider` 使用 `ASR_API_BASE_URL`、`ASR_API_KEY`、`ASR_MODEL`、`ASR_ENABLE_SPEAKER_DIARIZATION` 和超时配置。
- 请求使用 multipart 上传文件，并附带模型和说话人分离开关。
- 响应兼容常见结构：`segments`、`data.segments`、`result.segments`。
- 字段兼容：`start`/`start_time`、`end`/`end_time`、`speaker`/`speaker_label`、`text`/`content`。
- 说话人统一规范化为 `Speaker 1`、`Speaker 2`。
- 如果 API 未返回分段，则以全文生成一个 `Speaker 1` 片段。

`LLMProvider` 抽象：

- `OpenAICompatibleLLMProvider` 调用 `LLM_API_BASE_URL/chat/completions`。
- 支持配置 `LLM_MODEL`、`LLM_API_KEY`、`AI_REQUEST_TIMEOUT`。
- Prompt 要求返回 JSON。
- 解析失败时先从文本中提取 JSON，再使用兜底结构。

`EmbeddingProvider` 抽象：

- `OpenAICompatibleEmbeddingProvider` 调用 `EMBEDDING_API_BASE_URL/embeddings`。
- 支持配置 `EMBEDDING_MODEL`、`EMBEDDING_API_KEY`。
- 输出维度保持一致，用于 ChromaDB 建索引和查询。

`MockASRProvider`、`MockLLMProvider`、`MockEmbeddingProvider` 仅在无 Key 或显式配置 `mock` 时使用。

## 前端设计

### 页面

- `/`：会议列表页，显示标题、状态、来源类型、创建时间，支持查看和删除。
- `/meetings/new`：新建会议页，支持标题、描述、文件上传、参会人列表、说话人分离开关。提交后跳转详情并启动处理。
- `/meetings/:id`：会议详情页，展示处理状态、SSE 日志、参会人、Speaker 映射、转写、摘要、决策、风险和行动项。
- `/search`：历史会议语义搜索页，输入自然语言问题，展示来源会议、内容类型、相关说话人和匹配内容。

### 视觉风格

采用用户确认的参考风格：

- 左侧深色固定导航，包含品牌、会议入口、历史会议、待办、搜索入口。
- 主区域使用暖米色背景和浅纸感面板。
- 金色用于主操作按钮、虚线上传区、边框和重点状态。
- 列表项使用圆角边框、状态徽标和右侧操作按钮。
- 详情页保留管理台的信息密度，但避免普通白色后台模板感。

### 组件

- `ProcessingProgress`：进度条和事件日志。
- `ParticipantEditor`：参会人增删改。
- `SpeakerMappingPanel`：Speaker 标签到参会人或手动显示名的映射。
- `TranscriptTimeline`：时间轴式转写展示。
- `ActionItemTable`：行动项状态、负责人、截止时间、优先级编辑。

## 错误处理

- 第三方 API 调用均设置超时，捕获异常并记录错误。
- workflow 任一节点失败时将会议状态改为 `failed`，并写入失败事件。
- 前端显示加载、空数据和错误状态。
- 如果 ASR 不支持说话人分离，系统默认 `Speaker 1`，但仍保留 Speaker 映射能力。

## 测试与验证

首版完成后需要验证：

- 后端应用可启动，OpenAPI 可访问。
- 创建会议、上传文件、启动处理、SSE 事件可用。
- 无 Key 时 Mock 兜底流程可跑通。
- 配置自定义 API Key 和 URL 后，Provider 走真实 API 主路径。
- 前端可构建，主要页面无 TypeScript 错误。
- Speaker 映射保存后，转写和搜索结果展示名更新。

## 交付物

- 完整后端项目：FastAPI、SQLAlchemy、Provider、workflow、SSE、ChromaDB、README、`.env.example`。
- 完整前端项目：React、TypeScript、TailwindCSS、页面、组件、API client、README。
- 根目录 README 和 `docker-compose.yml`。

