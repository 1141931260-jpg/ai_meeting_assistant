import type {
  ActionItem,
  Decision,
  Meeting,
  MeetingSummary,
  Participant,
  Risk,
  SearchResult,
  SpeakerMapping,
  TranscriptSegment
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listMeetings: () => request<Meeting[]>("/api/meetings"),
  getMeeting: (id: string) => request<Meeting & { participants: Participant[] }>(`/api/meetings/${id}`),
  deleteMeeting: (id: string) => request<{ ok: boolean }>(`/api/meetings/${id}`, { method: "DELETE" }),
  createMeeting: (form: FormData) => request<Meeting>("/api/meetings", { method: "POST", body: form }),
  regenerate: (id: string) => request<Meeting>(`/api/meetings/${id}/regenerate`, { method: "POST" }),
  getParticipants: (id: string) => request<Participant[]>(`/api/meetings/${id}/participants`),
  addParticipant: (id: string, payload: Partial<Participant>) =>
    request<Participant>(`/api/meetings/${id}/participants`, { method: "POST", body: JSON.stringify(payload) }),
  getMappings: (id: string) => request<SpeakerMapping[]>(`/api/meetings/${id}/speaker-mappings`),
  updateMappings: (id: string, mappings: Partial<SpeakerMapping>[]) =>
    request<SpeakerMapping[]>(`/api/meetings/${id}/speaker-mappings`, {
      method: "PATCH",
      body: JSON.stringify({ mappings })
    }),
  getTranscript: (id: string) => request<TranscriptSegment[]>(`/api/meetings/${id}/transcript`),
  getSummary: (id: string) => request<MeetingSummary | null>(`/api/meetings/${id}/summary`),
  getDecisions: (id: string) => request<Decision[]>(`/api/meetings/${id}/decisions`),
  getRisks: (id: string) => request<Risk[]>(`/api/meetings/${id}/risks`),
  getActionItems: (id: string) => request<ActionItem[]>(`/api/meetings/${id}/action-items`),
  updateActionItem: (id: string, payload: Partial<ActionItem>) =>
    request<ActionItem>(`/api/action-items/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  search: (query: string, top_k = 5) =>
    request<SearchResult[]>("/api/search", { method: "POST", body: JSON.stringify({ query, top_k }) })
};
