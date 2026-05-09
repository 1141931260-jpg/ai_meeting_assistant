import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";

import { api } from "../api/client";

export default function NewMeetingPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [participantText, setParticipantText] = useState("");
  const [enableDiarization, setEnableDiarization] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setSubmitting(true);
    const form = new FormData();
    form.append("title", title);
    form.append("description", description);
    form.append("enable_speaker_diarization", String(enableDiarization));
    form.append("auto_process", "true");
    form.append(
      "participants",
      JSON.stringify(
        participantText
          .split(/\n|,/)
          .map((name) => name.trim())
          .filter(Boolean)
      )
    );
    form.append("file", file);
    const meeting = await api.createMeeting(form);
    navigate(`/meetings/${meeting.id}`);
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>新建会议</h1>
          <p>上传会议材料后自动启动 AI 处理流程。</p>
        </div>
      </header>

      <form className="form-panel" onSubmit={submit}>
        <label>
          会议标题
          <input value={title} onChange={(event) => setTitle(event.target.value)} required placeholder="例如：产品登录模块复盘" />
        </label>
        <label>
          会议描述
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="可选" />
        </label>
        <label>
          参会人名单
          <textarea
            value={participantText}
            onChange={(event) => setParticipantText(event.target.value)}
            placeholder="每行一个姓名，或用逗号分隔"
          />
        </label>
        <label className="checkbox-line">
          <input type="checkbox" checked={enableDiarization} onChange={(event) => setEnableDiarization(event.target.checked)} />
          启用说话人分离
        </label>
        <label className="file-drop">
          <Upload size={24} />
          <span>{file ? file.name : "选择 mp3、wav、m4a 或 txt 文件"}</span>
          <input type="file" accept=".mp3,.wav,.m4a,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <button className="gold-button wide" disabled={submitting || !file || !title}>
          {submitting ? "上传中..." : "上传并处理"}
        </button>
      </form>
    </div>
  );
}
