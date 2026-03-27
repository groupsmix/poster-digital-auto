import { useEffect, useState } from "react";
import { Target, TrendingUp, DollarSign, PlusCircle, AlertTriangle, Trophy, Info, RefreshCw } from "lucide-react";
import { fetchGoals, createRevenueGoal, refreshGoals } from "@/lib/api";
import type { RevenueGoal } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

const PERIOD_OPTIONS = ["weekly", "monthly", "quarterly", "yearly"];

const STATUS_COLORS: Record<string, string> = {
  achieved: "text-emerald-400",
  on_track: "text-blue-400",
  behind: "text-yellow-400",
  at_risk: "text-red-400",
};

const SUGGESTION_ICONS: Record<string, React.ElementType> = {
  success: Trophy,
  action: AlertTriangle,
  insight: Target,
  pricing: DollarSign,
  motivation: TrendingUp,
  info: Info,
};

export default function RevenueGoalsPage() {
  const [goals, setGoals] = useState<RevenueGoal[]>([]);
  const [activeGoal, setActiveGoal] = useState<RevenueGoal | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [targetAmount, setTargetAmount] = useState("1000");
  const [period, setPeriod] = useState("monthly");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadGoals();
  }, []);

  async function loadGoals() {
    setLoading(true);
    try {
      const res = await fetchGoals();
      setGoals(res.goals);
      setActiveGoal(res.active_goal);
    } catch {
      toast.error("Failed to load goals");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!targetAmount) return;
    setCreating(true);
    try {
      const res = await createRevenueGoal(parseFloat(targetAmount), period);
      toast.success(res.message);
      setShowCreate(false);
      loadGoals();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create goal");
    } finally {
      setCreating(false);
    }
  }

  async function handleRefresh() {
    try {
      await refreshGoals();
      toast.success("Goals refreshed");
      loadGoals();
    } catch {
      toast.error("Failed to refresh goals");
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-32">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Revenue Goals</h1>
          <p className="mt-1 text-zinc-400">Set targets, track progress, get smart suggestions</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-700"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
          >
            <PlusCircle className="h-4 w-4" />
            New Goal
          </button>
        </div>
      </div>

      {/* Create Goal Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 w-full max-w-md rounded-xl border border-zinc-700 bg-zinc-900 p-6">
            <h3 className="text-lg font-bold text-zinc-100">Set Revenue Goal</h3>
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-zinc-400">Target Amount ($)</label>
                <input
                  type="number"
                  step="100"
                  value={targetAmount}
                  onChange={(e) => setTargetAmount(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
                  placeholder="1000"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400">Period</label>
                <div className="mt-1 flex gap-2">
                  {PERIOD_OPTIONS.map((p) => (
                    <button
                      key={p}
                      onClick={() => setPeriod(p)}
                      className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                        period === p
                          ? "border-violet-500 bg-violet-500/20 text-violet-300"
                          : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                      }`}
                    >
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleCreate}
                disabled={creating || !targetAmount}
                className="flex-1 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
              >
                {creating ? "Creating..." : "Set Goal"}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Goal Widget */}
      {activeGoal && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-zinc-200">
              <Target className="h-5 w-5 text-violet-400" />
              Active Goal
            </h2>
            <span className={`text-sm font-medium ${STATUS_COLORS[activeGoal.status_label] || "text-zinc-400"}`}>
              {activeGoal.status_label === "achieved" ? "Achieved!" :
               activeGoal.status_label === "on_track" ? "On Track" :
               activeGoal.status_label === "behind" ? "Behind" : "At Risk"}
            </span>
          </div>

          {/* Progress bar */}
          <div className="mt-4">
            <div className="flex items-end justify-between">
              <p className="text-3xl font-bold text-zinc-100">
                ${activeGoal.current_amount.toFixed(2)}
              </p>
              <p className="text-sm text-zinc-400">
                of ${activeGoal.target_amount.toFixed(2)} / {activeGoal.period}
              </p>
            </div>
            <div className="mt-3 h-4 overflow-hidden rounded-full bg-zinc-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  activeGoal.progress_percent >= 100
                    ? "bg-emerald-500"
                    : activeGoal.progress_percent >= 75
                      ? "bg-blue-500"
                      : activeGoal.progress_percent >= 50
                        ? "bg-yellow-500"
                        : "bg-red-500"
                }`}
                style={{ width: `${Math.min(activeGoal.progress_percent, 100)}%` }}
              />
            </div>
            <p className="mt-1 text-right text-sm text-zinc-400">
              {activeGoal.progress_percent}%
            </p>
          </div>

          {/* Stats grid */}
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-zinc-800 p-3 text-center">
              <p className="text-lg font-bold text-zinc-200">${activeGoal.remaining.toFixed(2)}</p>
              <p className="text-xs text-zinc-500">Remaining</p>
            </div>
            <div className="rounded-lg bg-zinc-800 p-3 text-center">
              <p className="text-lg font-bold text-zinc-200">{activeGoal.sales_needed}</p>
              <p className="text-xs text-zinc-500">Sales Needed</p>
            </div>
            <div className="rounded-lg bg-zinc-800 p-3 text-center">
              <p className="text-lg font-bold text-zinc-200">${activeGoal.avg_sale_price.toFixed(2)}</p>
              <p className="text-xs text-zinc-500">Avg Sale Price</p>
            </div>
            <div className="rounded-lg bg-zinc-800 p-3 text-center">
              <p className="text-lg font-bold text-zinc-200">{activeGoal.total_products}</p>
              <p className="text-xs text-zinc-500">Total Products</p>
            </div>
          </div>

          {/* Suggestions */}
          {activeGoal.suggestions && activeGoal.suggestions.length > 0 && (
            <div className="mt-4 space-y-2">
              {activeGoal.suggestions.map((suggestion, i) => {
                const Icon = SUGGESTION_ICONS[suggestion.type] || Info;
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-3 rounded-lg p-3 ${
                      suggestion.type === "success"
                        ? "bg-emerald-500/10 border border-emerald-500/30"
                        : suggestion.type === "action"
                          ? "bg-yellow-500/10 border border-yellow-500/30"
                          : "bg-zinc-800"
                    }`}
                  >
                    <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                      suggestion.type === "success" ? "text-emerald-400" :
                      suggestion.type === "action" ? "text-yellow-400" :
                      suggestion.type === "pricing" ? "text-emerald-400" :
                      "text-zinc-400"
                    }`} />
                    <p className="text-sm text-zinc-300">{suggestion.message}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* All Goals */}
      {goals.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Target className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No revenue goals set yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
          >
            <PlusCircle className="h-4 w-4" /> Set Your First Goal
          </button>
        </div>
      ) : goals.length > 1 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold">Goal History</h2>
          <div className="space-y-3">
            {goals.filter(g => g.id !== activeGoal?.id).map((goal) => (
              <div key={goal.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-zinc-200">
                      ${goal.target_amount.toFixed(2)} / {goal.period}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Progress: ${goal.current_amount.toFixed(2)} ({goal.progress_percent}%)
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    goal.status === "active" ? "bg-blue-500/20 text-blue-300" : "bg-zinc-700 text-zinc-400"
                  }`}>
                    {goal.status}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-800">
                  <div
                    className="h-full rounded-full bg-zinc-600"
                    style={{ width: `${Math.min(goal.progress_percent, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
