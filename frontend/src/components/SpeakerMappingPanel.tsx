import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { Participant, SpeakerMapping, TranscriptSegment } from "../types";

type Draft = Record<string, { participant_id?: string; display_name?: string }>;

export default function SpeakerMappingPanel({
  meetingId,
  participants,
  transcript,
  onSaved
}: {
  meetingId: string;
  participants: Participant[];
  transcript: TranscriptSegment[];
  onSaved: () => void;
}) {
  const [mappings, setMappings] = useState<SpeakerMapping[]>([]);
  const [draft, setDraft] = useState<Draft>({});
  const labels = useMemo(() => [...new Set(transcript.map((item) => item.speaker))], [transcript]);

  useEffect(() => {
    api.getMappings(meetingId).then((items) => {
      setMappings(items);
      const next: Draft = {};
      for (const item of items) {
        next[item.speaker_label] = {
          participant_id: item.participant_id ?? "",
          display_name: item.display_name ?? ""
        };
      }
      setDraft(next);
    });
  }, [meetingId]);

  async function save() {
    const payload = labels.map((label) => ({
      speaker_label: label,
      participant_id: draft[label]?.participant_id || null,
      display_name: draft[label]?.display_name || null
    }));
    await api.updateMappings(meetingId, payload);
    onSaved();
  }

  return (
    <section className="panel">
      <div className="section-head">
        <h2>Speaker 映射</h2>
        <button className="gold-button small" onClick={save}>
          保存
        </button>
      </div>
      {labels.length === 0 ? (
        <div className="empty-line">处理完成后会显示说话人标签。</div>
      ) : (
        labels.map((label) => (
          <div className="mapping-row" key={label}>
            <strong>{label}</strong>
            <select
              value={draft[label]?.participant_id ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  [label]: { ...current[label], participant_id: event.target.value, display_name: "" }
                }))
              }
            >
              <option value="">选择参会人</option>
              {participants.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <input
              value={draft[label]?.display_name ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  [label]: { ...current[label], display_name: event.target.value }
                }))
              }
              placeholder="或手动显示名"
            />
          </div>
        ))
      )}
      {mappings.length > 0 && <p className="hint">保存后转写展示会立即更新，可再点击重新生成。</p>}
    </section>
  );
}
