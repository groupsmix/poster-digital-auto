import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FlaskConical, Trophy, Lightbulb, RefreshCw } from "lucide-react";
import { fetchABTests, fetchABPatterns, detectABWinner, recordABSale } from "@/lib/api";
import type { ABTest, ABPattern } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function ABTestsPage() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [patterns, setPatterns] = useState<ABPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");
  const [saleModal, setSaleModal] = useState<{ testId: number; variantId: number } | null>(null);
  const [saleRevenue, setSaleRevenue] = useState("");

  useEffect(() => {
    loadData();
  }, [filter]);

  async function loadData() {
    setLoading(true);
    try {
      const [testsRes, patternsRes] = await Promise.all([
        fetchABTests(filter || undefined),
        fetchABPatterns(),
      ]);
      setTests(testsRes.tests);
      setPatterns(patternsRes.patterns);
    } catch {
      toast.error("Failed to load A/B tests");
    } finally {
      setLoading(false);
    }
  }

  async function handleDetectWinner(testId: number) {
    try {
      const res = await detectABWinner(testId);
      if (res.winner_detected) {
        toast.success(`Winner detected: Variant #${res.winner}`);
      } else {
        toast.info("Not enough data to detect a winner yet");
      }
      loadData();
    } catch {
      toast.error("Failed to detect winner");
    }
  }

  async function handleRecordSale() {
    if (!saleModal || !saleRevenue) return;
    try {
      await recordABSale(saleModal.testId, saleModal.variantId, parseFloat(saleRevenue));
      toast.success("Sale recorded!");
      setSaleModal(null);
      setSaleRevenue("");
      loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to record sale");
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
      {/* Sale Modal */}
      {saleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 w-full max-w-sm rounded-xl border border-zinc-700 bg-zinc-900 p-6">
            <h3 className="text-lg font-bold text-zinc-100">Record Sale</h3>
            <p className="mt-1 text-sm text-zinc-400">Variant #{saleModal.variantId}</p>
            <input
              type="number"
              step="0.01"
              placeholder="Revenue amount"
              value={saleRevenue}
              onChange={(e) => setSaleRevenue(e.target.value)}
              className="mt-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={handleRecordSale}
                disabled={!saleRevenue}
                className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                Record
              </button>
              <button
                onClick={() => { setSaleModal(null); setSaleRevenue(""); }}
                className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold">A/B Tests</h1>
        <p className="mt-1 text-zinc-400">Compare variant performance and discover winning patterns</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        {["", "running", "completed"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              filter === f
                ? "border-violet-500 bg-violet-500/20 text-violet-300"
                : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
            }`}
          >
            {f === "" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <button
          onClick={loadData}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Patterns */}
      {patterns.length > 0 && (
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-cyan-300">
            <Lightbulb className="h-4 w-4" />
            Learned Patterns
          </h3>
          <div className="space-y-2">
            {patterns.map((p, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full bg-cyan-400" />
                <div>
                  <p className="text-sm font-medium text-zinc-200">{p.pattern}</p>
                  <p className="text-xs text-zinc-400">{p.detail}</p>
                </div>
                {p.confidence > 0 && (
                  <span className="ml-auto flex-shrink-0 rounded bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-300">
                    {p.confidence}% confidence
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tests List */}
      {tests.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <FlaskConical className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No A/B tests yet.</p>
          <p className="mt-1 text-sm text-zinc-500">
            Go to a product&apos;s Copy Center and click &ldquo;A/B Test&rdquo; on any variant to start.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {tests.map((test) => (
            <div key={test.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <div className="flex flex-wrap items-center gap-3 border-b border-zinc-800 pb-4">
                <FlaskConical className="h-5 w-5 text-violet-400" />
                <div className="flex-1">
                  <h3 className="font-semibold text-zinc-200">{test.test_name}</h3>
                  <Link
                    to={`/products/${test.product_id}`}
                    className="text-xs text-violet-400 hover:text-violet-300"
                  >
                    {test.product_name} &rarr;
                  </Link>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    test.status === "running"
                      ? "bg-blue-500/20 text-blue-300"
                      : "bg-emerald-500/20 text-emerald-300"
                  }`}
                >
                  {test.status}
                </span>
                {test.status === "running" && (
                  <button
                    onClick={() => handleDetectWinner(test.id)}
                    className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500"
                  >
                    <Trophy className="h-3 w-3" />
                    Check Winner
                  </button>
                )}
              </div>

              {/* Variants comparison */}
              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                {test.variants.map((v) => {
                  const isWinner = test.winner_id === v.id;
                  return (
                    <div
                      key={v.id}
                      className={`rounded-lg border p-4 ${
                        isWinner
                          ? "border-emerald-500 bg-emerald-500/10"
                          : "border-zinc-700 bg-zinc-800/50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-violet-500/20 px-1.5 py-0.5 text-xs font-bold text-violet-300">
                          {v.ab_variant || "?"}
                        </span>
                        {isWinner && (
                          <Trophy className="h-4 w-4 text-emerald-400" />
                        )}
                      </div>
                      <p className="mt-2 text-sm font-medium text-zinc-200 line-clamp-2">
                        {v.title || "No title"}
                      </p>
                      <p className="mt-1 text-xs text-zinc-400 line-clamp-2">
                        {v.description?.slice(0, 100) || "No description"}
                      </p>

                      {/* Metrics */}
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        <div className="rounded bg-zinc-800 px-2 py-1.5 text-center">
                          <p className="text-sm font-bold text-zinc-200">{v.sales_count}</p>
                          <p className="text-[10px] text-zinc-500">Sales</p>
                        </div>
                        <div className="rounded bg-zinc-800 px-2 py-1.5 text-center">
                          <p className="text-sm font-bold text-emerald-300">${v.sales_revenue.toFixed(2)}</p>
                          <p className="text-[10px] text-zinc-500">Revenue</p>
                        </div>
                        <div className="rounded bg-zinc-800 px-2 py-1.5 text-center">
                          <p className="text-sm font-bold text-zinc-200">{v.views_count}</p>
                          <p className="text-[10px] text-zinc-500">Views</p>
                        </div>
                        <div className="rounded bg-zinc-800 px-2 py-1.5 text-center">
                          <p className="text-sm font-bold text-zinc-200">{v.conversion_rate}%</p>
                          <p className="text-[10px] text-zinc-500">Conv.</p>
                        </div>
                      </div>

                      {test.status === "running" && (
                        <button
                          onClick={() => setSaleModal({ testId: test.id, variantId: v.id })}
                          className="mt-3 w-full rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600"
                        >
                          + Record Sale
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              <p className="mt-3 text-xs text-zinc-600">
                Started: {new Date(test.started_at).toLocaleString()}
                {test.ended_at && ` | Ended: ${new Date(test.ended_at).toLocaleString()}`}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
