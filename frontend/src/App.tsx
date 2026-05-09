import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Clock3, FilePlus2, ListChecks, Search, Sparkles } from "lucide-react";

import { api } from "./api/client";
import MeetingDetailPage from "./pages/MeetingDetailPage";
import MeetingListPage from "./pages/MeetingListPage";
import NewMeetingPage from "./pages/NewMeetingPage";
import SearchPage from "./pages/SearchPage";
import type { Meeting } from "./types";

function App() {
  const location = useLocation();
  const [meetings, setMeetings] = useState<Meeting[]>([]);

  useEffect(() => {
    api.listMeetings().then(setMeetings).catch(() => setMeetings([]));
  }, [location.pathname]);

  const meetingListActive = location.pathname === "/" || (location.pathname.startsWith("/meetings/") && location.pathname !== "/meetings/new");

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
          <div className={`nav-item nav-item-static ${meetingListActive ? "active" : ""}`}>
            <ListChecks size={18} /> 会议列表
          </div>
          <div className="sidebar-meeting-list">
            {meetings.length === 0 ? (
              <div className="sidebar-empty">暂无会议</div>
            ) : (
              meetings.map((meeting) => (
                <NavLink className="sidebar-meeting-item" to={`/meetings/${meeting.id}`} key={meeting.id}>
                  <strong>{meeting.title || "未命名会议"}</strong>
                  <span>{new Date(meeting.created_at).toLocaleString()}</span>
                </NavLink>
              ))
            )}
          </div>
          <NavLink className="nav-item" to="/meetings/new">
            <FilePlus2 size={18} /> 新建会议
          </NavLink>
          <NavLink className="nav-item" to="/search">
            <Search size={18} /> 历史搜索
          </NavLink>
        </nav>
        <div className="sidebar-card api-card">
          <div className="sidebar-card-head">
            <Sparkles size={18} />
            <strong>API 接入</strong>
          </div>
          <div className="api-chip-grid">
            <span>ASR</span>
            <span>LLM</span>
            <span>Embedding</span>
          </div>
          <p>自定义 Provider</p>
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
