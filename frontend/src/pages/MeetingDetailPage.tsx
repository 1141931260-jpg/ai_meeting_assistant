import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, RefreshCw, Send } from "lucide-react";

import { api } from "../api/client";
import ParticipantEditor from "../components/ParticipantEditor";
import ProcessingProgress from "../components/ProcessingProgress";
import SpeakerMappingPanel from "../components/SpeakerMappingPanel";
import StatusBadge from "../components/StatusBadge";
import TranscriptTimeline from "../components/TranscriptTimeline";
import type {
  ChatMessage,
  Meeting,
  MeetingSummary,
  Participant,
  TranscriptSegment
} from "../types";

type Tab = "transcript" | "summary";

export default function MeetingDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [meeting, setMeeting] = useState<(Meeting & { participants: Participant[] }) | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [summary, setSummary] = useState<MeetingSummary | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [transcriptCollapsed, setTranscriptCollapsed] = useState(false);
  const [tab, setTab] = useState<Tab>("transcript");
  const isProcessingFlow = searchParams.get("processing") === "1";

  async function load() {
    const [meetingData, transcriptData, summaryData] = await Promise.all([
      api.getMeeting(id),
      api.getTranscript(id),
      api.getSummary(id)
    ]);
    setMeeting(meetingData);
    setTranscript(transcriptData);
    setSummary(summaryData);
  }

  useEffect(() => {
    setMessages([]);
    setQuestion("");
    load();
  }, [id]);

  const transcriptText = useMemo(() => {
    return transcript
      .map((segment) => `[${Math.round(segment.start_time)}-${Math.round(segment.end_time)}] ${segment.display_speaker}: ${segment.content}`)
      .join("\n");
  }, [transcript]);

  async function regenerate() {
    await api.regenerate(id);
    setTimeout(load, 1200);
  }

  async function ask(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || sending) return;
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setQuestion("");
    setSending(true);
    try {
      const response = await api.chatWithMeeting(id, trimmed, messages);
      setMessages([...nextMessages, { role: "assistant", content: response.answer }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "问答请求失败";
      setMessages([...nextMessages, { role: "assistant", content: message }]);
    } finally {
      setSending(false);
    }
  }

  if (!meeting) {
    return <div className="empty-state">加载会议详情...</div>;
  }

  const isCompleted = meeting.status === "completed";
  const showProcessingPage = isProcessingFlow;

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>{meeting.title || "正在生成会议标题"}</h1>
          <p>{meeting.description || meeting.original_filename}</p>
        </div>
        <div className="header-actions">
          <StatusBadge status={meeting.status} />
          {showProcessingPage && isCompleted ? (
            <button className="gold-button" onClick={() => navigate(`/meetings/${meeting.id}`)}>
              下一步
            </button>
          ) : (
            <button className="gold-button" onClick={regenerate}>
              <RefreshCw size={16} /> 重新生成
            </button>
          )}
        </div>
      </header>

      {meeting.error_message && <div className="error-box">{meeting.error_message}</div>}

      {showProcessingPage ? (
        <div className="detail-layout">
          <aside className="detail-side">
            <ProcessingProgress meeting={meeting} onFinished={load} />
            <ParticipantEditor meetingId={meeting.id} participants={meeting.participants} onChanged={load} />
            <SpeakerMappingPanel meetingId={meeting.id} participants={meeting.participants} transcript={transcript} onSaved={load} />
          </aside>
          <MeetingResultPanel tab={tab} setTab={setTab} transcript={transcript} summary={summary} />
        </div>
      ) : (
      <section className={`meeting-workbench ${transcriptCollapsed ? "transcript-is-collapsed" : ""}`}>
        <section className="chat-panel panel">
          <div className="section-head compact">
            <div>
              <h2>本会议问答</h2>
              <p className="hint">回答只基于当前会议资料。</p>
            </div>
          </div>
          <div className="chat-history">
            {messages.length === 0 ? (
              <div className="empty-state">可以直接问：“这次会议确定了哪些行动项？”或“谁负责接口文档？”</div>
            ) : (
              messages.map((message, index) => (
                <div className={`chat-bubble ${message.role}`} key={`${message.role}-${index}`}>
                  {message.content}
                </div>
              ))
            )}
            {sending && <div className="chat-bubble assistant">正在根据当前会议内容回答...</div>}
          </div>
          <form className="chat-input" onSubmit={ask}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="问当前会议里的问题..."
              rows={2}
            />
            <button className="gold-button" disabled={sending || !question.trim()} type="submit">
              <Send size={16} /> 发送
            </button>
          </form>
        </section>

        <aside className="transcript-panel panel">
          <div className="section-head compact">
            <div>
              <h2>完整文字</h2>
              <p className="hint">{transcript.length} 段转写</p>
            </div>
            <button className="icon-button" onClick={() => setTranscriptCollapsed(true)} title="折叠完整文字">
              <ChevronRight size={18} />
            </button>
          </div>
          <pre className="transcript-full-text">{transcriptText || "暂无转写内容。"}</pre>
        </aside>

        <button className="transcript-restore" onClick={() => setTranscriptCollapsed(false)} title="展开完整文字">
          <ChevronLeft size={18} />
          <span>全文</span>
        </button>
      </section>
      )}
    </div>
  );
}

function MeetingResultPanel({
  tab,
  setTab,
  transcript,
  summary
}: {
  tab: Tab;
  setTab: (tab: Tab) => void;
  transcript: TranscriptSegment[];
  summary: MeetingSummary | null;
}) {
  return (
    <section className="panel result-panel">
      <div className="tabs">
        {[
          ["transcript", "音频内容"],
          ["summary", "摘要"]
        ].map(([key, label]) => (
          <button className={tab === key ? "active" : ""} onClick={() => setTab(key as Tab)} key={key}>
            {label}
          </button>
        ))}
      </div>
      {tab === "transcript" && <TranscriptTimeline segments={transcript} />}
      {tab === "summary" && (
        <div className="prose-box">
          {summary ? (
            <>
              <h2>会议总览</h2>
              <p>{summary.overview}</p>
              <h2>关键点</h2>
              <ul>{summary.key_points.map((point) => <li key={point}>{point}</li>)}</ul>
              <h2>结论</h2>
              <p>{summary.conclusion}</p>
            </>
          ) : (
            <div className="empty-state">暂无摘要。</div>
          )}
        </div>
      )}
    </section>
  );
}
