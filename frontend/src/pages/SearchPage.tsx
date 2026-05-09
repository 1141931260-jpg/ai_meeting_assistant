import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";

import { api } from "../api/client";
import type { SearchResult } from "../types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setResults(await api.search(query));
    setLoading(false);
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>历史搜索</h1>
          <p>用自然语言检索会议转写、摘要、决策、风险和行动项。</p>
        </div>
      </header>
      <form className="search-box" onSubmit={submit}>
        <Search size={22} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：哪些任务还没有完成？" />
        <button className="gold-button">搜索</button>
      </form>
      <section className="panel">
        {loading ? (
          <div className="empty-state">检索中...</div>
        ) : results.length === 0 ? (
          <div className="empty-state">输入问题后查看匹配内容。</div>
        ) : (
          results.map((item) => (
            <article className="list-card search-result" key={`${item.meeting_id}-${item.content}`}>
              <div>
                <h3>{item.content}</h3>
                <p>
                  {item.content_type} · {item.participant_name || item.speaker || "无说话人"} · 相似度 {item.score.toFixed(2)}
                </p>
                {item.evidence && <p>{item.evidence}</p>}
              </div>
              <Link className="gold-button small" to={`/meetings/${item.meeting_id}`}>
                {item.meeting_title}
              </Link>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
