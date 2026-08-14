"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function NotificationsPage() {
  const [items, setItems] = useState<any[]>([]);

  async function load() {
    const r = await api<{ items: any[] }>("/api/v1/notifications");
    setItems(r.data.items);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function markRead(n: any) {
    if (!n.is_read) {
      await api(`/api/v1/notifications/${n.id}/read`, { method: "POST" });
      await load();
    }
  }

  return (
    <RequireAuth>
      <AppShell title="Notifications" subtitle="Meetings, notices, tasks and attendance alerts">
        <div className="space-y-3">
          {items.map((n) => (
            <div
              key={n.id}
              className={`glass-panel w-full rounded-2xl p-4 text-left ${n.is_read ? "opacity-70" : "border border-sky-500/20"}`}
            >
              <button type="button" onClick={() => markRead(n)} className="w-full text-left">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="font-semibold text-navy-900">{n.title}</div>
                  {n.category && (
                    <span className="rounded-full bg-cloud-100 px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted">
                      {n.category.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-sm text-muted">{n.body}</div>
                <div className="mt-2 text-xs text-muted">{new Date(n.created_at).toLocaleString()}</div>
              </button>
              {n.link && (
                <Link href={n.link.startsWith("/app") ? n.link : `/app${n.link.startsWith("/") ? n.link : `/${n.link}`}`} className="mt-2 inline-block text-sm font-medium text-sky-500">
                  Open
                </Link>
              )}
            </div>
          ))}
          {!items.length && <div className="text-sm text-muted">No notifications yet.</div>}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
