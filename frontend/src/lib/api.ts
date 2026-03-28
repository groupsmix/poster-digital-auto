import type {
  Product, ProductCreate, Stats, AIProvider, SocialPost, AutoPostConfig,
  AnalyticsOverview, RevenueDataPoint, PlatformPerformance, TopProduct,
  CeoTrendPoint, AIProviderUsage, Insight,
  CalendarPost, ScheduleSuggestion,
  RemixResult,
  NicheIdea, TrendPrediction,
  ABTest, ABTestResult, ABPattern,
  PriceSuggestions, LaunchPricing, BundlePricing,
  EmailCampaign, EmailCampaignResult,
  RevenueGoal,
  RepurposedContent, RepurposeResult, VoiceOverResult,
  FAQEntry, FAQSuggestion,
  PlatformSetting, CustomerPersona, APIKeyStatus, SettingsPreferences,
  ProductTemplate, ProductBundle,
  Competitor, CompetitorAlert,
  Affiliate, ReferralLink,
  PiracyProtection, DMCARequest,
  WhiteLabelTenant, WhiteLabelTier,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://204.168.141.220";

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
  const API = import.meta.env.VITE_API_URL || "http://204.168.141.220";
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

// Remix Engine
export async function remixProduct(productId: number, remixTypes?: string[]): Promise<RemixResult> {
  return request<RemixResult>(`/api/products/${productId}/remix`, {
    method: "POST",
    body: JSON.stringify({ remix_types: remixTypes || null }),
  });
}

export async function fetchRemixChildren(productId: number): Promise<{ children: Product[]; count: number }> {
  return request(`/api/products/${productId}/children`);
}

// A/B Testing
export async function createABTest(variantId: number): Promise<ABTestResult> {
  return request<ABTestResult>(`/api/variants/${variantId}/ab-test`, { method: "POST" });
}

export async function fetchABTests(status?: string): Promise<{ tests: ABTest[]; count: number }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/ab-tests${query}`);
}

export async function recordABSale(testId: number, variantId: number, revenue: number): Promise<Record<string, unknown>> {
  return request(`/api/ab-tests/${testId}/sale`, {
    method: "POST",
    body: JSON.stringify({ variant_id: variantId, revenue }),
  });
}

export async function detectABWinner(testId: number): Promise<Record<string, unknown>> {
  return request(`/api/ab-tests/${testId}/detect-winner`, { method: "POST" });
}

export async function fetchABPatterns(): Promise<{ patterns: ABPattern[]; count: number }> {
  return request("/api/ab-tests/patterns");
}

// Smart Pricing
export async function fetchPriceSuggestions(productId: number): Promise<PriceSuggestions> {
  return request<PriceSuggestions>(`/api/products/${productId}/pricing`);
}

export async function calculateLaunchPricing(
  regularPrice: number,
  discountPercent: number = 40,
  durationHours: number = 48,
): Promise<LaunchPricing> {
  return request<LaunchPricing>("/api/pricing/launch", {
    method: "POST",
    body: JSON.stringify({ regular_price: regularPrice, discount_percent: discountPercent, duration_hours: durationHours }),
  });
}

export async function calculateBundlePricing(
  prices: number[],
  discountPercent: number = 25,
): Promise<BundlePricing> {
  return request<BundlePricing>("/api/pricing/bundle", {
    method: "POST",
    body: JSON.stringify({ prices, discount_percent: discountPercent }),
  });
}

// Email Marketing
export async function generateEmailCampaign(productId: number): Promise<EmailCampaignResult> {
  return request<EmailCampaignResult>(`/api/products/${productId}/email`, { method: "POST" });
}

export async function fetchEmailCampaign(productId: number): Promise<EmailCampaign> {
  return request<EmailCampaign>(`/api/products/${productId}/email`);
}

// Revenue Goals
export async function createRevenueGoal(targetAmount: number, period: string = "monthly"): Promise<{ success: boolean; goal: RevenueGoal; message: string }> {
  return request("/api/goals", {
    method: "POST",
    body: JSON.stringify({ target_amount: targetAmount, period }),
  });
}

export async function fetchGoals(): Promise<{ goals: RevenueGoal[]; active_goal: RevenueGoal | null; count: number }> {
  return request("/api/goals");
}

export async function refreshGoals(): Promise<{ updated: RevenueGoal[]; count: number }> {
  return request("/api/goals/refresh", { method: "POST" });
}

// Content Repurposing
export async function repurposeProduct(productId: number): Promise<RepurposeResult> {
  return request<RepurposeResult>(`/api/products/${productId}/repurpose`, { method: "POST" });
}

export async function fetchRepurposedContent(productId: number): Promise<{ content: RepurposedContent[]; count: number }> {
  return request(`/api/products/${productId}/repurpose`);
}

// Voice-Over
export async function generateVoiceover(productId: number): Promise<VoiceOverResult> {
  return request<VoiceOverResult>(`/api/products/${productId}/voiceover`, { method: "POST" });
}

// FAQ Bot
export async function createFAQ(question: string, answer: string, category: string = "general"): Promise<{ success: boolean; faq: FAQEntry; message: string }> {
  return request("/api/faq", {
    method: "POST",
    body: JSON.stringify({ question, answer, category }),
  });
}

export async function fetchFAQs(category?: string, search?: string): Promise<{ faqs: FAQEntry[]; count: number }> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/faq${query}`);
}

export async function updateFAQEntry(id: number, data: { question?: string; answer?: string; category?: string }): Promise<FAQEntry> {
  return request<FAQEntry>(`/api/faq/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteFAQEntry(id: number): Promise<{ message: string }> {
  return request(`/api/faq/${id}`, { method: "DELETE" });
}

export async function suggestFAQAnswer(question: string): Promise<FAQSuggestion> {
  return request<FAQSuggestion>("/api/faq/suggest", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

// Settings - Platform Management
export async function fetchPlatformSettings(): Promise<{ platforms: PlatformSetting[] }> {
  return request("/api/settings/platforms");
}

export async function createPlatformSetting(data: {
  name: string;
  type: string;
  tone: string;
  plan_mode: string;
  max_title_length: number;
  max_description_length: number;
  custom_instructions: string;
  enabled: boolean;
}): Promise<PlatformSetting> {
  return request<PlatformSetting>("/api/settings/platforms", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePlatformSetting(
  id: number,
  data: Partial<{
    tone: string;
    plan_mode: string;
    enabled: boolean;
    max_title_length: number;
    max_description_length: number;
    custom_instructions: string;
    type: string;
  }>,
): Promise<PlatformSetting> {
  return request<PlatformSetting>(`/api/settings/platforms/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deletePlatformSetting(id: number): Promise<{ message: string }> {
  return request(`/api/settings/platforms/${id}`, { method: "DELETE" });
}

// Settings - Customer Personas
export async function fetchPersonas(): Promise<{ personas: CustomerPersona[]; count: number }> {
  return request("/api/settings/personas");
}

export async function createPersona(data: {
  name: string;
  age_range: string;
  description: string;
  preferences: Record<string, unknown>;
  platforms: string[];
}): Promise<CustomerPersona> {
  return request<CustomerPersona>("/api/settings/personas", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePersona(
  id: number,
  data: Partial<{
    name: string;
    age_range: string;
    description: string;
    preferences: Record<string, unknown>;
    platforms: string[];
  }>,
): Promise<CustomerPersona> {
  return request<CustomerPersona>(`/api/settings/personas/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deletePersona(id: number): Promise<{ message: string }> {
  return request(`/api/settings/personas/${id}`, { method: "DELETE" });
}

// Settings - Preferences
export async function fetchPreferences(): Promise<{ preferences: SettingsPreferences }> {
  return request("/api/settings/preferences");
}

export async function updatePreference(key: string, value: unknown): Promise<{ key: string; value: unknown }> {
  return request("/api/settings/preferences", {
    method: "PATCH",
    body: JSON.stringify({ key, value }),
  });
}

// Settings - API Key Status
export async function fetchAPIKeyStatus(): Promise<{ api_keys: APIKeyStatus[]; configured_count: number; total_count: number }> {
  return request("/api/settings/api-keys");
}

// Product Templates
export async function fetchTemplates(): Promise<{ templates: ProductTemplate[]; count: number }> {
  return request("/api/templates");
}

export async function createTemplate(data: {
  name: string;
  product_type?: string;
  tone?: string;
  keywords?: string[];
  price_min?: number;
  price_max?: number;
  platforms?: string[];
  languages?: string[];
  brief_template?: string;
  seasonal_tag?: string;
  auto_activate_month?: number | null;
}): Promise<ProductTemplate> {
  return request<ProductTemplate>("/api/templates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTemplate(id: number, data: Partial<{
  name: string;
  product_type: string;
  tone: string;
  keywords: string[];
  price_min: number;
  price_max: number;
  platforms: string[];
  languages: string[];
  brief_template: string;
  seasonal_tag: string;
  auto_activate_month: number | null;
}>): Promise<ProductTemplate> {
  return request<ProductTemplate>(`/api/templates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTemplate(id: number): Promise<{ message: string }> {
  return request(`/api/templates/${id}`, { method: "DELETE" });
}

export async function createProductFromTemplate(templateId: number, productName: string): Promise<{ success: boolean; product_id: number; message: string }> {
  return request(`/api/templates/${templateId}/create-product`, {
    method: "POST",
    body: JSON.stringify({ product_name: productName }),
  });
}

// Product Bundles
export async function fetchBundles(): Promise<{ bundles: ProductBundle[]; count: number }> {
  return request("/api/bundles");
}

export async function createBundle(data: {
  name: string;
  product_ids: number[];
  discount_percent?: number;
  seasonal_tag?: string;
  auto_activate_month?: number | null;
}): Promise<{ success: boolean; bundle: ProductBundle; message: string }> {
  return request("/api/bundles", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteBundle(id: number): Promise<{ message: string }> {
  return request(`/api/bundles/${id}`, { method: "DELETE" });
}

export async function generateBundleListing(bundleId: number): Promise<{ success: boolean; listing: Record<string, unknown>; message: string }> {
  return request(`/api/bundles/${bundleId}/generate-listing`, { method: "POST" });
}

// Competitor Spy
export async function scanCompetitors(niches?: string): Promise<{ success: boolean; competitors: Competitor[]; alerts: CompetitorAlert[]; message: string }> {
  return request("/api/competitors/scan", {
    method: "POST",
    body: JSON.stringify({ niches: niches || "" }),
  });
}

export async function fetchCompetitors(platform?: string): Promise<{ competitors: Competitor[]; count: number }> {
  const query = platform ? `?platform=${encodeURIComponent(platform)}` : "";
  return request(`/api/competitors${query}`);
}

export async function fetchCompetitorAlerts(alertType?: string): Promise<{ alerts: CompetitorAlert[]; count: number }> {
  const query = alertType ? `?alert_type=${encodeURIComponent(alertType)}` : "";
  return request(`/api/competitors/alerts${query}`);
}

export async function dismissCompetitorAlert(alertId: number): Promise<{ message: string }> {
  return request(`/api/competitors/alerts/${alertId}/dismiss`, { method: "POST" });
}

// Cross-Platform Arbitrage
export async function fetchArbitrage(): Promise<Record<string, unknown>> {
  return request("/api/arbitrage");
}

// Upsell & Cross-sell
export async function fetchRecommendations(productId: number, limit?: number): Promise<Record<string, unknown>> {
  const query = limit ? `?limit=${limit}` : "";
  return request(`/api/products/${productId}/recommendations${query}`);
}

export async function fetchFrequentlyBought(productId: number): Promise<{ related_products: Record<string, unknown>[]; count: number }> {
  return request(`/api/products/${productId}/frequently-bought`);
}

// Email - Brevo Integration
export async function fetchBrevoStatus(): Promise<Record<string, unknown>> {
  return request("/api/email/status");
}

export async function sendCampaignEmail(campaignId: number, data: {
  email_type: string;
  to_email: string;
  to_name?: string;
}): Promise<{ success: boolean; message: string }> {
  return request(`/api/email/campaigns/${campaignId}/send`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function scheduleCampaignSequence(campaignId: number, data: {
  to_email: string;
  to_name?: string;
}): Promise<{ success: boolean; message: string }> {
  return request(`/api/email/campaigns/${campaignId}/schedule`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// AI Personas
export async function generateAIPersonas(count?: number): Promise<{ success: boolean; personas: CustomerPersona[]; message: string }> {
  const query = count ? `?count=${count}` : "";
  return request(`/api/personas/generate${query}`, { method: "POST" });
}

// Affiliate & Referral System
export async function fetchAffiliates(status?: string): Promise<{ affiliates: Affiliate[]; count: number }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/affiliates${query}`);
}

export async function createAffiliate(data: {
  name: string;
  email?: string;
  commission_rate?: number;
  notes?: string;
}): Promise<Affiliate> {
  return request<Affiliate>("/api/affiliates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAffiliate(id: number, data: Partial<{
  name: string;
  email: string;
  commission_rate: number;
  notes: string;
  status: string;
}>): Promise<Affiliate> {
  return request<Affiliate>(`/api/affiliates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAffiliate(id: number): Promise<{ message: string }> {
  return request(`/api/affiliates/${id}`, { method: "DELETE" });
}

export async function createReferralLink(affiliateId: number, productId: number): Promise<{ success: boolean; link: ReferralLink; message: string }> {
  return request("/api/affiliates/referral-link", {
    method: "POST",
    body: JSON.stringify({ affiliate_id: affiliateId, product_id: productId }),
  });
}

export async function fetchReferralLinks(affiliateId?: number, productId?: number): Promise<{ links: ReferralLink[]; count: number }> {
  const params = new URLSearchParams();
  if (affiliateId) params.set("affiliate_id", String(affiliateId));
  if (productId) params.set("product_id", String(productId));
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/affiliates/referral-links${query}`);
}

export async function trackReferralClick(refCode: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/affiliates/track-click?ref_code=${encodeURIComponent(refCode)}`, { method: "POST" });
}

export async function trackReferralConversion(refCode: string, revenue: number): Promise<{ success: boolean; message: string }> {
  return request("/api/affiliates/track-conversion", {
    method: "POST",
    body: JSON.stringify({ ref_code: refCode, revenue }),
  });
}

export async function fetchReferralStats(affiliateId?: number): Promise<Record<string, unknown>> {
  const query = affiliateId ? `?affiliate_id=${affiliateId}` : "";
  return request(`/api/affiliates/stats${query}`);
}

export async function generateMarketingKit(productId: number): Promise<{ success: boolean; kit: Record<string, unknown>; message: string }> {
  return request(`/api/affiliates/marketing-kit/${productId}`, { method: "POST" });
}

// Piracy Protection
export async function createWatermark(productId: number): Promise<{ success: boolean; watermark_id: string; message: string }> {
  return request(`/api/products/${productId}/watermark`, { method: "POST" });
}

export async function fetchPiracyStatus(productId?: number): Promise<{ protections: PiracyProtection[]; count: number }> {
  const query = productId ? `?product_id=${productId}` : "";
  return request(`/api/piracy/status${query}`);
}

export async function recordPiracyScan(productId: number, data: {
  source?: string;
  found_url?: string;
  match_confidence?: number;
  notes?: string;
}): Promise<{ success: boolean; message: string }> {
  return request(`/api/piracy/${productId}/scan`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateDMCA(productId: number, data: {
  infringer_url?: string;
  infringer_name?: string;
}): Promise<{ success: boolean; dmca: DMCARequest; message: string }> {
  return request(`/api/piracy/${productId}/dmca`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchDMCARequests(productId?: number): Promise<{ requests: DMCARequest[]; count: number }> {
  const query = productId ? `?product_id=${productId}` : "";
  return request(`/api/piracy/dmca${query}`);
}

export async function updateDMCAStatus(dmcaId: number, status: string): Promise<DMCARequest> {
  return request<DMCARequest>(`/api/piracy/dmca/${dmcaId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// White-Label Resell
export async function fetchWhiteLabelTiers(): Promise<{ tiers: WhiteLabelTier[]; count: number }> {
  return request("/api/white-label/tiers");
}

export async function fetchTenants(status?: string): Promise<{ tenants: WhiteLabelTenant[]; count: number }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/white-label/tenants${query}`);
}

export async function createTenant(data: {
  name: string;
  owner_email: string;
  brand_name?: string;
  brand_color?: string;
  tier?: string;
  custom_domain?: string;
}): Promise<{ success: boolean; tenant: WhiteLabelTenant; message: string }> {
  return request("/api/white-label/tenants", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTenant(id: number, data: Partial<{
  name: string;
  owner_email: string;
  brand_name: string;
  brand_color: string;
  tier: string;
  custom_domain: string;
  status: string;
}>): Promise<WhiteLabelTenant> {
  return request<WhiteLabelTenant>(`/api/white-label/tenants/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTenant(id: number): Promise<{ message: string }> {
  return request(`/api/white-label/tenants/${id}`, { method: "DELETE" });
}

export async function fetchTenantLimits(tenantId: number): Promise<Record<string, unknown>> {
  return request(`/api/white-label/tenants/${tenantId}/limits`);
}

export async function fetchWhiteLabelStats(): Promise<Record<string, unknown>> {
  return request("/api/white-label/stats");
}
