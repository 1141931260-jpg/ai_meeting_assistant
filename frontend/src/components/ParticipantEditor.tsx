import { useState } from "react";
import { Plus } from "lucide-react";

import { api } from "../api/client";
import type { Participant } from "../types";

export default function ParticipantEditor({
  meetingId,
  participants,
  onChanged
}: {
  meetingId: string;
  participants: Participant[];
  onChanged: () => void;
}) {
  const [name, setName] = useState("");

  async function add() {
    if (!name.trim()) return;
    await api.addParticipant(meetingId, { name });
    setName("");
    onChanged();
  }

  return (
    <section className="panel">
      <div className="section-head">
        <h2>参会人</h2>
      </div>
      <div className="compact-list">
        {participants.map((item) => (
          <div className="mini-row" key={item.id}>
            <strong>{item.name}</strong>
            <span>{item.role || "未设置角色"}</span>
          </div>
        ))}
      </div>
      <div className="inline-form">
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="新增参会人" />
        <button className="icon-button" onClick={add} title="新增参会人">
          <Plus size={18} />
        </button>
      </div>
    </section>
  );
}
