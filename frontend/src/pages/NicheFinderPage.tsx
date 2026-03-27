import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Sparkles, TrendingUp, ArrowUpDown,
  Filter, PlusCircle, X, Bookmark, RefreshCw, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { fetchNiches, scanNiches, createProductFromNiche, updateNicheStatus } from "@/lib/api";
import type { NicheIdea } from "@/lib/types";
import Spinner from "@/components/Spinner";

const COMPETITION_COLORS: Record<string, string> = {
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  high: "bg-red-500/20 text-red-400 border-red-500/30",
};

function DemandBadge({ score }: { score: number }) {
  let color = "bg-zinc-500/20 text-zinc-400";
  if (score >= 8) color = "bg-emerald-500/20 text-emerald-400";
  else if (score >= 6) color = "bg-blue-500/20 text-blue-400";
  else if (score >= 4) color = "bg-yellow-500/20 text-yellow-400";
  else color = "bg-red-500/20 text-red-400";

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-bold ${color}`}>
      <TrendingUp className="h-3.5 w-3.5" />
      {score}/10
    </span>
  );
}

export default function NicheFinderPage() {
  const navigate = useNavigate();
  const [ideas, setIdeas] = useState<NicheIdea[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("demand_score");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadIdeas = () => {
    setLoading(true);
    fetchNiches(filterStatus || undefined, sortBy)
      .then((res) => setIdeas(res.ideas))
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadIdeas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, sortBy]);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await scanNiches();
      toast.success(result.message);
      loadIdeas();
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
      const result = await createProductFromNiche(id);
      toast.success(result.message);
      navigate(`/products/${result.product_id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create product";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateStatus = async (id: number, status: string) => {
    setActionLoading(id);
    try {
      await updateNicheStatus(id, status);
      toast.success(`Idea ${status}`);
      loadIdeas();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update";
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
            <Sparkles className="h-6 w-6 text-amber-400" />
            Niche Finder AI
          </h1>
          <p className="mt-1 text-zinc-400">
            AI-discovered product ideas with proven demand
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
        >
          {scanning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {scanning ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-zinc-400" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
            <option value="created">Created</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown className="h-4 w-4 text-zinc-400" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
          >
            <option value="demand_score">Demand Score</option>
            <option value="monthly_searches">Monthly Searches</option>
            <option value="competition">Competition</option>
            <option value="created_at">Date Found</option>
          </select>
        </div>
        {filterStatus && (
          <button
            onClick={() => setFilterStatus("")}
            className="inline-flex items-center gap-1 rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200"
          >
            Clear <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : ideas.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-16 text-center">
          <Sparkles className="mx-auto h-12 w-12 text-zinc-600" />
          <p className="mt-4 text-lg text-zinc-400">No niche ideas found yet</p>
          <p className="mt-1 text-sm text-zinc-500">
            Click &quot;Scan Now&quot; to let AI discover product opportunities
          </p>
        </div>
      ) : (
        /* Card Grid */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ideas.map((idea) => (
            <div
              key={idea.id}
              className="group rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-zinc-700"
            >
              {/* Top: name + demand */}
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-semibold text-zinc-100 leading-tight">
                  {idea.product_name}
                </h3>
                <DemandBadge score={idea.demand_score} />
              </div>

              {/* Meta row */}
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <span
                  className={`inline-flex items-center rounded-full border px-2 py-0.5 font-medium capitalize ${
                    COMPETITION_COLORS[idea.competition] || COMPETITION_COLORS.medium
                  }`}
                >
                  {idea.competition} competition
                </span>
                <span className="text-zinc-500">
                  {idea.monthly_searches > 0
                    ? `${idea.monthly_searches.toLocaleString()} monthly searches`
                    : "Est. searches N/A"}
                </span>
              </div>

              {/* Price */}
              <div className="mt-3 text-sm text-zinc-300">
                <span className="text-zinc-500">Price: </span>
                <span className="font-medium text-emerald-400">{idea.suggested_price}</span>
              </div>

              {/* Evidence */}
              {idea.evidence && (
                <p className="mt-2 text-xs text-zinc-500 line-clamp-2">
                  {idea.evidence}
                </p>
              )}

              {/* Platforms */}
              {idea.best_platforms && idea.best_platforms.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {idea.best_platforms.map((p) => (
                    <span
                      key={p}
                      className="rounded-md bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 flex items-center gap-2">
                {idea.status === "new" || idea.status === "approved" ? (
                  <>
                    <button
                      onClick={() => handleCreateProduct(idea.id)}
                      disabled={actionLoading === idea.id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                    >
                      {actionLoading === idea.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <PlusCircle className="h-3 w-3" />
                      )}
                      Create Product
                    </button>
                    <button
                      onClick={() => handleUpdateStatus(idea.id, "rejected")}
                      disabled={actionLoading === idea.id}
                      className="inline-flex items-center gap-1 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 disabled:opacity-50"
                    >
                      <X className="h-3 w-3" />
                      Dismiss
                    </button>
                    <button
                      onClick={() => handleUpdateStatus(idea.id, "archived")}
                      disabled={actionLoading === idea.id}
                      className="inline-flex items-center gap-1 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 disabled:opacity-50"
                    >
                      <Bookmark className="h-3 w-3" />
                      Save
                    </button>
                  </>
                ) : idea.status === "created" ? (
                  <span className="text-xs text-emerald-400">
                    Product created (#{idea.created_product_id})
                  </span>
                ) : idea.status === "archived" ? (
                  <button
                    onClick={() => handleUpdateStatus(idea.id, "new")}
                    disabled={actionLoading === idea.id}
                    className="inline-flex items-center gap-1 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 disabled:opacity-50"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Restore
                  </button>
                ) : (
                  <span className="text-xs text-zinc-500 capitalize">{idea.status}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
