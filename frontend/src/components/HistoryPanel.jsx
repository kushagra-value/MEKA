import React from "react";

export default function HistoryPanel({ history, onSelect }) {
  if (!history || history.length === 0) {
    return (
      <div className="history-panel">
        <h3>Query History</h3>
        <p className="history-empty">No queries yet. Try asking a question!</p>
      </div>
    );
  }

  return (
    <div className="history-panel">
      <h3>Query History</h3>
      <div className="history-list">
        {history.map((entry) => (
          <div
            key={entry.query_id}
            className="history-item"
            onClick={() => onSelect(entry.query_id)}
          >
            <div className="history-query">{entry.query}</div>
            <div className="history-meta">
              <span className={`history-status status-${entry.status}`}>
                {entry.status}
              </span>
              {entry.created_at && (
                <span className="history-date">
                  {new Date(entry.created_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
