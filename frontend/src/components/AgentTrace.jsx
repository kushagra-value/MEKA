import React, { useState } from "react";

const AGENT_ICONS = {
  Orchestrator: "\u{1F9E0}",
  Retriever: "\u{1F50D}",
  Reranker: "\u{1F4CA}",
  Validator: "\u2705",
  Summarizer: "\u{1F4DD}",
};

const AGENT_COLORS = {
  Orchestrator: "#6366f1",
  Retriever: "#0ea5e9",
  Reranker: "#f59e0b",
  Validator: "#10b981",
  Summarizer: "#8b5cf6",
};

export default function AgentTrace({ trace }) {
  const [expandedIdx, setExpandedIdx] = useState(null);

  if (!trace || trace.length === 0) return null;

  return (
    <div className="agent-trace">
      <h3>Agent Execution Trace</h3>
      <div className="trace-timeline">
        {trace.map((step, i) => (
          <div
            key={i}
            className="trace-step"
            style={{ borderLeftColor: AGENT_COLORS[step.agent] || "#666" }}
            onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
          >
            <div className="trace-step-header">
              <span className="agent-icon">
                {AGENT_ICONS[step.agent] || "\u2699\uFE0F"}
              </span>
              <span
                className="agent-name"
                style={{ color: AGENT_COLORS[step.agent] || "#666" }}
              >
                {step.agent}
              </span>
              <span className="agent-action">{step.action}</span>
              <span className="expand-icon">
                {expandedIdx === i ? "\u25B2" : "\u25BC"}
              </span>
            </div>
            <div className="trace-step-summary">{step.output_summary}</div>
            {expandedIdx === i && step.details && (
              <div className="trace-step-details">
                <pre>{JSON.stringify(step.details, null, 2)}</pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
