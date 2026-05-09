import { api } from "../api/client";
import type { ActionItem } from "../types";

export default function ActionItemTable({
  items,
  onChanged
}: {
  items: ActionItem[];
  onChanged: () => void;
}) {
  async function patch(id: string, payload: Partial<ActionItem>) {
    await api.updateActionItem(id, payload);
    onChanged();
  }

  if (items.length === 0) {
    return <div className="empty-state">暂无行动项。</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>任务</th>
            <th>负责人</th>
            <th>截止</th>
            <th>优先级</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <strong>{item.title}</strong>
                <p>{item.description || item.evidence}</p>
              </td>
              <td>
                <input defaultValue={item.owner ?? ""} onBlur={(event) => patch(item.id, { owner: event.target.value })} />
              </td>
              <td>
                <input defaultValue={item.due_date ?? ""} onBlur={(event) => patch(item.id, { due_date: event.target.value })} />
              </td>
              <td>
                <select value={item.priority} onChange={(event) => patch(item.id, { priority: event.target.value as ActionItem["priority"] })}>
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </select>
              </td>
              <td>
                <select value={item.status} onChange={(event) => patch(item.id, { status: event.target.value as ActionItem["status"] })}>
                  <option value="todo">待办</option>
                  <option value="doing">进行中</option>
                  <option value="done">完成</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
