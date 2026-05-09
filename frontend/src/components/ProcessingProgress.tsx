import { useEffect, useRef, useState } from "react";

import type { Meeting, ProcessingEvent } from "../types";

export default function ProcessingProgress({ meeting, onFinished }: { meeting: Meeting; onFinished?: () => void | Promise<void> }) {
  const [events, setEvents] = useState<ProcessingEvent[]>([]);
  const notifiedRef = useRef(false);
  const onFinishedRef = useRef(onFinished);
  const latest = events.at(-1);
  const progress = latest?.progress ?? (meeting.status === "completed" ? 100 : 0);
  const isRunning = meeting.status === "pending" || meeting.status === "processing" || (events.length > 0 && progress < 100);

  useEffect(() => {
    onFinishedRef.current = onFinished;
  }, [onFinished]);

  useEffect(() => {
    setEvents([]);
    notifiedRef.current = meeting.status === "completed" || meeting.status === "failed";
  }, [meeting.id]);

  useEffect(() => {
    if (!meeting.id || meeting.status === "completed") {
      return;
    }
    const source = new EventSource(`/api/meetings/${meeting.id}/events`);
    source.addEventListener("processing", (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as ProcessingEvent;
      setEvents((current) => (current.some((item) => item.id === payload.id) ? current : [...current, payload]));
      if (!notifiedRef.current && (payload.progress >= 100 || payload.status === "failed")) {
        notifiedRef.current = true;
        window.setTimeout(() => {
          void onFinishedRef.current?.();
        }, 300);
      }
    });
    return () => source.close();
  }, [meeting.id, meeting.status]);

  return (
    <section className="panel">
      <div className="section-head">
        <h2>处理进度</h2>
        <div className="progress-summary">
          {isRunning && <span className="loading-spinner" aria-label="处理中" />}
          <strong>{progress}%</strong>
        </div>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="event-list">
        {events.length === 0 ? (
          <div className="empty-line">{meeting.status === "completed" ? "处理完成，可以进入下一步。" : "等待处理事件..."}</div>
        ) : (
          events.map((event) => (
            <div className="event-line" key={event.id}>
              <span>{event.progress}%</span>
              <p>{event.message}</p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
