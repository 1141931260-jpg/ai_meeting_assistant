# 前端运行说明

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认访问：`http://localhost:5173`

Vite 开发服务器已配置 `/api` 代理到 `http://localhost:8000`。如需指定后端地址，可以创建 `.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 页面

- `/`：会议列表
- `/meetings/new`：新建会议
- `/meetings/:id`：会议详情、进度、Speaker 映射、转写和行动项
- `/search`：历史会议语义搜索
