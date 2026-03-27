import { cn } from "@/lib/utils";

export default function CeoScoreBadge({ score, className }: { score: number; className?: string }) {
  const color =
    score >= 8
      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
      : score >= 6
        ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        : "bg-red-500/20 text-red-400 border-red-500/30";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        color,
        className
      )}
    >
      CEO: {score.toFixed(1)}
    </span>
  );
}
