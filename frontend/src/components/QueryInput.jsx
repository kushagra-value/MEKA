import React, { useState } from "react";

const EXAMPLE_QUERIES = [
  "Summarize all security incidents related to OAuth token leakage and suggest mitigations",
  "Compare GDPR Article 32 compliance evidence across our policies and past breach incidents",
  "List all incidents caused by Kubernetes misconfiguration and provide preventive action items",
];

export default function QueryInput({ onSubmit, loading }) {
  const [query, setQuery] = useState("");
  const [webSearch, setWebSearch] = useState(true);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSubmit(query.trim(), webSearch);
    }
  };

  return (
    <div className="query-input-container">
      <form onSubmit={handleSubmit}>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a complex question about security incidents, compliance policies, or vulnerabilities..."
          rows={3}
          disabled={loading}
        />
        <div className="query-controls">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={webSearch}
              onChange={(e) => setWebSearch(e.target.checked)}
              disabled={loading}
            />
            <span className="toggle-slider" />
            Web search supplement
          </label>
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? (
              <>
                <span className="spinner" />
                Processing...
              </>
            ) : (
              "Analyze"
            )}
          </button>
        </div>
      </form>

      <div className="example-queries">
        <span className="example-label">Try an example:</span>
        {EXAMPLE_QUERIES.map((eq, i) => (
          <button
            key={i}
            className="example-btn"
            onClick={() => setQuery(eq)}
            disabled={loading}
          >
            {eq.length > 70 ? eq.slice(0, 70) + "..." : eq}
          </button>
        ))}
      </div>
    </div>
  );
}
