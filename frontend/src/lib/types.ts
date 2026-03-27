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
