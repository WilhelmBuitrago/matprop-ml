// frontend/src/app/configuration/history.tsx
// History view component for configuration changes

import { useState, useEffect } from "react";
import { fetchConfigHistory } from "./api";

interface AuditEntry {
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  changes: Record<string, any>;
  validation_result: Record<string, any>;
  id: string;
}

export default function HistoryView() {
  const [history, setHistory] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const historyData = await fetchConfigHistory();
        setHistory(historyData);
      } catch (err) {
        setError(err.message || "Failed to fetch history");
        console.error("Error fetching history:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (loading) {
    return <div>Loading history...</div>;
  }

  if (error) {
    return <div>Error loading history: {error}</div>;
  }

  return (
    <div className="history-view">
      <h2>Configuration Change History</h2>
      {history.length === 0 ? (
        <p>No history entries found.</p>
      ) : (
        <div className="history-list">
          {history.map((entry) => (
            <div key={entry.id} className="history-entry">
              <div className="entry-header">
                <span className="timestamp">{new Date(entry.timestamp).toLocaleString()}</span>
                <span className="user">User: {entry.user}</span>
              </div>
              <div className="changes">
                <h4>Changes:</h4>
                {Object.entries(entry.changes).map(([key, change]) => (
                  <div key={key} className="change-item">
                    <span className="change-key">{key}:</span>
                    <span className="change-values">
                      {change.old} → {change.new}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      
      <style jsx>{`
        .history-view {
          padding: 20px;
        }
        
        .history-list {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }
        
        .history-entry {
          background: rgba(30, 30, 40, 0.7);
          border: 1px solid rgba(160, 140, 255, 0.32);
          border-radius: 8px;
          padding: 15px;
        }
        
        .entry-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 10px;
          padding-bottom: 10px;
          border-bottom: 1px solid rgba(160, 140, 255, 0.2);
        }
        
        .timestamp, .user {
          font-size: 0.9rem;
          color: #a08cff;
        }
        
        .changes {
          margin-top: 10px;
        }
        
        .change-item {
          display: flex;
          gap: 10px;
          margin-bottom: 5px;
        }
        
        .change-key {
          font-weight: bold;
          color: #a08cff;
        }
        
        .change-values {
          color: #f4f4f4;
        }
      `}</style>
    </div>
  );
}