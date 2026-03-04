import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function ResultDisplay({ result }) {
  const [showChunks, setShowChunks] = useState(false);

  if (!result) return null;

  return (
    <div className="result-display">
      {result.sub_tasks && result.sub_tasks.length > 0 && (
        <div className="result-section sub-tasks-section">
          <h3>Planned Sub-Tasks</h3>
          <div className="sub-tasks-list">
            {result.sub_tasks.map((task, i) => (
              <div key={i} className="sub-task-item">
                <span className="sub-task-badge">ST-{i + 1}</span>
                <span className="sub-task-desc">{task.description}</span>
                <span className={`sub-task-status status-${task.status}`}>
                  {task.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="result-section answer-section">
        <h3>Answer</h3>
        <div className="answer-content">
          <ReactMarkdown>{result.final_answer}</ReactMarkdown>
        </div>
      </div>

      {result.reasoning && (
        <div className="result-section reasoning-section">
          <h3>Reasoning Trace</h3>
          <div className="reasoning-content">
            <ReactMarkdown>{result.reasoning}</ReactMarkdown>
          </div>
        </div>
      )}

      {result.reranked_chunks && result.reranked_chunks.length > 0 && (
        <div className="result-section chunks-section">
          <h3
            className="clickable-header"
            onClick={() => setShowChunks(!showChunks)}
          >
            Evidence Chunks ({result.reranked_chunks.length})
            <span className="expand-icon">
              {showChunks ? "\u25B2" : "\u25BC"}
            </span>
          </h3>
          {showChunks && (
            <div className="chunks-list">
              {result.reranked_chunks.map((chunk, i) => (
                <div key={i} className="chunk-item">
                  <div className="chunk-header">
                    <span className="chunk-source">{chunk.source}</span>
                    <span className="chunk-score">
                      Score: {chunk.score?.toFixed(4)}
                    </span>
                  </div>
                  <div className="chunk-content">{chunk.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {result.sources && result.sources.length > 0 && (
        <div className="result-section sources-section">
          <h3>Sources</h3>
          <ul className="sources-list">
            {result.sources.map((src, i) => (
              <li key={i}>{src}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
