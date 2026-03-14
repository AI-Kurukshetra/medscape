"use client";

import { useEffect, useMemo, useState } from "react";
import { getProgress } from "@/lib/api";
import type { ProgressItem } from "@/lib/types";

const PASS_MARK = 70;

export default function AssessmentsPage() {
  const [rows, setRows] = useState<ProgressItem[]>([]);
  const [passMark, setPassMark] = useState(PASS_MARK);

  useEffect(() => {
    getProgress().then(setRows).catch(() => setRows([]));
  }, []);

  const summary = useMemo(() => {
    const total = rows.length;
    const passed = rows.filter((r) => (Number(r.assessment_score) || 0) >= passMark).length;
    const passRate = total > 0 ? ((passed / total) * 100).toFixed(2) : "0.00";
    return { total, passed, passRate };
  }, [rows, passMark]);

  return (
    <section className="card">
      <h2>Assessment Pass Rate Details</h2>
      <div className="controls">
        <label className="range-control">
          Pass Mark: <b>{passMark}</b>
          <input
            type="range"
            min={40}
            max={100}
            value={passMark}
            onChange={(e) => setPassMark(Number(e.target.value))}
          />
        </label>
      </div>
      <p>
        Pass mark: <b>{passMark}</b> | Passed: <b>{summary.passed}</b> / <b>{summary.total}</b> |
        Pass Rate: <b>{summary.passRate}%</b>
      </p>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Module</th>
              <th>Score</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => {
              const score = Number(item.assessment_score) || 0;
              const passed = score >= passMark;
              return (
                <tr key={`${item.user_id}-${item.module_code}`}>
                  <td>{item.user_id}</td>
                  <td>{item.module_code}</td>
                  <td>{score}</td>
                  <td>{passed ? "Passed" : "Failed"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
