import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Send, Edit3, Check, X, ExternalLink, Filter } from "lucide-react";
import { fetchSocialPosts, updateSocialPost, triggerAutoPost, fetchAutoPostConfig } from "@/lib/api";
import type { SocialPost, AutoPostConfig } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

const PLATFORMS = [
  "All", "Reddit", "Tumblr", "Twitter", "Pinterest", "Telegram",
  "Instagram", "TikTok", "Facebook", "Quora", "LinkedIn", "Threads",
];

const STATUS_FILTERS = ["All", "draft", "posted", "error", "verified"];

const AUTO_POST_PLATFORMS = ["Telegram", "Tumblr", "Pinterest"];

export default function SocialPostsPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [platformFilter, setPlatformFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [autoPostConfig, setAutoPostConfig] = useState<AutoPostConfig | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editCaption, setEditCaption] = useState("");
  const [postingId, setPostingId] = useState<number | null>(null);

  useEffect(() => {
    loadPosts();
    fetchAutoPostConfig().then(setAutoPostConfig).catch(() => {});
  }, [platformFilter, statusFilter]);

  function loadPosts() {
    setLoading(true);
    const filters: { platform?: string; post_status?: string } = {};
    if (platformFilter !== "All") filters.platform = platformFilter;
    if (statusFilter !== "All") filters.post_status = statusFilter;
    fetchSocialPosts(filters)
      .then((data) => setPosts(data.posts))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }

  function handleCopy(text: string, label: string) {
    navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied!`));
  }

  async function handleSaveEdit(id: number) {
    try {
      const updated = await updateSocialPost(id, { caption: editCaption });
      setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, ...updated } : p)));
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
      setPosts((prev) =>
        prev.map((p) =>
          p.id === id ? { ...p, post_status: "posted", post_url: result.post_url } : p,
        ),
      );
      toast.success(`Posted to ${result.platform}!`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Auto-post failed";
      toast.error(msg);
      setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, post_status: "error" } : p)));
    } finally {
      setPostingId(null);
    }
  }

  function isAutoPostAvailable(platform: string): boolean {
    if (!autoPostConfig) return false;
    const key = platform.toLowerCase() as keyof AutoPostConfig;
    return AUTO_POST_PLATFORMS.includes(platform) && autoPostConfig[key]?.configured === true;
  }

  // Group posts by product
  const grouped = posts.reduce<Record<number, SocialPost[]>>((acc, post) => {
    if (!acc[post.product_id]) acc[post.product_id] = [];
    acc[post.product_id].push(post);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Social Posts</h1>
          <p className="text-sm text-zinc-400">Manage captions and auto-posting across all platforms</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <span>{posts.length} posts</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-zinc-500" />
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">Platform:</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                platformFilter === p
                  ? "bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/50"
                  : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 ml-4">
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">Status:</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/50"
                  : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
              }`}
            >
              {s === "All" ? "All" : s}
            </button>
          ))}
        </div>
      </div>

      {/* Auto-post config status */}
      {autoPostConfig && (
        <div className="flex flex-wrap gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">Auto-Post:</span>
          {AUTO_POST_PLATFORMS.map((p) => {
            const key = p.toLowerCase() as keyof AutoPostConfig;
            const configured = autoPostConfig[key]?.configured;
            return (
              <span
                key={p}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  configured
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-zinc-800 text-zinc-500"
                }`}
              >
                {configured ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                {p}
              </span>
            );
          })}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : posts.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <p className="text-zinc-400">No social posts found. Generate captions from a product page.</p>
        </div>
      ) : (
        Object.entries(grouped).map(([productId, productPosts]) => (
          <div key={productId} className="space-y-3">
            <div className="flex items-center gap-2">
              <Link
                to={`/products/${productId}`}
                className="text-sm font-medium text-violet-400 hover:text-violet-300"
              >
                Product #{productId}
              </Link>
              <span className="text-xs text-zinc-500">({productPosts.length} captions)</span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {productPosts.map((post) => (
                <div
                  key={post.id}
                  className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/50 p-4"
                >
                  {/* Header */}
                  <div className="flex items-center justify-between gap-2 pb-3 border-b border-zinc-800">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-fuchsia-500/20 px-2 py-0.5 text-xs font-semibold text-fuchsia-300">
                        {post.platform}
                      </span>
                      <StatusBadge status={post.post_status} />
                    </div>
                    <div className="flex items-center gap-1">
                      {post.post_url && (
                        <a
                          href={post.post_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded p-1 text-zinc-400 hover:text-zinc-200"
                          title="View post"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Caption */}
                  <div className="flex-1 mt-3">
                    {editingId === post.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={editCaption}
                          onChange={(e) => setEditCaption(e.target.value)}
                          className="w-full rounded-lg bg-zinc-800 p-3 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none min-h-[100px] resize-y"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveEdit(post.id)}
                            className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-500"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="rounded-md bg-zinc-700 px-3 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-600"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap text-sm text-zinc-300 line-clamp-6">
                        {post.caption}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-zinc-800">
                    <button
                      onClick={() => handleCopy(post.caption, post.platform)}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(post.id);
                        setEditCaption(post.caption);
                      }}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
                    >
                      <Edit3 className="h-3 w-3" />
                      Edit
                    </button>
                    {AUTO_POST_PLATFORMS.includes(post.platform) && (
                      <button
                        onClick={() => handleAutoPost(post.id)}
                        disabled={postingId === post.id || !isAutoPostAvailable(post.platform)}
                        className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                          isAutoPostAvailable(post.platform)
                            ? "bg-violet-600 text-white hover:bg-violet-500"
                            : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                        }`}
                        title={
                          isAutoPostAvailable(post.platform)
                            ? `Auto-post to ${post.platform}`
                            : `${post.platform} API not configured`
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

                  {/* Timestamp */}
                  <p className="mt-2 text-xs text-zinc-600">
                    {post.posted_at
                      ? `Posted: ${new Date(post.posted_at).toLocaleString()}`
                      : `Created: ${new Date(post.created_at).toLocaleString()}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
