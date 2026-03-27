import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  draft: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  researching: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  creating: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  processing: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  review: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  approved: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  ready: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  published: "bg-green-500/20 text-green-400 border-green-500/30",
  posted: "bg-green-500/20 text-green-400 border-green-500/30",
  rejected: "bg-red-500/20 text-red-400 border-red-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  failed: "bg-red-500/20 text-red-400 border-red-500/30",
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  rate_limited: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  disabled: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  running: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

export default function StatusBadge({ status, className }: { status: string; className?: string }) {
  const colors = STATUS_COLORS[status] || "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        colors,
        className
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
