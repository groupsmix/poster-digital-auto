import { useEffect, useState, useRef, useCallback } from "react";
import {
  BarChart3,
  DollarSign,
  Eye,
  MousePointerClick,
  ShoppingCart,
  Trophy,
  TrendingUp,
  TrendingDown,
  Award,
  Lightbulb,
  AlertTriangle,
  Target,
  Info,
  Calendar,
  Upload,
  Plus,
  X,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  fetchAnalyticsOverview,
  fetchRevenue,
  fetchPlatformPerformance,
  fetchTopProducts,
  fetchCeoTrend,
  fetchAIUsage,
  fetchInsights,
  logManualSale,
  importSalesCsv,
  fetchProducts,
} from "@/lib/api";
import type {
  AnalyticsOverview,
  RevenueDataPoint,
  PlatformPerformance,
  TopProduct,
  CeoTrendPoint,
  AIProviderUsage,
  Insight,
  Product,
} from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

const PLATFORM_COLORS: Record<string, string> = {
  Gumroad: "#FF90E8",
  Payhip: "#00B4D8",
  "Lemon Squeezy": "#FFC233",
  Reddit: "#FF4500",
  Instagram: "#E1306C",
  Twitter: "#1DA1F2",
  TikTok: "#010101",
  Facebook: "#1877F2",
  Pinterest: "#E60023",
  Telegram: "#0088CC",
  Tumblr: "#35465C",
  LinkedIn: "#0A66C2",
  Quora: "#B92B27",
  Threads: "#010101",
};

const PIE_COLORS = [
  "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
  "#ec4899", "#3b82f6", "#14b8a6", "#f97316", "#6366f1",
];

const SEVERITY_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  positive: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", icon: "text-emerald-400" },
  negative: { bg: "bg-red-500/10", border: "border-red-500/30", icon: "text-red-400" },
  warning: { bg: "bg-amber-500/10", border: "border-amber-500/30", icon: "text-amber-400" },
  info: { bg: "bg-blue-500/10", border: "border-blue-500/30", icon: "text-blue-400" },
};

function InsightIcon({ icon, className }: { icon: string; className?: string }) {
  const icons: Record<string, React.ReactNode> = {
    "trending-up": <TrendingUp className={className} />,
    "trending-down": <TrendingDown className={className} />,
    "bar-chart": <BarChart3 className={className} />,
    award: <Award className={className} />,
    calendar: <Calendar className={className} />,
    target: <Target className={className} />,
    lightbulb: <Lightbulb className={className} />,
    "alert-triangle": <AlertTriangle className={className} />,
    info: <Info className={className} />,
  };
  return <>{icons[icon] || <Info className={className} />}</>;
}

function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [revenueData, setRevenueData] = useState<RevenueDataPoint[]>([]);
  const [revenuePeriod, setRevenuePeriod] = useState("30d");
  const [platforms, setPlatforms] = useState<PlatformPerformance[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [ceoTrend, setCeoTrend] = useState<CeoTrendPoint[]>([]);
  const [aiUsage, setAiUsage] = useState<AIProviderUsage[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);

  // Manual sale modal
  const [showSaleModal, setShowSaleModal] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [saleProductId, setSaleProductId] = useState<number>(0);
  const [salePlatform, setSalePlatform] = useState("");
  const [saleRevenue, setSaleRevenue] = useState("");
  const [saleDate, setSaleDate] = useState("");
  const [submittingSale, setSubmittingSale] = useState(false);

  // CSV import
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchAnalyticsOverview(),
      fetchRevenue(revenuePeriod),
      fetchPlatformPerformance(),
      fetchTopProducts(),
      fetchCeoTrend(),
      fetchAIUsage(),
      fetchInsights(),
    ])
      .then(([ov, rev, plat, top, ceo, ai, ins]) => {
        setOverview(ov);
        setRevenueData(rev.data);
        setPlatforms(plat.platforms);
        setTopProducts(top.products);
        setCeoTrend(ceo.trend);
        setAiUsage(ai.providers);
        setInsights(ins.insights);
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [revenuePeriod]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  function openSaleModal() {
    fetchProducts()
      .then((data) => {
        setProducts(data.products);
        setShowSaleModal(true);
      })
      .catch((e) => toast.error(e.message));
  }

  async function handleLogSale() {
    if (!saleProductId || !salePlatform || !saleRevenue) {
      toast.error("Fill in all required fields");
      return;
    }
    setSubmittingSale(true);
    try {
      await logManualSale({
        product_id: saleProductId,
        platform: salePlatform,
        revenue: parseFloat(saleRevenue),
        date: saleDate || undefined,
      });
      toast.success("Sale logged!");
      setShowSaleModal(false);
      setSaleProductId(0);
      setSalePlatform("");
      setSaleRevenue("");
      setSaleDate("");
      loadAll();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to log sale";
      toast.error(msg);
    } finally {
      setSubmittingSale(false);
    }
  }

  async function handleCsvImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importSalesCsv(file);
      toast.success(result.message);
      if (result.errors.length > 0) {
        toast.warning(`${result.errors.length} rows had errors`);
      }
      loadAll();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Import failed";
      toast.error(msg);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-violet-400" />
            Analytics Dashboard
          </h1>
          <p className="text-sm text-zinc-400">
            Track product performance, revenue, and insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleCsvImport}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-700 transition-colors disabled:opacity-50"
          >
            <Upload className="h-4 w-4 text-blue-400" />
            {importing ? "Importing..." : "Import CSV"}
          </button>
          <button
            onClick={openSaleModal}
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-500 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Log Sale
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="rounded-lg bg-emerald-500/10 p-2">
                <DollarSign className="h-5 w-5 text-emerald-400" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Net Revenue
              </span>
            </div>
            <p className="text-2xl font-bold text-emerald-400">
              {formatCurrency(overview.net_revenue)}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              {overview.total_sales} sales &middot; {formatCurrency(overview.total_refunds)} refunds
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="rounded-lg bg-blue-500/10 p-2">
                <ShoppingCart className="h-5 w-5 text-blue-400" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Products
              </span>
            </div>
            <p className="text-2xl font-bold text-blue-400">
              {overview.products_created}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              {overview.total_views} views &middot; {overview.total_clicks} clicks
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="rounded-lg bg-violet-500/10 p-2">
                <Trophy className="h-5 w-5 text-violet-400" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Best Platform
              </span>
            </div>
            <p className="text-2xl font-bold text-violet-400">
              {overview.best_platform}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              {formatCurrency(overview.best_platform_revenue)} revenue
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="rounded-lg bg-amber-500/10 p-2">
                <Award className="h-5 w-5 text-amber-400" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Avg CEO Score
              </span>
            </div>
            <p className="text-2xl font-bold text-amber-400">
              {overview.avg_ceo_score}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              {overview.approval_rate}% approval rate
            </p>
          </div>
        </div>
      )}

      {/* AI Insights Panel */}
      {insights.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-400" />
            AI Insights
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {insights.map((insight, idx) => {
              const style = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;
              return (
                <div
                  key={idx}
                  className={`rounded-lg border p-3 ${style.bg} ${style.border}`}
                >
                  <div className="flex items-start gap-2.5">
                    <InsightIcon icon={insight.icon} className={`h-5 w-5 shrink-0 mt-0.5 ${style.icon}`} />
                    <p className="text-sm text-zinc-200">{insight.message}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Revenue Chart */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            Revenue Over Time
          </h2>
          <div className="flex gap-1">
            {["7d", "30d", "90d", "all"].map((p) => (
              <button
                key={p}
                onClick={() => setRevenuePeriod(p)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  revenuePeriod === p
                    ? "bg-violet-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
              >
                {p === "all" ? "All" : p}
              </button>
            ))}
          </div>
        </div>
        {revenueData.length === 0 ? (
          <p className="text-sm text-zinc-500 py-8 text-center">
            No revenue data yet. Log sales to see the chart.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis
                dataKey="date"
                stroke="#71717a"
                fontSize={12}
                tickFormatter={(v) => {
                  const d = new Date(v + "T00:00:00");
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
              />
              <YAxis stroke="#71717a" fontSize={12} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#18181b",
                  border: "1px solid #3f3f46",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [
                  name === "revenue" ? formatCurrency(value) : value,
                  name === "revenue" ? "Revenue" : name === "sale_count" ? "Sales" : name,
                ]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Revenue"
              />
              <Line
                type="monotone"
                dataKey="sale_count"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                name="Sales"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Two-column: Platform Comparison + AI Provider Usage */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Platform Comparison */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-400" />
            Platform Revenue
          </h2>
          {platforms.length === 0 ? (
            <p className="text-sm text-zinc-500 py-8 text-center">No platform data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={platforms} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis type="number" stroke="#71717a" fontSize={12} tickFormatter={(v) => `$${v}`} />
                <YAxis type="category" dataKey="platform" stroke="#71717a" fontSize={12} width={90} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    border: "1px solid #3f3f46",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value: number) => [formatCurrency(value), "Revenue"]}
                />
                <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                  {platforms.map((entry, index) => (
                    <Cell
                      key={entry.platform}
                      fill={PLATFORM_COLORS[entry.platform] || PIE_COLORS[index % PIE_COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* AI Provider Usage */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="h-5 w-5 text-violet-400" />
            AI Provider Usage
          </h2>
          {aiUsage.length === 0 ? (
            <p className="text-sm text-zinc-500 py-8 text-center">No AI usage data yet.</p>
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={250}>
                <PieChart>
                  <Pie
                    data={aiUsage}
                    dataKey="usage_count"
                    nameKey="provider"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    innerRadius={50}
                  >
                    {aiUsage.map((_entry, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#18181b",
                      border: "1px solid #3f3f46",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {aiUsage.map((p, i) => (
                  <div key={p.provider} className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-full shrink-0"
                      style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                    />
                    <span className="text-xs text-zinc-300 truncate flex-1">{p.provider}</span>
                    <span className="text-xs text-zinc-500">{p.usage_count}</span>
                    <span className="text-xs text-emerald-400">{p.success_rate}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Top Products Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Trophy className="h-5 w-5 text-amber-400" />
          Top Products by Revenue
        </h2>
        {topProducts.length === 0 ? (
          <p className="text-sm text-zinc-500 py-8 text-center">
            No product revenue data yet. Log sales to see rankings.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-left">
                  <th className="pb-3 pr-4 font-medium text-zinc-400">#</th>
                  <th className="pb-3 pr-4 font-medium text-zinc-400">Product</th>
                  <th className="pb-3 pr-4 font-medium text-zinc-400">Status</th>
                  <th className="pb-3 pr-4 font-medium text-zinc-400 text-right">Revenue</th>
                  <th className="pb-3 pr-4 font-medium text-zinc-400 text-right">Sales</th>
                  <th className="pb-3 font-medium text-zinc-400 text-right">Views</th>
                </tr>
              </thead>
              <tbody>
                {topProducts.map((p, idx) => (
                  <tr key={p.product_id} className="border-b border-zinc-800/50">
                    <td className="py-3 pr-4 text-zinc-500">{idx + 1}</td>
                    <td className="py-3 pr-4">
                      <span className="font-medium text-zinc-200">{p.name}</span>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-right font-medium text-emerald-400">
                      {formatCurrency(p.revenue)}
                    </td>
                    <td className="py-3 pr-4 text-right text-zinc-300">{p.sales}</td>
                    <td className="py-3 text-right text-zinc-400">{p.views}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CEO Score Trend */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Award className="h-5 w-5 text-amber-400" />
          CEO Approval Trend
        </h2>
        <p className="text-xs text-zinc-500 mb-3">
          Are your products getting better over time?
        </p>
        {ceoTrend.length === 0 ? (
          <p className="text-sm text-zinc-500 py-8 text-center">
            No CEO review data yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={ceoTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis
                dataKey="date"
                stroke="#71717a"
                fontSize={12}
                tickFormatter={(v) => {
                  const d = new Date(v + "T00:00:00");
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
              />
              <YAxis stroke="#71717a" fontSize={12} domain={[0, 10]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#18181b",
                  border: "1px solid #3f3f46",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="avg_score"
                stroke="#f59e0b"
                strokeWidth={2}
                dot
                name="Avg CEO Score"
              />
              <Line
                type="monotone"
                dataKey="approval_rate"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Approval Rate %"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Platform Detail Cards */}
      {platforms.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-400" />
            Platform Details
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {platforms.map((p) => (
              <div
                key={p.platform}
                className="rounded-lg border border-zinc-800 p-4"
                style={{ borderLeftWidth: "3px", borderLeftColor: PLATFORM_COLORS[p.platform] || "#6b7280" }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className="rounded px-2 py-0.5 text-xs font-semibold"
                    style={{
                      backgroundColor: `${PLATFORM_COLORS[p.platform] || "#6b7280"}20`,
                      color: PLATFORM_COLORS[p.platform] || "#6b7280",
                    }}
                  >
                    {p.platform}
                  </span>
                  <span className="text-sm font-bold text-emerald-400">
                    {formatCurrency(p.revenue)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <Eye className="h-3.5 w-3.5 mx-auto text-zinc-500 mb-0.5" />
                    <p className="text-xs text-zinc-400">{p.views}</p>
                    <p className="text-xs text-zinc-600">views</p>
                  </div>
                  <div>
                    <MousePointerClick className="h-3.5 w-3.5 mx-auto text-zinc-500 mb-0.5" />
                    <p className="text-xs text-zinc-400">{p.clicks}</p>
                    <p className="text-xs text-zinc-600">clicks</p>
                  </div>
                  <div>
                    <ShoppingCart className="h-3.5 w-3.5 mx-auto text-zinc-500 mb-0.5" />
                    <p className="text-xs text-zinc-400">{p.sales}</p>
                    <p className="text-xs text-zinc-600">sales</p>
                  </div>
                </div>
                {p.conversion_rate > 0 && (
                  <p className="text-xs text-zinc-500 mt-2 text-center">
                    {p.conversion_rate}% conversion &middot; {p.posts} posts
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Manual Sale Modal */}
      {showSaleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-emerald-400" />
                Log Manual Sale
              </h3>
              <button
                onClick={() => setShowSaleModal(false)}
                className="rounded p-1 text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-xs text-zinc-500 mb-4">
              For Gumroad/Payhip sales without real-time API tracking.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Product</label>
                <select
                  value={saleProductId}
                  onChange={(e) => setSaleProductId(Number(e.target.value))}
                  className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                >
                  <option value={0}>Select a product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Platform</label>
                <select
                  value={salePlatform}
                  onChange={(e) => setSalePlatform(e.target.value)}
                  className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                >
                  <option value="">Select platform...</option>
                  {["Gumroad", "Payhip", "Lemon Squeezy"].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Revenue ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={saleRevenue}
                    onChange={(e) => setSaleRevenue(e.target.value)}
                    placeholder="9.99"
                    className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Date (optional)</label>
                  <input
                    type="date"
                    value={saleDate}
                    onChange={(e) => setSaleDate(e.target.value)}
                    className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  onClick={() => setShowSaleModal(false)}
                  className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleLogSale}
                  disabled={submittingSale || !saleProductId || !salePlatform || !saleRevenue}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {submittingSale ? <Spinner className="h-4 w-4" /> : "Log Sale"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
