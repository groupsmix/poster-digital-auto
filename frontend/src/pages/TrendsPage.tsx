import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, Calendar, Zap, Clock, Target,
  PlusCircle, Search, Loader2, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { fetchTrends, scanTrends, createProductFromTrend } from "@/lib/api";
import type { TrendPrediction } from "@/lib/types";
import Spinner from "@/components/Spinner";

const PHASE_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  early_rise: {
    label: "Early Rise",
    color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    icon: TrendingUp,
  },
  rising: {
    label: "Rising",
    color: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    icon: TrendingUp,
  },
  approaching_peak: {
    label: "Approaching Peak",
    color: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    icon: Zap,
  },
  at_peak: {
    label: "At Peak",
    color: "bg-red-500/20 text-red-400 border-red-500/30",
    icon: AlertTriangle,
  },
};

const CATEGORY_COLORS: Record<string, string> = {
  seasonal: "bg-cyan-500/20 text-cyan-400",
  social: "bg-pink-500/20 text-pink-400",
  evergreen: "bg-emerald-500/20 text-emerald-400",
  event: "bg-violet-500/20 text-violet-400",
};

function ConfidenceBar({ confidence }: { confidence: number }) {
  let barColor = "bg-red-500";
  if (confidence >= 80) barColor = "bg-emerald-500";
  else if (confidence >= 60) barColor = "bg-blue-500";
  else if (confidence >= 40) barColor = "bg-yellow-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${confidence}%` }} />
      </div>
      <span className="text-xs font-medium text-zinc-400">{confidence}%</span>
    </div>
  );
}

export default function TrendsPage() {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<TrendPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadTrends = () => {
    setLoading(true);
    fetchTrends(filterStatus || undefined)
      .then((res) => setPredictions(res.predictions))
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTrends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await scanTrends();
      toast.success(result.message);
      loadTrends();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Scan failed";
      toast.error(message);
    } finally {
      setScanning(false);
    }
  };

  const handleCreateProduct = async (id: number) => {
    setActionLoading(id);
    try {
      const result = await createProductFromTrend(id);
      toast.success(result.message);
      navigate(`/products/${result.product_id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <TrendingUp className="h-6 w-6 text-cyan-400" />
            Trend Predictor AI
          </h1>
          <p className="mt-1 text-zinc-400">
            Predict what will trend in 2-4 weeks and act early
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cyan-500 disabled:opacity-50"
        >
          {scanning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {scanning ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-200 focus:border-cyan-500 focus:outline-none"
        >
          <option value="">All Predictions</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="created">Product Created</option>
        </select>
      </div>

      {/* Loading / Empty */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : predictions.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-16 text-center">
          <TrendingUp className="mx-auto h-12 w-12 text-zinc-600" />
          <p className="mt-4 text-lg text-zinc-400">No trend predictions yet</p>
          <p className="mt-1 text-sm text-zinc-500">
            Click &quot;Scan Now&quot; to let AI predict upcoming trends
          </p>
        </div>
      ) : (
        /* Trend Cards */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {predictions.map((pred) => {
            const phaseInfo = PHASE_CONFIG[pred.current_phase] || PHASE_CONFIG.early_rise;
            const PhaseIcon = phaseInfo.icon;
            const catColor = CATEGORY_COLORS[pred.category] || "bg-zinc-500/20 text-zinc-400";

            return (
              <div
                key={pred.id}
                className="group rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-zinc-700"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-zinc-100 leading-tight">
                    {pred.trend_name}
                  </h3>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${phaseInfo.color}`}
                  >
                    <PhaseIcon className="h-3 w-3" />
                    {phaseInfo.label}
                  </span>
                </div>

                {/* Confidence */}
                <div className="mt-3">
                  <p className="mb-1 text-xs text-zinc-500">Confidence</p>
                  <ConfidenceBar confidence={pred.confidence} />
                </div>

                {/* Peak date & time remaining */}
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Calendar className="h-3.5 w-3.5 text-zinc-500" />
                    <span>
                      {pred.predicted_peak
                        ? new Date(pred.predicted_peak + "T00:00:00").toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })
                        : "TBD"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Clock className="h-3.5 w-3.5 text-zinc-500" />
                    <span>{pred.time_remaining || "—"}</span>
                  </div>
                </div>

                {/* Category */}
                {pred.category && (
                  <div className="mt-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${catColor}`}>
                      {pred.category}
                    </span>
                  </div>
                )}

                {/* Action */}
                {pred.action && (
                  <div className="mt-3 rounded-lg bg-zinc-800/60 p-2.5">
                    <p className="flex items-start gap-1.5 text-xs text-zinc-300">
                      <Target className="mt-0.5 h-3 w-3 shrink-0 text-cyan-400" />
                      {pred.action}
                    </p>
                  </div>
                )}

                {/* Evidence */}
                {pred.evidence && (
                  <p className="mt-2 text-xs text-zinc-500 line-clamp-2">
                    {pred.evidence}
                  </p>
                )}

                {/* Create button */}
                <div className="mt-4">
                  {pred.status === "active" ? (
                    <button
                      onClick={() => handleCreateProduct(pred.id)}
                      disabled={actionLoading === pred.id}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-medium text-white hover:bg-cyan-500 disabled:opacity-50"
                    >
                      {actionLoading === pred.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <PlusCircle className="h-3.5 w-3.5" />
                      )}
                      Create product for this trend
                    </button>
                  ) : pred.status === "created" ? (
                    <span className="text-xs text-emerald-400">
                      Product created (#{pred.created_product_id})
                    </span>
                  ) : (
                    <span className="text-xs text-zinc-500 capitalize">{pred.status}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
