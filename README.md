# AI 会议纪要与任务跟踪系统

一个前后端分离的 AI 会议助手，支持上传会议音频或文本，调用自定义 ASR / LLM / Embedding API 完成转写、摘要、决策、风险、行动项提取和历史会议语义检索。

## 项目亮点

- 设计 `ASRProvider` / `LLMProvider` / `EmbeddingProvider` 三层抽象，分别接入第三方语音识别 API、大模型 API 和 Embedding API。
- 支持会议音频时间戳转写和说话人分离，将多人会议内容按 Speaker 维度结构化展示。
- 设计 Speaker 与参会人映射机制，支持将 `Speaker 1`、`Speaker 2` 手动映射为真实参会人姓名。
- 使用工作流服务编排转写、说话人处理、摘要、决策提取、风险识别、行动项生成和向量索引。
- 设计 Action Item 抽取模块，结合说话人信息自动识别任务内容、负责人、截止时间和优先级。
- 基于 ChromaDB 构建会议内容向量索引，支持历史会议语义检索，并返回会议来源和相关说话人。
- 使用 FastAPI SSE 实现长耗时 AI 任务进度实时推送。
- React + TypeScript 实现会议管理、Speaker 映射、任务跟踪和语义搜索页面。
- 默认可 Mock 兜底；配置 ASR / LLM / Embedding 三类 API Key 后走真实第三方服务主路径。

## 技术栈

后端：FastAPI、SQLAlchemy、SQLite、Pydantic、ChromaDB、LangGraph、LangChain、SSE。

前端：React 19、TypeScript、Vite、TailwindCSS、React Router、EventSource。

## 目录结构

```txt
backend/   FastAPI 后端
frontend/  React 前端
docs/      设计文档
```

## 本地运行

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问：`http://localhost:5173`

## 第三方 API 配置

复制 `backend/.env.example` 为 `backend/.env`，填写：

```env
ASR_PROVIDER=custom
ASR_API_KEY=your_asr_api_key
ASR_API_BASE_URL=https://your-asr-provider.example.com/transcribe
ASR_MODEL=your-asr-model

LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_llm_api_key
LLM_API_BASE_URL=https://your-llm-provider.example.com/v1
LLM_MODEL=your-chat-model

EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_API_BASE_URL=https://your-embedding-provider.example.com/v1
EMBEDDING_MODEL=your-embedding-model
```

说话人分离依赖第三方 ASR 服务能力。如果 API 不支持说话人分离，系统会默认使用 `Speaker 1`，但仍保留 Speaker 映射 UI 和数据结构。

## Docker Compose

```bash
docker compose up --build
```

前端：`http://localhost:5173`

后端：`http://localhost:8000/docs`
