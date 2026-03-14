"use client";

import { useEffect, useState } from "react";
import { getAuditLogs } from "@/lib/api";
import type { AuditItem } from "@/lib/types";

export default function AuditPage() {
  const [rows, setRows] = useState<AuditItem[]>([]);

  useEffect(() => {
    getAuditLogs().then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <section className="card">
      <h2>Audit Trail & Logging</h2>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Entity</th>
              <th>Actor</th>
              <th>Org</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.audit_id}>
                <td>{item.action}</td>
                <td>{item.entity_type}</td>
                <td>{item.actor_user_id ?? "system"}</td>
                <td>{item.organization_slug ?? "global"}</td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
