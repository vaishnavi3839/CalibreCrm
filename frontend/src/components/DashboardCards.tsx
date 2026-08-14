"use client";

export function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  return (
    <div className="glass-panel rounded-2xl p-4 transition hover:-translate-y-0.5">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-2 text-3xl font-semibold ${accent || "text-navy-900"}`}>{value}</div>
    </div>
  );
}

export function LeaderboardCard({
  rows,
  title = "Leaderboard",
}: {
  rows: { name: string; photo_url?: string | null; score?: number; calls?: number; admissions?: number }[];
  title?: string;
}) {
  if (!rows?.length) return null;
  return (
    <div className="glass-panel rounded-2xl p-5">
      <h2 className="font-semibold text-navy-900">{title}</h2>
      <div className="mt-4 space-y-3">
        {rows.map((row, i) => (
          <div key={`${row.name}-${i}`} className="flex items-center justify-between rounded-xl bg-cloud-50 px-4 py-3">
            <div className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={
                  row.photo_url ||
                  `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(String(row.name).replace(/\s/g, ""))}`
                }
                alt={row.name}
                className="h-11 w-11 rounded-full border-2 border-brass-500/40 object-cover"
              />
              <div>
                <div className="font-medium text-navy-900">
                  {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}.`} {row.name}
                </div>
                <div className="text-xs text-muted">
                  {row.calls ?? 0} calls · {row.admissions ?? 0} admissions
                </div>
              </div>
            </div>
            <div className="text-sm font-semibold text-brass-500">{row.score ?? 0} pts</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="glass-panel block rounded-2xl px-4 py-5 text-center text-sm font-medium text-navy-900 transition hover:-translate-y-0.5 hover:border-sky-500/30"
    >
      {label}
    </a>
  );
}
