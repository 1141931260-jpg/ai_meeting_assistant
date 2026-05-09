import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";

import { api } from "../api/client";
import ActionItemTable from "../components/ActionItemTable";
import ParticipantEditor from "../components/ParticipantEditor";
import ProcessingProgress from "../components/ProcessingProgress";
import SpeakerMappingPanel from "../components/SpeakerMappingPanel";
import StatusBadge from "../components/StatusBadge";
import TranscriptTimeline from "../components/TranscriptTimeline";
import type { ActionItem, Decision, Meeting, MeetingSummary, Participant, Risk, TranscriptSegment } from "../types";

type Tab = "transcript" | "summary" | "decisions" | "risks" | "actions";

export default function MeetingDetailPage() {
  const { id = "" } = useParams();
  const [meeting, setMeeting] = useState<(Meeting & { participants: Participant[] }) | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [summary, setSummary] = useState<MeetingSummary | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [tab, setTab] = useState<Tab>("transcript");

  async function load() {
    const [meetingData, transcriptData, summaryData, decisionsData, risksData, actionsData] = await Promise.all([
      api.getMeeting(id),
      api.getTranscript(id),
      api.getSummary(id),
      api.getDecisions(id),
      api.getRisks(id),
      api.getActionItems(id)
    ]);
    setMeeting(meetingData);
    setTranscript(transcriptData);
    setSummary(summaryData);
    setDecisions(decisionsData);
    setRisks(risksData);
    setActions(actionsData);
  }

  useEffect(() => {
    load();
  }, [id]);

  async function regenerate() {
    await api.regenerate(id);
    setTimeout(load, 1200);
  }

  if (!meeting) {
    return <div className="empty-state">加载会议详情...</div>;
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>{meeting.title}</h1>
          <p>{meeting.description || meeting.original_filename}</p>
        </div>
        <div className="header-actions">
          <StatusBadge status={meeting.status} />
          <button className="gold-button" onClick={regenerate}>
            <RefreshCw size={16} /> 重新生成
          </button>
        </div>
      </header>

      {meeting.error_message && <div className="error-box">{meeting.error_message}</div>}

      <div className="detail-layout">
        <aside className="detail-side">
          <ProcessingProgress meeting={meeting} />
          <ParticipantEditor meetingId={meeting.id} participants={meeting.participants} onChanged={load} />
          <SpeakerMappingPanel meetingId={meeting.id} participants={meeting.participants} transcript={transcript} onSaved={load} />
        </aside>
        <section className="panel result-panel">
          <div className="tabs">
            {[
              ["transcript", "转写"],
              ["summary", "摘要"],
              ["decisions", "决策"],
              ["risks", "风险"],
              ["actions", "行动项"]
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
          {tab === "decisions" && <ResultList rows={decisions.map((item) => ({ title: item.content, meta: item.evidence }))} />}
          {tab === "risks" && <ResultList rows={risks.map((item) => ({ title: `${item.risk_type} · ${item.level}`, meta: item.description }))} />}
          {tab === "actions" && <ActionItemTable items={actions} onChanged={load} />}
        </section>
      </div>
    </div>
  );
}

function ResultList({ rows }: { rows: { title: string; meta?: string | null }[] }) {
  if (rows.length === 0) return <div className="empty-state">暂无结果。</div>;
  return (
    <div className="result-list">
      {rows.map((row) => (
        <article className="list-card" key={row.title}>
          <div>
            <h3>{row.title}</h3>
            <p>{row.meta}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
