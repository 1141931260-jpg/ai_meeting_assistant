import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { api } from "../api/client";
import type { Meeting } from "../types";

export default function MeetingListPage() {
  const [meetings, setMeetings] = useState<Meeting[] | null>(null);

  useEffect(() => {
    api.listMeetings().then(setMeetings).catch(() => setMeetings([]));
  }, []);

  if (!meetings) {
    return <div className="empty-state">加载会议...</div>;
  }

  if (meetings.length === 0) {
    return <Navigate to="/meetings/new" replace />;
  }

  return <Navigate to={`/meetings/${meetings[0].id}`} replace />;
}
