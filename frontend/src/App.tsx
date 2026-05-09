import { NavLink, Route, Routes } from "react-router-dom";
import { Clock3, FilePlus2, ListChecks, Search, Sparkles } from "lucide-react";

import MeetingDetailPage from "./pages/MeetingDetailPage";
import MeetingListPage from "./pages/MeetingListPage";
import NewMeetingPage from "./pages/NewMeetingPage";
import SearchPage from "./pages/SearchPage";

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">会</div>
          <div>
            <div className="brand-title">会议助手</div>
            <div className="brand-subtitle">纪要、任务、检索</div>
          </div>
        </div>
        <nav className="nav-group">
          <div className="nav-label">工作台</div>
          <NavLink className="nav-item" to="/" end>
            <ListChecks size={18} /> 会议列表
          </NavLink>
          <NavLink className="nav-item" to="/meetings/new">
            <FilePlus2 size={18} /> 新建会议
          </NavLink>
          <NavLink className="nav-item" to="/search">
            <Search size={18} /> 历史搜索
          </NavLink>
        </nav>
        <div className="sidebar-card">
          <Sparkles size={18} />
          <strong>自定义 API</strong>
          <span>ASR / LLM / Embedding 三类 Provider 解耦接入。</span>
        </div>
        <div className="sidebar-card muted-card">
          <Clock3 size={18} />
          <strong>SSE 进度</strong>
          <span>长耗时 AI 流程实时回传。</span>
        </div>
      </aside>
      <main className="main-stage">
        <Routes>
          <Route path="/" element={<MeetingListPage />} />
          <Route path="/meetings/new" element={<NewMeetingPage />} />
          <Route path="/meetings/:id" element={<MeetingDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
