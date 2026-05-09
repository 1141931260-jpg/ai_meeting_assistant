import type { TranscriptSegment } from "../types";

export default function TranscriptTimeline({ segments }: { segments: TranscriptSegment[] }) {
  if (segments.length === 0) {
    return <div className="empty-state">暂无转写内容。</div>;
  }
  return (
    <div className="timeline">
      {segments.map((segment) => (
        <article className="timeline-item" key={segment.id}>
          <time>
            {Math.round(segment.start_time)}s - {Math.round(segment.end_time)}s
          </time>
          <span className="speaker-badge">{segment.display_speaker}</span>
          <p>{segment.content}</p>
        </article>
      ))}
    </div>
  );
}
