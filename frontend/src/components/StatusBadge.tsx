import type { Meeting } from "../types";

const labels: Record<string, string> = {
  pending: "待处理",
  processing: "处理中",
  completed: "已完成",
  failed: "失败"
};

export default function StatusBadge({ status }: { status: Meeting["status"] }) {
  return <span className={`status-badge status-${status}`}>{labels[status] ?? status}</span>;
}
