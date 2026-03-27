import { useEffect, useState } from "react";
import { Loader2, Eye, AlertTriangle, X, Search } from "lucide-react";
import { scanCompetitors, fetchCompetitors, fetchCompetitorAlerts, dismissCompetitorAlert } from "@/lib/api";
import type { Competitor, CompetitorAlert } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function CompetitorSpyPage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [alerts, setAlerts] = useState<CompetitorAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [niches, setNiches] = useState("");

  async function loadData() {
    try {
      const [cRes, aRes] = await Promise.all([
        fetchCompetitors(),
        fetchCompetitorAlerts(),
      ]);
      setCompetitors(cRes.competitors);
      setAlerts(aRes.alerts);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleScan() {
    setScanning(true);
    try {
      const res = await scanCompetitors(niches);
      toast.success(res.message || "Competitor scan complete!");
      setLoading(true);
      loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  async function handleDismiss(alertId: number) {
    try {
      await dismissCompetitorAlert(alertId);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      toast.success("Alert dismissed");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to dismiss");
    }
  }

  const threatColors: Record<string, string> = {
    high: "text-red-400 bg-red-500/20 border-red-500/30",
    medium: "text-yellow-400 bg-yellow-500/20 border-yellow-500/30",
    low: "text-emerald-400 bg-emerald-500/20 border-emerald-500/30",
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Competitor Spy</h1>
          <p className="mt-1 text-sm text-zinc-400">Monitor competitors, track price changes, and find market gaps</p>
        </div>
      </div>

      {/* Scan bar */}
      <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Eye className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-violet-300">AI Competitor Scan</span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={niches}
            onChange={e => setNiches(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleScan()}
            placeholder="Enter niches to analyze (e.g., digital planners, notion templates)..."
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
          />
          <button onClick={handleScan} disabled={scanning} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50">
            {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {scanning ? "Scanning..." : "Scan"}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-zinc-200 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
            Active Alerts ({alerts.length})
          </h2>
          {alerts.map(alert => (
            <div key={alert.id} className="rounded-xl border border-yellow-500/30 bg-yellow-500/5 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-yellow-500/20 px-2 py-0.5 text-xs font-medium text-yellow-400">{alert.alert_type}</span>
                    {alert.platform && <span className="text-xs text-zinc-500">{alert.platform}</span>}
                  </div>
                  <p className="mt-2 text-sm text-zinc-300">{alert.recommendation}</p>
                </div>
                <button onClick={() => handleDismiss(alert.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Competitors */}
      <h2 className="text-lg font-semibold text-zinc-200">Tracked Competitors ({competitors.length})</h2>
      {competitors.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Eye className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No competitors tracked yet. Run a scan to discover competitors in your niches.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {competitors.map(c => (
            <div key={c.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-zinc-200">{c.seller_name}</h3>
                <span className={`rounded border px-2 py-0.5 text-xs font-medium ${threatColors[c.threat_level] || "text-zinc-400 bg-zinc-800 border-zinc-700"}`}>
                  {c.threat_level} threat
                </span>
              </div>
              {c.platform && <p className="mt-1 text-xs text-zinc-500">{c.platform}</p>}
              {c.price_range && <p className="mt-2 text-sm text-zinc-400">Price range: {c.price_range}</p>}
              {c.strengths && (
                <div className="mt-2">
                  <span className="text-xs font-medium text-emerald-400">Strengths:</span>
                  <p className="text-xs text-zinc-400">{c.strengths}</p>
                </div>
              )}
              {c.weaknesses && (
                <div className="mt-1">
                  <span className="text-xs font-medium text-red-400">Weaknesses:</span>
                  <p className="text-xs text-zinc-400">{c.weaknesses}</p>
                </div>
              )}
              <p className="mt-2 text-xs text-zinc-600">Updated: {new Date(c.updated_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
