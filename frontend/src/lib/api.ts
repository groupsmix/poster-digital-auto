import type {
  Product, ProductCreate, Stats, AIProvider, SocialPost, AutoPostConfig,
  AnalyticsOverview, RevenueDataPoint, PlatformPerformance, TopProduct,
  CeoTrendPoint, AIProviderUsage, Insight,
  CalendarPost, ScheduleSuggestion,
  NicheIdea, TrendPrediction,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  return request<Stats>("/api/stats");
}

export async function fetchProducts(status?: string): Promise<{ products: Product[]; count: number }> {
  const query = status ? `?status=${status}` : "";
  return request(`/api/products${query}`);
}

export async function fetchProduct(id: number): Promise<Product> {
  return request<Product>(`/api/products/${id}`);
}

export async function createProduct(data: ProductCreate): Promise<Product> {
  return request<Product>("/api/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteProduct(id: number): Promise<{ message: string }> {
  return request(`/api/products/${id}`, { method: "DELETE" });
}

export async function generateProduct(id: number): Promise<unknown> {
  return request(`/api/products/${id}/generate`, { method: "POST" });
}

export async function fetchAIStatus(): Promise<{ providers: AIProvider[]; count: number }> {
  return request("/api/ai-status");
}

export async function resetAILimits(): Promise<{ message: string }> {
  return request("/api/ai-status/reset", { method: "POST" });
}

// Social Posts
export async function fetchSocialPosts(filters?: {
  product_id?: number;
  platform?: string;
  post_status?: string;
}): Promise<{ posts: SocialPost[]; count: number }> {
  const params = new URLSearchParams();
  if (filters?.product_id) params.set("product_id", String(filters.product_id));
  if (filters?.platform) params.set("platform", filters.platform);
  if (filters?.post_status) params.set("post_status", filters.post_status);
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/social-posts${query}`);
}

export async function updateSocialPost(
  id: number,
  data: { caption?: string; post_status?: string },
): Promise<SocialPost> {
  return request<SocialPost>(`/api/social-posts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function triggerAutoPost(id: number): Promise<{ success: boolean; message: string; post_url: string; platform: string }> {
  return request(`/api/social-posts/${id}/post`, { method: "POST" });
}

export async function generateCaptions(productId: number): Promise<unknown> {
  return request(`/api/products/${productId}/captions`, { method: "POST" });
}

export async function fetchAutoPostConfig(): Promise<AutoPostConfig> {
  return request<AutoPostConfig>("/api/auto-post/config");
}

// Analytics
export async function fetchAnalyticsOverview(): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>("/api/analytics/overview");
}

export async function fetchRevenue(period: string = "30d"): Promise<{ period: string; data: RevenueDataPoint[]; count: number }> {
  return request(`/api/analytics/revenue?period=${encodeURIComponent(period)}`);
}

export async function fetchPlatformPerformance(): Promise<{ platforms: PlatformPerformance[]; count: number }> {
  return request("/api/analytics/platforms");
}

export async function fetchTopProducts(limit: number = 10): Promise<{ products: TopProduct[] }> {
  return request(`/api/analytics/top-products?limit=${limit}`);
}

export async function fetchCeoTrend(): Promise<{ trend: CeoTrendPoint[] }> {
  return request("/api/analytics/ceo-trend");
}

export async function fetchAIUsage(): Promise<{ providers: AIProviderUsage[] }> {
  return request("/api/analytics/ai-usage");
}

export async function fetchInsights(): Promise<{ insights: Insight[] }> {
  return request("/api/analytics/insights");
}

export async function logManualSale(data: {
  product_id: number;
  platform: string;
  revenue: number;
  date?: string;
}): Promise<Record<string, unknown>> {
  return request("/api/analytics/manual-sale", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function importSalesCsv(file: File): Promise<{ imported: number; errors: string[]; message: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const res = await fetch(`${API}/api/analytics/import-csv`, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// Calendar & Scheduler
export async function fetchCalendarPosts(start: string, end: string): Promise<{ posts: CalendarPost[]; count: number }> {
  return request(`/api/calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
}

export async function schedulePost(postId: number, scheduledAt: string): Promise<CalendarPost> {
  return request<CalendarPost>("/api/calendar/schedule", {
    method: "POST",
    body: JSON.stringify({ post_id: postId, scheduled_at: scheduledAt }),
  });
}

export async function reschedulePost(postId: number, scheduledAt: string): Promise<CalendarPost> {
  return request<CalendarPost>(`/api/calendar/${postId}`, {
    method: "PATCH",
    body: JSON.stringify({ scheduled_at: scheduledAt }),
  });
}

export async function unschedulePost(postId: number): Promise<{ message: string }> {
  return request(`/api/calendar/${postId}`, { method: "DELETE" });
}

export async function fetchScheduleSuggestions(platform?: string): Promise<{ suggestions: ScheduleSuggestion[]; count: number }> {
  const query = platform ? `?platform=${encodeURIComponent(platform)}` : "";
  return request(`/api/calendar/suggestions${query}`);
}

export async function autoSchedulePosts(body: {
  post_ids?: number[];
  start_date?: string;
  days_span?: number;
  posts_per_day?: number;
}): Promise<{ scheduled: CalendarPost[]; count: number; message: string }> {
  return request("/api/calendar/auto-schedule", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function batchScheduleProducts(body: {
  product_ids: number[];
  start_date?: string;
  days_span?: number;
  posts_per_day?: number;
}): Promise<{ scheduled: CalendarPost[]; count: number; message: string }> {
  return request("/api/calendar/batch-schedule", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchPlatformColors(): Promise<Record<string, string>> {
  return request("/api/calendar/platform-colors");
}

// Niche Finder
export async function scanNiches(): Promise<{ success: boolean; ideas: NicheIdea[]; scan_summary: string; message: string }> {
  return request("/api/niches/scan", { method: "POST" });
}

export async function fetchNiches(status?: string, sortBy?: string): Promise<{ ideas: NicheIdea[]; count: number }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (sortBy) params.set("sort_by", sortBy);
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/niches${query}`);
}

export async function createProductFromNiche(nicheId: number): Promise<{ success: boolean; product_id: number; message: string }> {
  return request(`/api/niches/${nicheId}/create`, { method: "POST" });
}

export async function updateNicheStatus(nicheId: number, status: string): Promise<NicheIdea> {
  return request<NicheIdea>(`/api/niches/${nicheId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// Trend Predictor
export async function scanTrends(): Promise<{ success: boolean; predictions: TrendPrediction[]; scan_summary: string; message: string }> {
  return request("/api/trends/scan", { method: "POST" });
}

export async function fetchTrends(status?: string): Promise<{ predictions: TrendPrediction[]; count: number }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/trends${query}`);
}

export async function fetchTrendAlerts(): Promise<{ alerts: TrendPrediction[]; count: number }> {
  return request("/api/trends/alerts");
}

export async function createProductFromTrend(trendId: number): Promise<{ success: boolean; product_id: number; message: string }> {
  return request(`/api/trends/${trendId}/create`, { method: "POST" });
}
