import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package, Clock, CheckCircle, Send, AlertTriangle, PlusCircle, Cpu, ArrowRight, TrendingUp, Zap } from "lucide-react";
import { fetchStats, fetchProducts, fetchTrendAlerts } from "@/lib/api";
import type { Stats, Product, TrendPrediction } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import Spinner from "@/components/Spinner";

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-zinc-400">{label}</p>
          <p className="mt-1 text-3xl font-bold text-zinc-100">{value}</p>
        </div>
        <div className={`rounded-lg p-3 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<Product[]>([]);
  const [trendAlerts, setTrendAlerts] = useState<TrendPrediction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchStats(), fetchProducts(), fetchTrendAlerts()])
      .then(([s, p, t]) => {
        setStats(s);
        setRecent(p.products.slice(0, 10));
        setTrendAlerts(t.alerts || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const byStatus = stats?.products.by_status || {};

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 text-zinc-400">Overview of your AI Product Factory</p>
      </div>

      {/* Trend Alerts Banner */}
      {trendAlerts.length > 0 && (
        <div className="space-y-2">
          {trendAlerts.map((alert) => (
            <Link
              key={alert.id}
              to="/trends"
              className="flex items-center gap-3 rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-4 transition-colors hover:bg-cyan-500/15"
            >
              <div className="rounded-lg bg-cyan-500/20 p-2">
                <Zap className="h-5 w-5 text-cyan-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-cyan-300">
                  Trend Alert: {alert.trend_name} will peak{" "}
                  {alert.time_remaining ? `in ${alert.time_remaining}` : "soon"}
                </p>
                <p className="mt-0.5 text-xs text-zinc-400">
                  {alert.action} • {alert.confidence}% confidence
                </p>
              </div>
              <TrendingUp className="h-5 w-5 text-cyan-400" />
            </Link>
          ))}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Total Products" value={stats?.products.total || 0} icon={Package} color="bg-violet-500/20 text-violet-400" />
        <StatCard label="Pending" value={(byStatus.draft || 0) + (byStatus.pending || 0)} icon={Clock} color="bg-yellow-500/20 text-yellow-400" />
        <StatCard label="Ready" value={(byStatus.approved || 0)} icon={CheckCircle} color="bg-emerald-500/20 text-emerald-400" />
        <StatCard label="Posted" value={byStatus.published || 0} icon={Send} color="bg-blue-500/20 text-blue-400" />
        <StatCard label="Errors" value={byStatus.rejected || 0} icon={AlertTriangle} color="bg-red-500/20 text-red-400" />
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          to="/new"
          className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-violet-500/50 hover:bg-zinc-900"
        >
          <div className="rounded-lg bg-violet-500/20 p-3 text-violet-400">
            <PlusCircle className="h-5 w-5" />
          </div>
          <div>
            <p className="font-medium">Create Product</p>
            <p className="text-sm text-zinc-400">Start a new AI pipeline</p>
          </div>
        </Link>
        <Link
          to="/products"
          className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-fuchsia-500/50 hover:bg-zinc-900"
        >
          <div className="rounded-lg bg-fuchsia-500/20 p-3 text-fuchsia-400">
            <Package className="h-5 w-5" />
          </div>
          <div>
            <p className="font-medium">View Products</p>
            <p className="text-sm text-zinc-400">Manage all products</p>
          </div>
        </Link>
        <Link
          to="/ai-status"
          className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-pink-500/50 hover:bg-zinc-900"
        >
          <div className="rounded-lg bg-pink-500/20 p-3 text-pink-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <p className="font-medium">AI Status</p>
            <p className="text-sm text-zinc-400">Monitor AI providers</p>
          </div>
        </Link>
      </div>

      {/* Recent Products */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Products</h2>
          <Link to="/products" className="flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300">
            View all <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {recent.length === 0 ? (
          <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
            <Package className="mx-auto h-10 w-10 text-zinc-600" />
            <p className="mt-3 text-zinc-400">No products yet. Create your first one!</p>
            <Link
              to="/new"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
            >
              <PlusCircle className="h-4 w-4" /> New Product
            </Link>
          </div>
        ) : (
          <div className="mt-4 overflow-hidden rounded-xl border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/80">
                <tr>
                  <th className="px-4 py-3 font-medium text-zinc-400">Name</th>
                  <th className="hidden px-4 py-3 font-medium text-zinc-400 sm:table-cell">Status</th>
                  <th className="hidden px-4 py-3 font-medium text-zinc-400 md:table-cell">Platforms</th>
                  <th className="hidden px-4 py-3 font-medium text-zinc-400 lg:table-cell">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {recent.map((p) => (
                  <tr key={p.id} className="transition-colors hover:bg-zinc-900/60">
                    <td className="px-4 py-3 font-medium">{p.name}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="hidden px-4 py-3 md:table-cell">
                      <span className="text-zinc-400">{p.target_platforms.join(", ") || "—"}</span>
                    </td>
                    <td className="hidden px-4 py-3 text-zinc-400 lg:table-cell">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/products/${p.id}`} className="text-violet-400 hover:text-violet-300">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
