"use client";

import { useEffect, useState } from "react";
import { getNotifications } from "@/lib/api";
import type { NotificationItem } from "@/lib/types";

export default function NotificationsPage() {
  const [rows, setRows] = useState<NotificationItem[]>([]);

  useEffect(() => {
    getNotifications().then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <section className="card">
      <h2>Automated Notifications</h2>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Title</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.notification_id}>
                <td>{item.notification_type}</td>
                <td>{item.title}</td>
                <td>
                  <span className="pill">{item.status}</span>
                </td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
