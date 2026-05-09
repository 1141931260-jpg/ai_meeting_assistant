export type Meeting = {
  id: string;
  title: string;
  description?: string | null;
  source_type: "audio" | "text";
  status: "pending" | "processing" | "completed" | "failed" | string;
  enable_speaker_diarization: boolean;
  original_filename: string;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type Participant = {
  id: string;
  meeting_id: string;
  name: string;
  role?: string | null;
  email?: string | null;
  created_at: string;
  updated_at: string;
};

export type SpeakerMapping = {
  id: string;
  meeting_id: string;
  speaker_label: string;
  participant_id?: string | null;
  display_name?: string | null;
};

export type TranscriptSegment = {
  id: string;
  meeting_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  speaker: string;
  participant_id?: string | null;
  display_speaker: string;
  content: string;
  created_at: string;
};

export type MeetingSummary = {
  id: string;
  meeting_id: string;
  overview: string;
  key_points: string[];
  conclusion: string;
  speaker_summary?: Record<string, string> | null;
};

export type Decision = {
  id: string;
  content: string;
  owner?: string | null;
  reason?: string | null;
  evidence?: string | null;
  speaker?: string | null;
};

export type Risk = {
  id: string;
  risk_type: string;
  description: string;
  level: "low" | "medium" | "high";
  owner?: string | null;
  speaker?: string | null;
  evidence?: string | null;
  suggestion?: string | null;
};

export type ActionItem = {
  id: string;
  meeting_id: string;
  title: string;
  description?: string | null;
  owner?: string | null;
  owner_participant_id?: string | null;
  due_date?: string | null;
  priority: "low" | "medium" | "high";
  status: "todo" | "doing" | "done";
  evidence?: string | null;
  source_speaker?: string | null;
};

export type ProcessingEvent = {
  id: string;
  meeting_id: string;
  step: string;
  status: "started" | "running" | "completed" | "failed";
  message: string;
  progress: number;
  created_at: string;
};

export type SearchResult = {
  meeting_id: string;
  meeting_title: string;
  content_type: string;
  speaker?: string | null;
  participant_name?: string | null;
  content: string;
  score: number;
  evidence?: string | null;
};
