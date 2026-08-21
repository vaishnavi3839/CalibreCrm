import { cn } from "@/lib/utils";

/** Shared mobile card field row */
export function FieldRow({
  label,
  value,
  className,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex justify-between gap-3 text-sm", className)}>
      <dt className="shrink-0 text-muted">{label}</dt>
      <dd className="max-w-[65%] break-words text-right text-navy-900">{value ?? "—"}</dd>
    </div>
  );
}
