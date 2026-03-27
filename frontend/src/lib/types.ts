export interface Product {
  id: number;
  name: string;
  product_type: string;
  brief: string;
  target_platforms: string[];
  target_languages: string[];
  status: string;
  plan_mode: string;
  research_data: Record<string, unknown>;
  niche_data: Record<string, unknown>;
  trend_data: Record<string, unknown>;
  remix_parent_id: number | null;
  created_at: string;
  updated_at: string;
  variants?: ProductVariant[];
  social_posts?: SocialPost[];
  pipeline_logs?: PipelineLog[];
}

export interface ProductVariant {
  id: number;
  product_id: number;
  platform: string;
  language: string;
  title: string;
  description: string;
  tags: string[];
  price: string;
  image_urls: string[];
  ceo_score: number;
  ceo_feedback: string;
  ceo_status: string;
  revision_count: number;
  post_status: string;
  post_url: string;
  ab_variant: string;
  created_at: string;
}

export interface SocialPost {
  id: number;
  product_id: number;
  platform: string;
  caption: string;
  video_url: string;
  voice_url: string;
  post_status: string;
  post_url: string;
  scheduled_at: string | null;
  posted_at: string | null;
  created_at: string;
  hashtags?: string[];
  subreddits?: string[];
}

export interface PipelineLog {
  id: number;
  product_id: number;
  agent: string;
  ai_provider: string;
  status: string;
  message: string;
  created_at: string;
}

export interface AIProvider {
  name: string;
  model: string;
  type: string;
  status: string;
  requests_today: number;
  daily_limit: number;
  available: boolean;
  last_used: string;
  last_error: string;
}

export interface Stats {
  products: {
    total: number;
    by_status: Record<string, number>;
  };
  variants: { total: number };
  social_posts: { total: number };
  niche_ideas: { total: number };
  ab_tests: { total: number };
}

export interface ProductCreate {
  name: string;
  product_type: string;
  brief: string;
  target_platforms: string[];
  target_languages: string[];
  status: string;
  plan_mode: string;
}

export interface AutoPostPlatformConfig {
  configured: boolean;
  [key: string]: boolean;
}

export interface AutoPostConfig {
  telegram: AutoPostPlatformConfig;
  tumblr: AutoPostPlatformConfig;
  pinterest: AutoPostPlatformConfig;
}

// Analytics types
export interface AnalyticsOverview {
  total_revenue: number;
  total_refunds: number;
  net_revenue: number;
  products_created: number;
  total_sales: number;
  total_views: number;
  total_clicks: number;
  best_platform: string;
  best_platform_revenue: number;
  avg_ceo_score: number;
  approval_rate: number;
}

export interface RevenueDataPoint {
  date: string;
  revenue: number;
  sales: number;
  refunds: number;
  sale_count: number;
  views: number;
  clicks: number;
}

export interface PlatformPerformance {
  platform: string;
  revenue: number;
  gross_revenue: number;
  refunds: number;
  sales: number;
  views: number;
  clicks: number;
  conversion_rate: number;
  posts: number;
}

export interface TopProduct {
  product_id: number;
  name: string;
  status: string;
  created_at: string;
  revenue: number;
  gross_revenue: number;
  refunds: number;
  sales: number;
  views: number;
}

export interface CeoTrendPoint {
  date: string;
  avg_score: number;
  approved: number;
  rejected: number;
  total: number;
  approval_rate: number;
}

export interface AIProviderUsage {
  provider: string;
  usage_count: number;
  success: number;
  errors: number;
  success_rate: number;
}

export interface Insight {
  type: string;
  icon: string;
  message: string;
  severity: "positive" | "negative" | "warning" | "info";
}

export interface CalendarPost {
  id: number;
  product_id: number;
  platform: string;
  caption: string;
  video_url: string;
  voice_url: string;
  post_status: string;
  post_url: string;
  scheduled_at: string;
  posted_at: string | null;
  created_at: string;
  product_name: string;
  hashtags?: string[];
}

export interface ScheduleSuggestion {
  platform: string;
  best_days: string[];
  best_hours: number[];
  timezone: string;
  tip: string;
  color: string;
}

// Remix Engine types
export interface RemixVariation {
  remix_type: string;
  variation_name: string;
  product_name: string;
  product_type: string;
  brief: string;
  target_audience: string;
  suggested_price: string;
  language: string;
  key_differences: string;
  child_product_id?: number;
}

export interface RemixResult {
  success: boolean;
  variations: RemixVariation[];
  children_ids: number[];
  provider: string | null;
  message: string;
}

// Niche Finder types
export interface NicheIdea {
  id: number;
  product_name: string;
  demand_score: number;
  competition: string;
  monthly_searches: number;
  evidence: string;
  suggested_price: string;
  best_platforms: string[];
  status: string;
  created_product_id: number | null;
  created_at: string;
}

// A/B Testing types
export interface ABTest {
  id: number;
  product_id: number;
  product_name: string;
  test_name: string;
  variant_a_id: number;
  variant_b_id: number;
  variant_c_id: number;
  winner_id: number | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  variants: ABTestVariant[];
}

export interface ABTestVariant extends ProductVariant {
  sales_count: number;
  sales_revenue: number;
  views_count: number;
  conversion_rate: number;
}

export interface ABTestResult {
  success: boolean;
  test_id: number;
  variant_a_id: number;
  variant_b_id: number;
  variant_c_id: number;
  strategies: Record<string, string>;
  insights: string;
  provider: string | null;
  message: string;
}

export interface ABPattern {
  pattern: string;
  detail: string;
  confidence: number;
}

// Smart Pricing types
export interface PriceSuggestions {
  success: boolean;
  product_id: number;
  product_name: string;
  suggestions: {
    base_price: string;
    platform_prices: Record<string, { price: string; reasoning: string }>;
    launch_pricing: {
      launch_price: string;
      launch_duration_hours: number;
      regular_price: string;
      reasoning: string;
    };
    bundle_pricing: {
      bundle_3_price: string;
      individual_total: string;
      savings_percent: string;
      reasoning: string;
    };
    pricing_tiers: { tier: string; price: string; includes: string }[];
    competitor_analysis: string;
    confidence: number;
  };
  provider: string | null;
  generated_at: string;
  message: string;
}

export interface LaunchPricing {
  regular_price: string;
  launch_price: string;
  discount_percent: string;
  savings: string;
  duration_hours: number;
  description: string;
}

export interface BundlePricing {
  individual_total: string;
  bundle_price: string;
  savings: string;
  savings_percent: string;
  item_count: number;
  description: string;
}

// Email Marketing types
export interface EmailCampaign {
  id: number;
  product_id: number;
  subject_lines: string[];
  email_body: { subject: string; body: string };
  follow_up_day3: { subject: string; body: string };
  follow_up_day7: { subject: string; body: string };
  status: string;
  created_at: string;
}

export interface EmailCampaignResult {
  success: boolean;
  campaign: EmailCampaign;
  provider: string | null;
  message: string;
}

// Revenue Goals types
export interface RevenueGoal {
  id: number;
  target_amount: number;
  period: string;
  current_amount: number;
  products_needed: number;
  status: string;
  created_at: string;
  progress_percent: number;
  remaining: number;
  avg_sale_price: number;
  sales_this_period: number;
  sales_needed: number;
  total_products: number;
  status_label: string;
  suggestions: GoalSuggestion[];
}

export interface GoalSuggestion {
  type: string;
  icon: string;
  message: string;
}

// Trend Predictor types
export interface TrendPrediction {
  id: number;
  trend_name: string;
  predicted_peak: string;
  current_phase: string;
  confidence: number;
  action: string;
  time_remaining: string;
  category: string;
  evidence: string;
  status: string;
  created_product_id: number | null;
  created_at: string;
}

// Content Repurposing types
export interface RepurposedContent {
  id: number;
  product_id: number;
  content_type: string;
  content: string;
  platform: string;
  post_status: string;
  scheduled_at: string | null;
  created_at: string;
  label: string;
}

export interface RepurposeResult {
  success: boolean;
  product_id: number;
  content: RepurposedContent[];
  count: number;
  provider: string | null;
  message: string;
}

// Voice-Over types
export interface VoiceOverResult {
  success: boolean;
  product_id: number;
  script: string;
  duration_estimate: string;
  word_count: number;
  tone: string;
  audio_url: string;
  tts_provider: string;
  ai_provider: string | null;
  message: string;
}

// FAQ Bot types
export interface FAQEntry {
  id: number;
  question: string;
  answer: string;
  category: string;
  times_used: number;
  created_at: string;
  updated_at: string;
}

export interface FAQSuggestion {
  success: boolean;
  question: string;
  suggested_answer: string;
  confidence: number;
  category: string;
  related_faqs: string[];
  provider: string | null;
  message: string;
}

// Settings types
export interface PlatformSetting {
  id: number;
  platform: string;
  tone: string;
  plan_mode: string;
  enabled: number | boolean;
  max_title_length: number;
  max_description_length: number;
  custom_instructions: string;
}

export interface CustomerPersona {
  id: number;
  name: string;
  age_range: string;
  description: string;
  preferences: Record<string, unknown>;
  platforms: string[];
  created_at: string;
}

export interface APIKeyStatus {
  keys: Record<string, boolean>;
  configured: number;
  total: number;
}

export interface UserPreferences {
  [key: string]: string;
}
