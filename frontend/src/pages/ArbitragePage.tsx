import { useEffect, useState } from "react";
import { ArrowRightLeft, TrendingUp, DollarSign, AlertTriangle } from "lucide-react";
import { fetchArbitrage } from "@/lib/api";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

interface ArbitrageOpportunity {
  product_id: number;
  product_name: string;
  platform_a: string;
  platform_b: string;
  price_a: string;
  price_b: string;
  price_diff: string;
  recommendation: string;
}

interface ArbitrageData {
  opportunities: ArbitrageOpportunity[];
  total_potential: number;
  products_analyzed: number;
  message: string;
}

export default function ArbitragePage() {
  const [data, setData] = useState<ArbitrageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchArbitrage()
      .then((res) => setData(res as unknown as ArbitrageData))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const opportunities = data?.opportunities || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Cross-Platform Arbitrage</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Detect pricing and performance differences across platforms to optimize revenue
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-400">Opportunities</p>
              <p className="mt-1 text-3xl font-bold text-zinc-100">{opportunities.length}</p>
            </div>
            <div className="rounded-lg bg-violet-500/20 p-3">
              <ArrowRightLeft className="h-5 w-5 text-violet-400" />
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-400">Products Analyzed</p>
              <p className="mt-1 text-3xl font-bold text-zinc-100">{data?.products_analyzed || 0}</p>
            </div>
            <div className="rounded-lg bg-blue-500/20 p-3">
              <TrendingUp className="h-5 w-5 text-blue-400" />
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-400">Revenue Potential</p>
              <p className="mt-1 text-3xl font-bold text-emerald-400">${data?.total_potential?.toFixed(2) || "0.00"}</p>
            </div>
            <div className="rounded-lg bg-emerald-500/20 p-3">
              <DollarSign className="h-5 w-5 text-emerald-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Opportunities List */}
      {opportunities.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <ArrowRightLeft className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">
            No arbitrage opportunities found yet. Add products to multiple platforms to enable cross-platform analysis.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-zinc-200">
            <AlertTriangle className="mr-2 inline h-5 w-5 text-yellow-400" />
            Pricing Opportunities
          </h2>
          <div className="overflow-hidden rounded-xl border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/80">
                <tr>
                  <th className="px-4 py-3 font-medium text-zinc-400">Product</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Platform A</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Platform B</th>
                  <th className="px-4 py-3 font-medium text-zinc-400">Difference</th>
                  <th className="hidden px-4 py-3 font-medium text-zinc-400 md:table-cell">Recommendation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {opportunities.map((opp, idx) => (
                  <tr key={idx} className="transition-colors hover:bg-zinc-900/60">
                    <td className="px-4 py-3 font-medium text-zinc-200">{opp.product_name}</td>
                    <td className="px-4 py-3">
                      <span className="text-zinc-400">{opp.platform_a}:</span>{" "}
                      <span className="font-medium text-zinc-200">${opp.price_a}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-zinc-400">{opp.platform_b}:</span>{" "}
                      <span className="font-medium text-zinc-200">${opp.price_b}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400">
                        +${opp.price_diff}
                      </span>
                    </td>
                    <td className="hidden px-4 py-3 text-zinc-400 md:table-cell">{opp.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data?.message && (
        <p className="text-sm text-zinc-500">{data.message}</p>
      )}
    </div>
  );
}
