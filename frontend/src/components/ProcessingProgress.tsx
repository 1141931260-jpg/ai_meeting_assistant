import { useEffect, useState } from "react";

import type { Meeting, ProcessingEvent } from "../types";

export default function ProcessingProgress({ meeting }: { meeting: Meeting }) {
  const [events, setEvents] = useState<ProcessingEvent[]>([]);
  const latest = events.at(-1);
  const progress = latest?.progress ?? (meeting.status === "completed" ? 100 : 0);

  useEffect(() => {
    if (!meeting.id || meeting.status === "completed") {
      return;
    }
    const source = new EventSource(`/api/meetings/${meeting.id}/events`);
    source.addEventListener("processing", (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as ProcessingEvent;
      setEvents((current) => (current.some((item) => item.id === payload.id) ? current : [...current, payload]));
    });
    return () => source.close();
  }, [meeting.id, meeting.status]);

  return (
    <section className="panel">
      <div className="section-head">
        <h2>处理进度</h2>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="event-list">
        {events.length === 0 ? (
          <div className="empty-line">等待处理事件...</div>
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
