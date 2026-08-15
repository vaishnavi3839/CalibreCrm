"use client";

export type TopPerformer = {
  name: string;
  photo_url?: string | null;
  score?: number;
  calls?: number;
  admissions?: number;
};

function Sparkle({ className }: { className?: string }) {
  return (
    <span className={`sparkle-dot absolute ${className || ""}`} aria-hidden>
      ✦
    </span>
  );
}

export function TopPerformerSpotlight({
  performer,
  compact = false,
}: {
  performer?: TopPerformer | string | null;
  compact?: boolean;
}) {
  if (!performer) return null;

  const data: TopPerformer =
    typeof performer === "string" ? { name: performer } : performer;

  if (!data.name) return null;

  const photo =
    data.photo_url ||
    `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(data.name.replace(/\s/g, ""))}&backgroundColor=0a1628`;

  const size = compact ? "h-28 w-28 sm:h-32 sm:w-32" : "h-40 w-40 sm:h-48 sm:w-48";

  return (
    <div
      className="top-performer-card relative overflow-hidden rounded-3xl border border-brass-500/30 bg-gradient-to-br from-navy-900 via-navy-800 to-navy-700 p-5 shadow-[0_20px_60px_rgba(10,22,40,0.35)] animate-rise"
      style={{ color: "#ffffff" }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(196,163,90,0.35),transparent_45%),radial-gradient(circle_at_10%_90%,rgba(74,159,216,0.25),transparent_40%)]" />
      <div className="relative flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-8">
        <div className={`relative ${size} shrink-0`}>
          <div className="absolute -inset-2 rounded-full bg-gradient-to-br from-brass-400 via-sky-400 to-brass-500 opacity-80 blur-md sparkle-glow" />
          <div className="relative h-full w-full overflow-hidden rounded-full border-4 border-brass-400/80 shadow-xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photo} alt={data.name} className="h-full w-full object-cover" />
          </div>
          <Sparkle className="left-2 top-3 text-brass-400 text-lg sparkle-1" />
          <Sparkle className="right-1 top-8 text-sky-300 text-base sparkle-2" />
          <Sparkle className="bottom-4 left-0 text-brass-400 text-xl sparkle-3" />
          <Sparkle className="bottom-2 right-3 text-sm sparkle-1" />
          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 rounded-full bg-brass-500 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-navy-900 shadow-lg">
            #1 Today
          </div>
        </div>

        <div className="relative z-10 text-center sm:text-left">
          <div className="text-xs uppercase tracking-[0.22em] text-brass-400">Today&apos;s Top Performer</div>
          <h2 className="mt-1 font-[family-name:var(--font-display)] text-3xl leading-tight sm:text-4xl" style={{ color: "#ffffff" }}>
            {data.name}
          </h2>
          <p className="mt-2 text-sm" style={{ color: "rgba(255,255,255,0.7)" }}>Keep Climbing · Calibre Aviation Academy</p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
            {typeof data.score === "number" && (
              <span className="rounded-full px-3 py-1 text-sm font-semibold text-brass-400" style={{ backgroundColor: "rgba(255,255,255,0.1)" }}>
                {data.score} pts
              </span>
            )}
            {typeof data.calls === "number" && (
              <span className="rounded-full px-3 py-1 text-sm" style={{ backgroundColor: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.9)" }}>
                {data.calls} calls
              </span>
            )}
            {typeof data.admissions === "number" && data.admissions > 0 && (
              <span className="rounded-full px-3 py-1 text-sm" style={{ backgroundColor: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.9)" }}>
                {data.admissions} admissions
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Official Calibre Aviation Academy emblem */
export function BrandLogo({
  className = "h-16 w-auto",
  priority = false,
}: {
  className?: string;
  priority?: boolean;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/calibre-logo-clean.png"
      alt="Calibre Aviation Academy"
      width={752}
      height={687}
      className={`object-contain ${className}`}
      decoding="async"
      {...(priority ? { fetchPriority: "high" as const } : {})}
    />
  );
}
