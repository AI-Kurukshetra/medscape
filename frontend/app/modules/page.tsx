"use client";

import { useEffect, useMemo, useState } from "react";
import { getModules } from "@/lib/api";
import type { ModuleItem } from "@/lib/types";

export default function ModulesPage() {
  const [rows, setRows] = useState<ModuleItem[]>([]);
  const [query, setQuery] = useState("");
  const [regulation, setRegulation] = useState("all");

  useEffect(() => {
    getModules().then(setRows).catch(() => setRows([]));
  }, []);

  const regulations = useMemo(
    () => ["all", ...Array.from(new Set(rows.map((item) => item.regulation))).sort()],
    [rows]
  );

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((item) => {
      const matchesReg = regulation === "all" || item.regulation === regulation;
      const matchesQuery =
        !q ||
        item.code.toLowerCase().includes(q) ||
        item.title.toLowerCase().includes(q) ||
        item.regulation.toLowerCase().includes(q);
      return matchesReg && matchesQuery;
    });
  }, [rows, query, regulation]);

  return (
    <section className="card">
      <h2>Training Modules</h2>
      <div className="controls">
        <input
          className="input"
          placeholder="Search module code/title..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="input" value={regulation} onChange={(e) => setRegulation(e.target.value)}>
          {regulations.map((item) => (
            <option key={item} value={item}>
              {item === "all" ? "All Regulations" : item}
            </option>
          ))}
        </select>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Title</th>
              <th>Regulation</th>
              <th>Minutes</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((item) => (
              <tr key={item.code}>
                <td>
                  <span className="pill">{item.code}</span>
                </td>
                <td>{item.title}</td>
                <td>{item.regulation}</td>
                <td>{item.total_estimated_minutes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
