import React, { useState, useEffect, useCallback } from "react";
import QueryInput from "./components/QueryInput";
import AgentTrace from "./components/AgentTrace";
import ResultDisplay from "./components/ResultDisplay";
import HistoryPanel from "./components/HistoryPanel";
import { submitQuery, getUserHistory, getQueryStatus } from "./api/client";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const refreshHistory = useCallback(async () => {
    try {
      const data = await getUserHistory();
      setHistory(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const handleSubmit = async (query, webSearchEnabled) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await submitQuery(query, webSearchEnabled);
      setResult(data);
      refreshHistory();
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = async (queryId) => {
    try {
      setLoading(true);
      const data = await getQueryStatus(queryId);
      setResult(data);
      setShowHistory(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <h1>MEKA</h1>
            <span className="subtitle">
              Multi-Agent Expert Knowledge Assistant
            </span>
          </div>
          <div className="header-actions">
            <span className="domain-badge">
              Security &amp; Compliance
            </span>
            <button
              className="history-toggle"
              onClick={() => setShowHistory(!showHistory)}
            >
              {showHistory ? "Hide History" : "History"}
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className={`content-area ${showHistory ? "with-sidebar" : ""}`}>
          <div className="main-panel">
            <QueryInput onSubmit={handleSubmit} loading={loading} />

            {error && (
              <div className="error-banner">
                <strong>Error:</strong> {error}
              </div>
            )}

            {loading && (
              <div className="processing-indicator">
                <div className="processing-animation">
                  <div className="pulse-ring" />
                  <div className="pulse-ring delay-1" />
                  <div className="pulse-ring delay-2" />
                </div>
                <p>Agents are analyzing your query...</p>
                <p className="processing-sub">
                  Planning sub-tasks, retrieving evidence, reranking, validating,
                  and summarizing.
                </p>
              </div>
            )}

            {result && !loading && (
              <>
                <AgentTrace trace={result.agent_trace} />
                <ResultDisplay result={result} />
              </>
            )}
          </div>

          {showHistory && (
            <aside className="sidebar">
              <HistoryPanel
                history={history}
                onSelect={handleHistorySelect}
              />
            </aside>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>
          MEKA v1.0 — Powered by LangGraph, ChromaDB, and cross-encoder
          reranking
        </p>
      </footer>
    </div>
  );
}
