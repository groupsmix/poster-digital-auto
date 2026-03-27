import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Copy, Download, Check, ClipboardList, Send, Edit3, Shuffle, X, Globe, FlaskConical, DollarSign, Mail, Loader2, Tag, Clock, Package, Zap, RefreshCw, Play, Pause, Volume2, FileText } from "lucide-react";
import { fetchProduct, generateCaptions, triggerAutoPost, updateSocialPost, fetchAutoPostConfig, remixProduct, fetchRemixChildren, createABTest, fetchPriceSuggestions, generateEmailCampaign, fetchEmailCampaign, repurposeProduct, fetchRepurposedContent, generateVoiceover } from "@/lib/api";
import type { Product, AutoPostConfig, PriceSuggestions, EmailCampaign, RepurposedContent, VoiceOverResult } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import CeoScoreBadge from "@/components/CeoScoreBadge";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

type Tab = "copy" | "research" | "social" | "email" | "pricing" | "repurpose" | "voiceover" | "logs";

const REMIX_TYPE_OPTIONS = [
  { key: "audience", label: "Audience", description: "Student, Business, Family, Freelancer" },
  { key: "style", label: "Style", description: "Dark Mode, Pastel, Minimalist, Colorful" },
  { key: "language", label: "Language", description: "English, Arabic, French, Spanish, German" },
  { key: "niche", label: "Niche", description: "Budget, Health, Fitness, Travel" },
  { key: "bundle", label: "Bundle", description: "Combine with other products" },
];

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  ar: "Arabic",
  fr: "French",
  es: "Spanish",
  de: "German",
};

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success(`${label} copied!`);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-700"
    >
      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

const AUTO_POST_PLATFORMS = ["Telegram", "Tumblr", "Pinterest"];

function SocialPostsTab({
  product,
  setProduct,
}: {
  product: Product;
  setProduct: React.Dispatch<React.SetStateAction<Product | null>>;
}) {
  const [generating, setGenerating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editCaption, setEditCaption] = useState("");
  const [postingId, setPostingId] = useState<number | null>(null);
  const [autoPostConfig, setAutoPostConfig] = useState<AutoPostConfig | null>(null);

  useEffect(() => {
    fetchAutoPostConfig().then(setAutoPostConfig).catch(() => {});
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await generateCaptions(product.id);
      const updated = await fetchProduct(product.id);
      setProduct(updated);
      toast.success("Captions generated for all platforms!");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Generation failed";
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  }

  function handleCopyAll(platform: string) {
    const posts = product.social_posts?.filter((p) => p.platform === platform) ?? [];
    const text = posts.map((p) => p.caption).join("\n\n---\n\n");
    navigator.clipboard.writeText(text).then(() => toast.success(`All ${platform} captions copied!`));
  }

  function handleCopyAllPlatforms() {
    const posts = product.social_posts ?? [];
    const text = posts
      .map((p) => `=== ${p.platform} ===\n\n${p.caption}`)
      .join("\n\n---\n\n");
    navigator.clipboard.writeText(text).then(() => toast.success("All captions copied!"));
  }

  async function handleSaveEdit(id: number) {
    try {
      const updated = await updateSocialPost(id, { caption: editCaption });
      setProduct((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          social_posts: prev.social_posts?.map((p) => (p.id === id ? { ...p, ...updated } : p)),
        };
      });
      setEditingId(null);
      toast.success("Caption updated!");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Update failed";
      toast.error(msg);
    }
  }

  async function handleAutoPost(id: number) {
    setPostingId(id);
    try {
      const result = await triggerAutoPost(id);
      setProduct((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          social_posts: prev.social_posts?.map((p) =>
            p.id === id ? { ...p, post_status: "posted", post_url: result.post_url } : p,
          ),
        };
      });
      toast.success(`Posted to ${result.platform}!`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Auto-post failed";
      toast.error(msg);
    } finally {
      setPostingId(null);
    }
  }

  function isAutoPostAvailable(platform: string): boolean {
    if (!autoPostConfig) return false;
    const key = platform.toLowerCase() as keyof AutoPostConfig;
    return AUTO_POST_PLATFORMS.includes(platform) && autoPostConfig[key]?.configured === true;
  }

  const posts = product.social_posts ?? [];
  const platforms = [...new Set(posts.map((p) => p.platform))];

  return (
    <div className="space-y-6">
      {/* Actions bar */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {generating ? <Spinner className="h-4 w-4" /> : <ClipboardList className="h-4 w-4" />}
          {generating ? "Generating..." : "Generate Captions"}
        </button>
        {posts.length > 0 && (
          <button
            onClick={handleCopyAllPlatforms}
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
          >
            <Copy className="h-4 w-4" />
            Copy All ({posts.length})
          </button>
        )}
      </div>

      {posts.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <p className="text-zinc-400">
            No social posts generated yet. Click &ldquo;Generate Captions&rdquo; to create captions for all 11 platforms.
          </p>
        </div>
      ) : (
        platforms.map((platform) => {
          const platformPosts = posts.filter((p) => p.platform === platform);
          return (
            <div key={platform} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-fuchsia-500/20 px-2.5 py-1 text-sm font-semibold text-fuchsia-300">
                    {platform}
                  </span>
                  <span className="text-xs text-zinc-500">({platformPosts.length})</span>
                </div>
                <button
                  onClick={() => handleCopyAll(platform)}
                  className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
                >
                  <Copy className="h-3 w-3" />
                  Copy All
                </button>
              </div>

              {platformPosts.map((post) => (
                <div
                  key={post.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
                >
                  <div className="flex items-center justify-between">
                    <StatusBadge status={post.post_status} />
                    <div className="flex items-center gap-2">
                      <CopyButton text={post.caption} label={`${platform} caption`} />
                      <button
                        onClick={() => {
                          setEditingId(post.id);
                          setEditCaption(post.caption);
                        }}
                        className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
                      >
                        <Edit3 className="h-3 w-3" />
                        Edit
                      </button>
                      {AUTO_POST_PLATFORMS.includes(platform) && (
                        <button
                          onClick={() => handleAutoPost(post.id)}
                          disabled={postingId === post.id || !isAutoPostAvailable(platform)}
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${
                            isAutoPostAvailable(platform)
                              ? "bg-violet-600 text-white hover:bg-violet-500"
                              : "bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700"
                          }`}
                          title={
                            isAutoPostAvailable(platform)
                              ? `Auto-post to ${platform}`
                              : `${platform} API not configured`
                          }
                        >
                          {postingId === post.id ? (
                            <Spinner className="h-3 w-3" />
                          ) : (
                            <Send className="h-3 w-3" />
                          )}
                          Post
                        </button>
                      )}
                    </div>
                  </div>

                  {editingId === post.id ? (
                    <div className="mt-3 space-y-2">
                      <textarea
                        value={editCaption}
                        onChange={(e) => setEditCaption(e.target.value)}
                        className="w-full rounded-lg bg-zinc-800 p-3 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none min-h-[120px] resize-y"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(post.id)}
                          className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-3 whitespace-pre-wrap rounded-lg bg-zinc-800/50 p-3 text-sm text-zinc-200">
                      {post.caption}
                    </p>
                  )}

                  {post.hashtags && post.hashtags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {post.hashtags.map((tag, i) => (
                        <span key={i} className="rounded-full bg-violet-500/10 px-2 py-0.5 text-xs text-violet-300">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {post.subreddits && post.subreddits.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {post.subreddits.map((sub, i) => (
                        <span key={i} className="rounded-full bg-orange-500/10 px-2 py-0.5 text-xs text-orange-300">
                          r/{sub}
                        </span>
                      ))}
                    </div>
                  )}

                  {post.post_url && (
                    <a
                      href={post.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                    >
                      View post <span className="text-[10px]">&rarr;</span>
                    </a>
                  )}

                  <p className="mt-2 text-xs text-zinc-600">
                    {post.posted_at
                      ? `Posted: ${new Date(post.posted_at).toLocaleString()}`
                      : `Created: ${new Date(post.created_at).toLocaleString()}`}
                  </p>
                </div>
              ))}
            </div>
          );
        })
      )}
    </div>
  );
}

function ABTestButton({ variantId }: { variantId: number }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ strategies?: Record<string, string>; insights?: string } | null>(null);

  async function handleCreateTest() {
    setLoading(true);
    try {
      const res = await createABTest(variantId);
      setResult({ strategies: res.strategies, insights: res.insights });
      toast.success(res.message);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "A/B test creation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-violet-400" />
          <span className="text-xs font-medium text-zinc-300">A/B Testing</span>
        </div>
        <button
          onClick={handleCreateTest}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <FlaskConical className="h-3 w-3" />}
          {loading ? "Creating..." : "A/B Test"}
        </button>
      </div>
      {result && (
        <div className="mt-3 space-y-2">
          {result.strategies && Object.entries(result.strategies).map(([key, val]) => (
            <div key={key} className="flex items-start gap-2">
              <span className="rounded bg-violet-500/20 px-1.5 py-0.5 text-[10px] font-bold text-violet-300">{key}</span>
              <span className="text-xs text-zinc-400">{val}</span>
            </div>
          ))}
          {result.insights && (
            <p className="text-xs italic text-zinc-500">{result.insights}</p>
          )}
        </div>
      )}
    </div>
  );
}

function EmailTab({ product }: { product: Product }) {
  const [campaign, setCampaign] = useState<EmailCampaign | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    fetchEmailCampaign(product.id)
      .then(setCampaign)
      .catch(() => {})
      .finally(() => setFetching(false));
  }, [product.id]);

  async function handleGenerate() {
    setLoading(true);
    try {
      const res = await generateEmailCampaign(product.id);
      setCampaign(res.campaign);
      toast.success(res.message);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Email generation failed");
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="flex justify-center py-10">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
          {loading ? "Generating..." : campaign ? "Regenerate Campaign" : "Generate Email Campaign"}
        </button>
      </div>

      {!campaign ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Mail className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No email campaign yet. Click &ldquo;Generate Email Campaign&rdquo; to create one.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Subject Lines */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-200">
              <Tag className="h-4 w-4 text-violet-400" />
              Subject Line Variations
            </h3>
            <div className="space-y-2">
              {campaign.subject_lines.map((subject, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-zinc-800/50 p-3">
                  <span className="text-sm text-zinc-200">{subject}</span>
                  <CopyButton text={subject} label={`Subject ${i + 1}`} />
                </div>
              ))}
            </div>
          </div>

          {/* Promo Email */}
          {campaign.email_body && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
                  <Send className="h-4 w-4 text-emerald-400" />
                  Launch Email
                </h3>
                <CopyButton
                  text={`Subject: ${campaign.email_body.subject}\n\n${campaign.email_body.body}`}
                  label="Launch email"
                />
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-3">
                <p className="mb-2 text-xs font-medium text-zinc-400">Subject: {campaign.email_body.subject}</p>
                <p className="whitespace-pre-wrap text-sm text-zinc-200">{campaign.email_body.body}</p>
              </div>
            </div>
          )}

          {/* Day 3 Follow-up */}
          {campaign.follow_up_day3 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
                  <Clock className="h-4 w-4 text-yellow-400" />
                  Day 3 Follow-up (Tip/Value)
                </h3>
                <CopyButton
                  text={`Subject: ${campaign.follow_up_day3.subject}\n\n${campaign.follow_up_day3.body}`}
                  label="Day 3 email"
                />
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-3">
                <p className="mb-2 text-xs font-medium text-zinc-400">Subject: {campaign.follow_up_day3.subject}</p>
                <p className="whitespace-pre-wrap text-sm text-zinc-200">{campaign.follow_up_day3.body}</p>
              </div>
            </div>
          )}

          {/* Day 7 Follow-up */}
          {campaign.follow_up_day7 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
                  <Package className="h-4 w-4 text-fuchsia-400" />
                  Day 7 Follow-up (Upsell)
                </h3>
                <CopyButton
                  text={`Subject: ${campaign.follow_up_day7.subject}\n\n${campaign.follow_up_day7.body}`}
                  label="Day 7 email"
                />
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-3">
                <p className="mb-2 text-xs font-medium text-zinc-400">Subject: {campaign.follow_up_day7.subject}</p>
                <p className="whitespace-pre-wrap text-sm text-zinc-200">{campaign.follow_up_day7.body}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PricingTab({ product }: { product: Product }) {
  const [pricing, setPricing] = useState<PriceSuggestions | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleFetchPricing() {
    setLoading(true);
    try {
      const res = await fetchPriceSuggestions(product.id);
      setPricing(res);
      toast.success("Price suggestions generated!");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Pricing failed");
    } finally {
      setLoading(false);
    }
  }

  const s = pricing?.suggestions;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={handleFetchPricing}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <DollarSign className="h-4 w-4" />}
          {loading ? "Analyzing..." : pricing ? "Refresh Pricing" : "Get AI Price Suggestions"}
        </button>
      </div>

      {!s ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <DollarSign className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">Click &ldquo;Get AI Price Suggestions&rdquo; to analyze optimal pricing.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Base Price & Confidence */}
          <div className="flex items-center gap-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
            <div className="rounded-lg bg-emerald-500/20 p-3">
              <DollarSign className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-300">{s.base_price}</p>
              <p className="text-sm text-zinc-400">Recommended Base Price</p>
            </div>
            {s.confidence && (
              <div className="ml-auto text-right">
                <p className="text-lg font-semibold text-zinc-200">{s.confidence}%</p>
                <p className="text-xs text-zinc-500">Confidence</p>
              </div>
            )}
          </div>

          {/* Platform Prices */}
          {s.platform_prices && Object.keys(s.platform_prices).length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="mb-3 text-sm font-semibold text-zinc-200">Platform-Specific Pricing</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                {Object.entries(s.platform_prices).map(([platform, data]) => (
                  <div key={platform} className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
                    <p className="text-xs font-medium text-zinc-400">{platform}</p>
                    <p className="mt-1 text-lg font-bold text-emerald-300">{data.price}</p>
                    <p className="mt-1 text-xs text-zinc-500">{data.reasoning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Launch Pricing */}
          {s.launch_pricing && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-200">
                <Zap className="h-4 w-4 text-yellow-400" />
                Launch Pricing Strategy
              </h3>
              <div className="flex items-center gap-4">
                <div className="rounded-lg bg-yellow-500/10 p-3 text-center">
                  <p className="text-xl font-bold text-yellow-300">{s.launch_pricing.launch_price}</p>
                  <p className="text-xs text-zinc-400">for {s.launch_pricing.launch_duration_hours}h</p>
                </div>
                <span className="text-zinc-500">&rarr;</span>
                <div className="rounded-lg bg-zinc-800 p-3 text-center">
                  <p className="text-xl font-bold text-zinc-200">{s.launch_pricing.regular_price}</p>
                  <p className="text-xs text-zinc-400">regular</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-zinc-500">{s.launch_pricing.reasoning}</p>
            </div>
          )}

          {/* Bundle Pricing */}
          {s.bundle_pricing && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-200">
                <Package className="h-4 w-4 text-fuchsia-400" />
                Bundle Pricing
              </h3>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-zinc-800 p-3 text-center">
                  <p className="text-sm text-zinc-400 line-through">{s.bundle_pricing.individual_total}</p>
                  <p className="text-xs text-zinc-500">individual</p>
                </div>
                <span className="text-zinc-500">&rarr;</span>
                <div className="rounded-lg bg-fuchsia-500/10 p-3 text-center">
                  <p className="text-xl font-bold text-fuchsia-300">{s.bundle_pricing.bundle_3_price}</p>
                  <p className="text-xs text-zinc-400">bundle of 3</p>
                </div>
                <span className="rounded bg-emerald-500/20 px-2 py-1 text-xs font-medium text-emerald-300">
                  Save {s.bundle_pricing.savings_percent}
                </span>
              </div>
              <p className="mt-2 text-xs text-zinc-500">{s.bundle_pricing.reasoning}</p>
            </div>
          )}

          {/* Pricing Tiers */}
          {s.pricing_tiers && s.pricing_tiers.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="mb-3 text-sm font-semibold text-zinc-200">Pricing Tiers</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                {s.pricing_tiers.map((tier, i) => (
                  <div key={i} className={`rounded-lg border p-4 ${i === 1 ? "border-violet-500 bg-violet-500/10" : "border-zinc-700 bg-zinc-800/50"}`}>
                    <p className="text-xs font-medium text-zinc-400">{tier.tier}</p>
                    <p className="mt-1 text-xl font-bold text-zinc-200">{tier.price}</p>
                    <p className="mt-2 text-xs text-zinc-500">{tier.includes}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Competitor Analysis */}
          {s.competitor_analysis && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="mb-2 text-sm font-semibold text-zinc-200">Competitor Analysis</h3>
              <p className="text-sm text-zinc-400">{s.competitor_analysis}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const CONTENT_TYPE_LABELS: Record<string, { label: string; icon: string }> = {
  blog_post: { label: "Blog Post (SEO)", icon: "📝" },
  youtube_script: { label: "YouTube Script (60s)", icon: "🎬" },
  twitter_thread: { label: "Twitter/X Thread", icon: "🐦" },
  instagram_carousel: { label: "Instagram Carousel", icon: "📸" },
  newsletter: { label: "Newsletter Issue", icon: "📧" },
  quora_answer: { label: "Quora Answer", icon: "❓" },
  pinterest_pin: { label: "Pinterest Pin", icon: "📌" },
};

function RepurposeTab({ product }: { product: Product }) {
  const [content, setContent] = useState<RepurposedContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    fetchRepurposedContent(product.id)
      .then((res) => setContent(res.content))
      .catch(() => {})
      .finally(() => setFetching(false));
  }, [product.id]);

  async function handleRepurpose() {
    setLoading(true);
    try {
      const res = await repurposeProduct(product.id);
      setContent(res.content);
      toast.success(res.message);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Repurposing failed");
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="flex justify-center py-10">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={handleRepurpose}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          {loading ? "Generating..." : content.length > 0 ? "Regenerate All" : "Repurpose Content"}
        </button>
        {content.length > 0 && (
          <span className="text-sm text-zinc-400">{content.length} formats generated</span>
        )}
      </div>

      {content.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <FileText className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">
            No repurposed content yet. Click &ldquo;Repurpose Content&rdquo; to generate 7 content formats from this product.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {content.map((item) => {
            const meta = CONTENT_TYPE_LABELS[item.content_type] || { label: item.content_type, icon: "📄" };
            return (
              <div key={item.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{meta.icon}</span>
                    <h3 className="text-sm font-semibold text-zinc-200">{meta.label}</h3>
                    {item.platform && (
                      <span className="rounded bg-fuchsia-500/20 px-2 py-0.5 text-xs text-fuchsia-300">
                        {item.platform}
                      </span>
                    )}
                  </div>
                  <CopyButton text={item.content} label={meta.label} />
                </div>
                <p className="mt-3 whitespace-pre-wrap rounded-lg bg-zinc-800/50 p-4 text-sm leading-relaxed text-zinc-200">
                  {item.content}
                </p>
                <p className="mt-2 text-xs text-zinc-600">
                  Generated: {new Date(item.created_at).toLocaleString()}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function VoiceOverTab({ product }: { product: Product }) {
  const [result, setResult] = useState<VoiceOverResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null);

  async function handleGenerate() {
    setLoading(true);
    try {
      const res = await generateVoiceover(product.id);
      setResult(res);
      toast.success(res.message);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Voice-over generation failed");
    } finally {
      setLoading(false);
    }
  }

  function handlePlay() {
    if (!result?.audio_url) {
      toast.error("No audio available. Browser TTS will be used.");
      if (result?.script) {
        const utterance = new SpeechSynthesisUtterance(result.script);
        utterance.rate = 0.9;
        utterance.onend = () => setPlaying(false);
        speechSynthesis.speak(utterance);
        setPlaying(true);
      }
      return;
    }

    if (playing && audioEl) {
      audioEl.pause();
      setPlaying(false);
      return;
    }

    const audio = new Audio(result.audio_url);
    audio.onended = () => setPlaying(false);
    audio.play();
    setAudioEl(audio);
    setPlaying(true);
  }

  function handleStop() {
    if (audioEl) {
      audioEl.pause();
      audioEl.currentTime = 0;
    }
    speechSynthesis.cancel();
    setPlaying(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Volume2 className="h-4 w-4" />}
          {loading ? "Generating..." : result ? "Regenerate Voice-Over" : "Generate Voice-Over"}
        </button>
      </div>

      {!result ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Volume2 className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">
            No voice-over generated yet. Click &ldquo;Generate Voice-Over&rdquo; to create a 30-second audio script.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Script */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-semibold text-zinc-200">Voice-Over Script</h3>
              <CopyButton text={result.script} label="Script" />
            </div>
            <p className="mt-3 whitespace-pre-wrap rounded-lg bg-zinc-800/50 p-4 text-sm leading-relaxed text-zinc-200">
              {result.script}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-zinc-500">
              <span>{result.word_count} words</span>
              <span>{result.duration_estimate}</span>
              <span>Tone: {result.tone}</span>
              <span>TTS: {result.tts_provider}</span>
              {result.ai_provider && <span>AI: {result.ai_provider}</span>}
            </div>
          </div>

          {/* Audio Player */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <h3 className="mb-4 text-sm font-semibold text-zinc-200">Audio Player</h3>
            <div className="flex items-center gap-3">
              <button
                onClick={handlePlay}
                className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors ${
                  playing
                    ? "bg-amber-600 hover:bg-amber-500"
                    : "bg-emerald-600 hover:bg-emerald-500"
                }`}
              >
                {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {playing ? "Pause" : "Play"}
              </button>
              {playing && (
                <button
                  onClick={handleStop}
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
                >
                  Stop
                </button>
              )}
              {result.audio_url && (
                <a
                  href={result.audio_url}
                  download
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
                >
                  <Download className="h-4 w-4" />
                  Download
                </a>
              )}
            </div>
            {!result.audio_url && (
              <p className="mt-3 text-xs text-zinc-500">
                No audio file generated — browser Text-to-Speech will be used for playback.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("copy");
  const [showRemixModal, setShowRemixModal] = useState(false);
  const [selectedRemixTypes, setSelectedRemixTypes] = useState<string[]>(["audience", "style", "language"]);
  const [remixing, setRemixing] = useState(false);
  const [remixChildren, setRemixChildren] = useState<Product[]>([]);
  const [copyLangTab, setCopyLangTab] = useState<string>("all");

  useEffect(() => {
    if (!id) return;
    fetchProduct(Number(id))
      .then((p) => {
        setProduct(p);
        fetchRemixChildren(Number(id))
          .then((r) => setRemixChildren(r.children))
          .catch(() => {});
      })
      .catch((e) => {
        toast.error(e.message);
        navigate("/products");
      })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  function toggleRemixType(key: string) {
    setSelectedRemixTypes((prev) =>
      prev.includes(key) ? prev.filter((t) => t !== key) : [...prev, key]
    );
  }

  async function handleRemix() {
    if (!product || selectedRemixTypes.length === 0) return;
    setRemixing(true);
    try {
      const result = await remixProduct(product.id, selectedRemixTypes);
      toast.success(result.message);
      setShowRemixModal(false);
      const children = await fetchRemixChildren(product.id);
      setRemixChildren(children.children);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Remix failed");
    } finally {
      setRemixing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-32">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!product) return null;

  const tabs: { key: Tab; label: string }[] = [
    { key: "copy", label: "Copy Center" },
    { key: "research", label: "Research" },
    { key: "social", label: "Social Posts" },
    { key: "email", label: "Email" },
    { key: "pricing", label: "Pricing" },
    { key: "repurpose", label: "Repurpose" },
    { key: "voiceover", label: "Voice-Over" },
    { key: "logs", label: "Pipeline Logs" },
  ];

  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  return (
    <div className="space-y-6">
      {/* Remix Modal */}
      {showRemixModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-zinc-100">Remix This Product</h2>
              <button onClick={() => setShowRemixModal(false)} className="text-zinc-400 hover:text-zinc-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="mt-2 text-sm text-zinc-400">
              Generate 5-10 variations of &ldquo;{product.name}&rdquo;. Each variation goes through the full AI pipeline.
            </p>
            <div className="mt-4 space-y-3">
              {REMIX_TYPE_OPTIONS.map((opt) => (
                <label
                  key={opt.key}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                    selectedRemixTypes.includes(opt.key)
                      ? "border-violet-500 bg-violet-500/10"
                      : "border-zinc-700 bg-zinc-800 hover:border-zinc-600"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedRemixTypes.includes(opt.key)}
                    onChange={() => toggleRemixType(opt.key)}
                    className="mt-0.5 accent-violet-500"
                  />
                  <div>
                    <span className="font-medium text-zinc-200">{opt.label}</span>
                    <p className="text-xs text-zinc-400">{opt.description}</p>
                  </div>
                </label>
              ))}
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleRemix}
                disabled={remixing || selectedRemixTypes.length === 0}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {remixing ? <Spinner className="h-4 w-4" /> : <Shuffle className="h-4 w-4" />}
                {remixing ? "Remixing..." : `Remix (${selectedRemixTypes.length} types)`}
              </button>
              <button
                onClick={() => setShowRemixModal(false)}
                className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/products")} className="rounded-md p-1 text-zinc-400 hover:text-zinc-200">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">{product.name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <StatusBadge status={product.status} />
              <span className="text-sm text-zinc-500">Plan {product.plan_mode}</span>
              <span className="text-sm text-zinc-500">
                {product.target_platforms.join(", ")}
              </span>
              {product.remix_parent_id && (
                <Link
                  to={`/products/${product.remix_parent_id}`}
                  className="rounded bg-fuchsia-500/20 px-2 py-0.5 text-xs font-medium text-fuchsia-300 hover:bg-fuchsia-500/30"
                >
                  Remix of #{product.remix_parent_id}
                </Link>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => setShowRemixModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          <Shuffle className="h-4 w-4" />
          Remix This Product
        </button>
      </div>

      {/* Remix Children */}
      {remixChildren.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="mb-3 text-sm font-semibold text-zinc-300">Remix Variations ({remixChildren.length})</h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {remixChildren.map((child) => (
              <Link
                key={child.id}
                to={`/products/${child.id}`}
                className="flex items-center justify-between rounded-lg border border-zinc-700 bg-zinc-800 p-3 transition-colors hover:border-violet-500/50"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-200">{child.name}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <StatusBadge status={child.status} />
                    {child.target_languages.map((lang) => (
                      <span key={lang} className="rounded bg-zinc-700 px-1.5 py-0.5 text-[10px] text-zinc-400">
                        {LANGUAGE_LABELS[lang] || lang}
                      </span>
                    ))}
                  </div>
                </div>
                <span className="ml-2 text-xs text-violet-400">View &rarr;</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-zinc-800">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-violet-500 text-violet-400"
                : "border-transparent text-zinc-400 hover:border-zinc-600 hover:text-zinc-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "copy" && (
        <div className="space-y-6">
          {(!product.variants || product.variants.length === 0) ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <p className="text-zinc-400">No variants generated yet. Run the AI pipeline to generate content.</p>
            </div>
          ) : (
            <>
              {/* Language filter tabs */}
              {(() => {
                const languages = [...new Set(product.variants!.map((v) => v.language || "en"))];
                if (languages.length > 1) {
                  return (
                    <div className="flex flex-wrap items-center gap-2">
                      <Globe className="h-4 w-4 text-zinc-500" />
                      <button
                        onClick={() => setCopyLangTab("all")}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                          copyLangTab === "all"
                            ? "border-violet-500 bg-violet-500/20 text-violet-300"
                            : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                        }`}
                      >
                        All
                      </button>
                      {languages.map((lang) => (
                        <button
                          key={lang}
                          onClick={() => setCopyLangTab(lang)}
                          className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                            copyLangTab === lang
                              ? "border-violet-500 bg-violet-500/20 text-violet-300"
                              : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                          }`}
                        >
                          {LANGUAGE_LABELS[lang] || lang}
                        </button>
                      ))}
                    </div>
                  );
                }
                return null;
              })()}

              {product.variants
                .filter((v) => copyLangTab === "all" || (v.language || "en") === copyLangTab)
                .map((v) => (
                <div key={v.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
                  <div className="flex flex-wrap items-center gap-3 border-b border-zinc-800 pb-4">
                    <span className="rounded bg-violet-500/20 px-2.5 py-1 text-sm font-semibold text-violet-300">
                      {v.platform}
                    </span>
                    {v.language && v.language !== "en" && (
                      <span className="rounded bg-sky-500/20 px-2 py-0.5 text-xs font-medium text-sky-300">
                        {LANGUAGE_LABELS[v.language] || v.language}
                      </span>
                    )}
                    {v.ceo_score > 0 && <CeoScoreBadge score={v.ceo_score} />}
                    <StatusBadge status={v.ceo_status} />
                    {v.price && (
                      <span className="text-sm font-semibold text-emerald-400">{v.price}</span>
                    )}
                  </div>

                  <div className="mt-4 space-y-4">
                    {/* Title */}
                    {v.title && (
                      <div>
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Title</label>
                          <CopyButton text={v.title} label="Title" />
                        </div>
                        <p className="mt-1 rounded-lg bg-zinc-800/50 p-3 text-sm text-zinc-200">{v.title}</p>
                      </div>
                    )}

                    {/* Description */}
                    {v.description && (
                      <div>
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Description</label>
                          <CopyButton text={v.description} label="Description" />
                        </div>
                        <p className="mt-1 whitespace-pre-wrap rounded-lg bg-zinc-800/50 p-3 text-sm text-zinc-200">
                          {v.description}
                        </p>
                      </div>
                    )}

                    {/* Tags */}
                    {v.tags && v.tags.length > 0 && (
                      <div>
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tags</label>
                          <CopyButton text={v.tags.join(", ")} label="Tags" />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {v.tags.map((tag, i) => (
                            <span key={i} className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs text-zinc-300">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* A/B Test Button */}
                    <ABTestButton variantId={v.id} />

                    {/* CEO Feedback */}
                    {v.ceo_feedback && (
                      <div>
                        <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">CEO Feedback</label>
                        <p className="mt-1 rounded-lg border border-zinc-700 bg-zinc-800/30 p-3 text-sm italic text-zinc-400">
                          {v.ceo_feedback}
                        </p>
                      </div>
                    )}

                    {/* Images */}
                    {v.image_urls && v.image_urls.length > 0 && (
                      <div>
                        <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Images</label>
                        <div className="mt-2 flex flex-wrap gap-3">
                          {v.image_urls.map((url, i) => {
                            const fullUrl = url.startsWith("http") ? url : `${apiUrl}${url}`;
                            return (
                              <div key={i} className="group relative overflow-hidden rounded-lg border border-zinc-700">
                                <img
                                  src={fullUrl}
                                  alt={`Product image ${i + 1}`}
                                  className="h-24 w-24 object-cover"
                                />
                                <a
                                  href={fullUrl}
                                  download
                                  className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 transition-opacity group-hover:opacity-100"
                                >
                                  <Download className="h-5 w-5 text-white" />
                                </a>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {tab === "copy" && product.variants && product.variants.length > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <FlaskConical className="h-4 w-4 text-violet-400" />
          <span className="text-sm text-zinc-400">Want to test which title converts best?</span>
          <span className="text-xs text-zinc-500">Click the A/B Test button on any variant above.</span>
        </div>
      )}

      {tab === "research" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          {Object.keys(product.research_data).length === 0 ? (
            <p className="text-zinc-400">No research data available yet.</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(product.research_data).map(([key, value]) => (
                <div key={key}>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                    {key.replace(/_/g, " ")}
                  </label>
                  <div className="mt-1 rounded-lg bg-zinc-800/50 p-3 text-sm text-zinc-200">
                    {typeof value === "object" ? (
                      <pre className="whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                    ) : (
                      String(value)
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {Object.keys(product.trend_data).length > 0 && (
            <div className="mt-6 border-t border-zinc-800 pt-6">
              <h3 className="mb-4 text-sm font-semibold text-zinc-300">Trend Data</h3>
              {Object.entries(product.trend_data).map(([key, value]) => (
                <div key={key} className="mb-3">
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                    {key.replace(/_/g, " ")}
                  </label>
                  <div className="mt-1 rounded-lg bg-zinc-800/50 p-3 text-sm text-zinc-200">
                    {typeof value === "object" ? (
                      <pre className="whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                    ) : (
                      String(value)
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "social" && (
        <SocialPostsTab product={product} setProduct={setProduct} />
      )}

      {tab === "email" && (
        <EmailTab product={product} />
      )}

      {tab === "pricing" && (
        <PricingTab product={product} />
      )}

      {tab === "repurpose" && (
        <RepurposeTab product={product} />
      )}

      {tab === "voiceover" && (
        <VoiceOverTab product={product} />
      )}

      {tab === "logs" && (
        <div className="space-y-3">
          {(!product.pipeline_logs || product.pipeline_logs.length === 0) ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <p className="text-zinc-400">No pipeline logs yet.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50">
              {product.pipeline_logs.map((log, i) => (
                <div
                  key={log.id}
                  className={`flex items-start gap-4 p-4 ${
                    i < product.pipeline_logs!.length - 1 ? "border-b border-zinc-800" : ""
                  }`}
                >
                  <div className="mt-1 flex-shrink-0">
                    <div
                      className={`h-2.5 w-2.5 rounded-full ${
                        log.status === "success"
                          ? "bg-emerald-400"
                          : log.status === "running"
                            ? "bg-blue-400 animate-pulse"
                            : log.status === "error"
                              ? "bg-red-400"
                              : "bg-zinc-500"
                      }`}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-zinc-200">{log.agent}</span>
                      {log.ai_provider && (
                        <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                          {log.ai_provider}
                        </span>
                      )}
                      <StatusBadge status={log.status} />
                    </div>
                    {log.message && (
                      <p className="mt-1 text-sm text-zinc-400">{log.message}</p>
                    )}
                    <p className="mt-1 text-xs text-zinc-600">
                      {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
