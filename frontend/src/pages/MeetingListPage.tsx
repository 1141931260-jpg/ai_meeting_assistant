import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Trash2 } from "lucide-react";

import { api } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import type { Meeting } from "../types";

export default function MeetingListPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setMeetings(await api.listMeetings());
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function remove(id: string) {
    await api.deleteMeeting(id);
    load();
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>会议列表</h1>
          <p>管理会议文件、AI 处理结果和待办跟踪。</p>
        </div>
        <Link className="gold-button" to="/meetings/new">
          新建会议
        </Link>
      </header>

      <section className="upload-hero">
        <h2>AI 会议知识工作台</h2>
        <p>上传音频或文本后，系统会调用自定义 ASR、LLM 和 Embedding API 生成纪要、决策、风险和行动项。</p>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>最近会议</h2>
        </div>
        {loading ? (
          <div className="empty-state">加载中...</div>
        ) : meetings.length === 0 ? (
          <div className="empty-state">还没有会议，先创建一场吧。</div>
        ) : (
          meetings.map((meeting) => (
            <article className="list-card" key={meeting.id}>
              <div>
                <h3>{meeting.title}</h3>
                <p>
                  {meeting.source_type} · {new Date(meeting.created_at).toLocaleString()}
                </p>
              </div>
              <StatusBadge status={meeting.status} />
              <div className="row-actions">
                <Link className="icon-button" to={`/meetings/${meeting.id}`} title="查看">
                  <ArrowRight size={18} />
                </Link>
                <button className="icon-button danger" onClick={() => remove(meeting.id)} title="删除">
                  <Trash2 size={18} />
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
