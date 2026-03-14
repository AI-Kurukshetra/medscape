"use client";

import { useEffect, useMemo, useState } from "react";
import { getProgress } from "@/lib/api";
import type { ProgressItem } from "@/lib/types";

export default function ProgressPage() {
  const [rows, setRows] = useState<ProgressItem[]>([]);
  const [query, setQuery] = useState("");
  const [minCompletion, setMinCompletion] = useState(0);

  useEffect(() => {
    getProgress().then(setRows).catch(() => setRows([]));
  }, []);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((item) => {
      const matchesQuery =
        !q || item.user_id.toLowerCase().includes(q) || item.module_code.toLowerCase().includes(q);
      const matchesCompletion = Number(item.completion_rate) >= minCompletion;
      return matchesQuery && matchesCompletion;
    });
  }, [rows, query, minCompletion]);

  return (
    <section className="card">
      <h2>User Progress Tracking</h2>
      <div className="controls">
        <input
          className="input"
          placeholder="Search by user/module..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="range-control">
          Min Completion: <b>{minCompletion}%</b>
          <input
            type="range"
            min={0}
            max={100}
            value={minCompletion}
            onChange={(e) => setMinCompletion(Number(e.target.value))}
          />
        </label>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Module</th>
              <th>Completion</th>
              <th>Score</th>
              <th>Time (min)</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((item) => (
              <tr key={`${item.user_id}-${item.module_code}`}>
                <td>{item.user_id}</td>
                <td>{item.module_code}</td>
                <td>{item.completion_rate}%</td>
                <td>{item.assessment_score}</td>
                <td>{item.time_spent_minutes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
