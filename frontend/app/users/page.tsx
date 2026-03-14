"use client";

import { useEffect, useMemo, useState } from "react";
import { getUsers } from "@/lib/api";
import type { UserItem } from "@/lib/types";

export default function UsersPage() {
  const [rows, setRows] = useState<UserItem[]>([]);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");

  useEffect(() => {
    getUsers().then(setRows).catch(() => setRows([]));
  }, []);

  const roles = useMemo(
    () =>
      [
        "all",
        ...Array.from(new Set(rows.map((item) => item.role_name ?? "unassigned"))).sort(),
      ],
    [rows]
  );

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((item) => {
      const itemRole = item.role_name ?? "unassigned";
      const matchesRole = role === "all" || itemRole === role;
      const matchesQuery =
        !q ||
        item.full_name.toLowerCase().includes(q) ||
        item.email.toLowerCase().includes(q) ||
        item.user_id.toLowerCase().includes(q);
      return matchesRole && matchesQuery;
    });
  }, [rows, query, role]);

  return (
    <section className="card">
      <h2>System Users</h2>
      <div className="controls">
        <input
          className="input"
          placeholder="Search by name/email/user id..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
          {roles.map((item) => (
            <option key={item} value={item}>
              {item === "all" ? "All Roles" : item}
            </option>
          ))}
        </select>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>User ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((item) => (
              <tr key={item.user_id}>
                <td>{item.user_id}</td>
                <td>{item.full_name}</td>
                <td>{item.email}</td>
                <td>{item.role_name ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
