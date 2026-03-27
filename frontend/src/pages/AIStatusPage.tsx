import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchAIStatus, resetAILimits } from "@/lib/api";
import type { AIProvider } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function AIStatusPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  function load() {
    setLoading(true);
    fetchAIStatus()
      .then((r) => setProviders(r.providers))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleReset() {
    setResetting(true);
    try {
      await resetAILimits();
      toast.success("All limits reset!");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  }

  function usagePercent(used: number, limit: number) {
    if (limit === 0) return 0;
    return Math.min((used / limit) * 100, 100);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Status Monitor</h1>
          <p className="mt-1 text-zinc-400">Real-time status of all AI providers</p>
        </div>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-700 disabled:opacity-50"
        >
          {resetting ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
          Reset All Limits
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden overflow-hidden rounded-xl border border-zinc-800 md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/80">
                <tr>
                  <th className="px-4 py-3 font-medium text-zinc-400">Provider</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Model</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Type</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Status</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Used / Limit</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Last Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {providers.map((p) => (
                  <tr key={p.name} className="transition-colors hover:bg-zinc-900/60">
                    <td className="px-4 py-3 font-medium text-zinc-200">{p.name.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 font-mono text-xs text-zinc-400">{p.model}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        p.type === "text" ? "bg-blue-500/20 text-blue-400" : "bg-pink-500/20 text-pink-400"
                      }`}>
                        {p.type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className={`h-full rounded-full transition-all ${
                              usagePercent(p.requests_today, p.daily_limit) >= 90
                                ? "bg-red-500"
                                : usagePercent(p.requests_today, p.daily_limit) >= 60
                                  ? "bg-yellow-500"
                                  : "bg-emerald-500"
                            }`}
                            style={{ width: `${usagePercent(p.requests_today, p.daily_limit)}%` }}
                          />
                        </div>
                        <span className="text-xs text-zinc-400">
                          {p.requests_today}/{p.daily_limit}
                        </span>
                      </div>
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-xs text-red-400">
                      {p.last_error || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 md:hidden">
            {providers.map((p) => (
              <div key={p.name} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-zinc-200">{p.name.replace(/_/g, " ")}</span>
                  <StatusBadge status={p.status} />
                </div>
                <p className="mt-1 font-mono text-xs text-zinc-500">{p.model}</p>
                <div className="mt-3 flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className={`h-full rounded-full ${
                        usagePercent(p.requests_today, p.daily_limit) >= 90
                          ? "bg-red-500"
                          : usagePercent(p.requests_today, p.daily_limit) >= 60
                            ? "bg-yellow-500"
                            : "bg-emerald-500"
                      }`}
                      style={{ width: `${usagePercent(p.requests_today, p.daily_limit)}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-400">{p.requests_today}/{p.daily_limit}</span>
                </div>
                {p.last_error && (
                  <p className="mt-2 truncate text-xs text-red-400">{p.last_error}</p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
