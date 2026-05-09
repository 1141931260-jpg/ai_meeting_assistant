# 后端运行说明

## 启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

macOS / Linux 激活虚拟环境使用：

```bash
source .venv/bin/activate
```

OpenAPI 文档：`http://localhost:8000/docs`

## 自定义 API 配置

项目按三类 Provider 解耦：

- ASR：`ASR_PROVIDER=custom`，向 `ASR_API_BASE_URL` 发起文件上传请求，负责转写、时间戳和说话人分离。
- LLM：`LLM_PROVIDER=openai_compatible`，调用 `{LLM_API_BASE_URL}/chat/completions`，负责摘要、决策、风险和行动项。
- Embedding：`EMBEDDING_PROVIDER=openai_compatible`，调用 `{EMBEDDING_API_BASE_URL}/embeddings`，负责 ChromaDB 语义索引。

ASR 响应会兼容常见字段：

- 分段列表：`segments`、`data.segments`、`result.segments`
- 时间字段：`start` / `start_time`，`end` / `end_time`
- 说话人：`speaker` / `speaker_label`
- 文本：`text` / `content`

如果没有配置对应 Key 或 Base URL，Provider 会回退到 Mock，保证本地流程可演示。
