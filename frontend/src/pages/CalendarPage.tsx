import { useEffect, useState, useCallback, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Sparkles,
  Clock,
  X,
  GripVertical,
  Layers,
  Lightbulb,
  Trash2,
} from "lucide-react";
import {
  fetchCalendarPosts,
  reschedulePost,
  unschedulePost,
  autoSchedulePosts,
  batchScheduleProducts,
  fetchScheduleSuggestions,
  fetchProducts,
  fetchSocialPosts,
  schedulePost,
} from "@/lib/api";
import type { CalendarPost, ScheduleSuggestion, Product, SocialPost } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

// Platform colors for calendar display
const PLATFORM_COLORS: Record<string, string> = {
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
  Gumroad: "#FF90E8",
  Payhip: "#00B4D8",
  "Lemon Squeezy": "#FFC233",
};

function getPlatformColor(platform: string): string {
  return PLATFORM_COLORS[platform] || "#6B7280";
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function formatTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function CalendarPage() {
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [posts, setPosts] = useState<CalendarPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<ScheduleSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [autoScheduling, setAutoScheduling] = useState(false);

  // Batch scheduling state
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>([]);
  const [batchDays, setBatchDays] = useState(30);
  const [batchPostsPerDay, setBatchPostsPerDay] = useState(1);
  const [batchScheduling, setBatchScheduling] = useState(false);

  // Schedule individual post state
  const [unscheduledPosts, setUnscheduledPosts] = useState<SocialPost[]>([]);
  const [schedulePostId, setSchedulePostId] = useState<number | null>(null);
  const [scheduleDateTime, setScheduleDateTime] = useState("");

  // Drag state
  const dragPostRef = useRef<CalendarPost | null>(null);
  const [dragOverDay, setDragOverDay] = useState<string | null>(null);

  const loadPosts = useCallback(() => {
    setLoading(true);
    const startDate = new Date(currentYear, currentMonth, 1);
    const endDate = new Date(currentYear, currentMonth + 1, 0, 23, 59, 59);
    fetchCalendarPosts(formatDate(startDate), formatDate(endDate) + "T23:59:59")
      .then((data) => setPosts(data.posts))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [currentYear, currentMonth]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  function prevMonth() {
    if (currentMonth === 0) {
      setCurrentYear(currentYear - 1);
      setCurrentMonth(11);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  }

  function nextMonth() {
    if (currentMonth === 11) {
      setCurrentYear(currentYear + 1);
      setCurrentMonth(0);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  }

  function goToToday() {
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth());
  }

  // Group posts by date
  const postsByDate: Record<string, CalendarPost[]> = {};
  posts.forEach((post) => {
    if (post.scheduled_at) {
      const dateKey = post.scheduled_at.split("T")[0];
      if (!postsByDate[dateKey]) postsByDate[dateKey] = [];
      postsByDate[dateKey].push(post);
    }
  });

  // Selected day's posts
  const selectedDayPosts = selectedDay ? postsByDate[selectedDay] || [] : [];

  // Handle drag-and-drop reschedule
  function handleDragStart(post: CalendarPost) {
    dragPostRef.current = post;
  }

  function handleDragOver(e: React.DragEvent, dateKey: string) {
    e.preventDefault();
    setDragOverDay(dateKey);
  }

  function handleDragLeave() {
    setDragOverDay(null);
  }

  async function handleDrop(e: React.DragEvent, targetDate: string) {
    e.preventDefault();
    setDragOverDay(null);
    const post = dragPostRef.current;
    if (!post) return;

    // Keep the same time, just change the date
    const oldTime = post.scheduled_at.includes("T")
      ? post.scheduled_at.split("T")[1]
      : "10:00:00";
    const newScheduledAt = `${targetDate}T${oldTime}`;

    try {
      await reschedulePost(post.id, newScheduledAt);
      toast.success(`Rescheduled to ${targetDate}`);
      loadPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Reschedule failed";
      toast.error(msg);
    }
    dragPostRef.current = null;
  }

  async function handleUnschedule(postId: number) {
    try {
      await unschedulePost(postId);
      toast.success("Post unscheduled");
      loadPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unschedule failed";
      toast.error(msg);
    }
  }

  async function handleAutoSchedule() {
    setAutoScheduling(true);
    try {
      const result = await autoSchedulePosts({
        start_date: formatDate(new Date(currentYear, currentMonth, 1)),
        days_span: getDaysInMonth(currentYear, currentMonth),
        posts_per_day: 2,
      });
      toast.success(result.message);
      loadPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Auto-schedule failed";
      toast.error(msg);
    } finally {
      setAutoScheduling(false);
    }
  }

  function openSuggestions() {
    fetchScheduleSuggestions()
      .then((data) => {
        setSuggestions(data.suggestions);
        setShowSuggestions(true);
      })
      .catch((e) => toast.error(e.message));
  }

  function openBatchModal() {
    fetchProducts()
      .then((data) => {
        setProducts(data.products);
        setShowBatchModal(true);
      })
      .catch((e) => toast.error(e.message));
  }

  async function handleBatchSchedule() {
    if (selectedProductIds.length === 0) {
      toast.error("Select at least one product");
      return;
    }
    setBatchScheduling(true);
    try {
      const result = await batchScheduleProducts({
        product_ids: selectedProductIds,
        days_span: batchDays,
        posts_per_day: batchPostsPerDay,
      });
      toast.success(result.message);
      setShowBatchModal(false);
      setSelectedProductIds([]);
      loadPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Batch schedule failed";
      toast.error(msg);
    } finally {
      setBatchScheduling(false);
    }
  }

  function openScheduleModal(day: string) {
    setScheduleDateTime(`${day}T10:00`);
    fetchSocialPosts({ post_status: "pending" })
      .then((data) => {
        const pending = data.posts.filter((p) => !p.scheduled_at);
        setUnscheduledPosts(pending);
        setShowScheduleModal(true);
      })
      .catch((e) => toast.error(e.message));
  }

  async function handleSchedulePost() {
    if (!schedulePostId || !scheduleDateTime) {
      toast.error("Select a post and date/time");
      return;
    }
    try {
      await schedulePost(schedulePostId, scheduleDateTime.replace("T", "T") + ":00");
      toast.success("Post scheduled!");
      setShowScheduleModal(false);
      setSchedulePostId(null);
      loadPosts();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Schedule failed";
      toast.error(msg);
    }
  }

  // Build calendar grid
  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
  const calendarDays: (number | null)[] = [];

  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d);
  while (calendarDays.length % 7 !== 0) calendarDays.push(null);

  const todayStr = formatDate(today);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CalendarIcon className="h-6 w-6 text-violet-400" />
            Content Calendar
          </h1>
          <p className="text-sm text-zinc-400">
            Schedule and manage posts across all platforms
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openSuggestions}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            <Lightbulb className="h-4 w-4 text-amber-400" />
            AI Tips
          </button>
          <button
            onClick={openBatchModal}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            <Layers className="h-4 w-4 text-blue-400" />
            Batch Schedule
          </button>
          <button
            onClick={handleAutoSchedule}
            disabled={autoScheduling}
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-500 transition-colors disabled:opacity-50"
          >
            {autoScheduling ? (
              <Spinner className="h-4 w-4" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Auto-Schedule
          </button>
        </div>
      </div>

      {/* Month navigation */}
      <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3">
        <button
          onClick={prevMonth}
          className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">
            {MONTH_NAMES[currentMonth]} {currentYear}
          </h2>
          <button
            onClick={goToToday}
            className="rounded-md bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            Today
          </button>
        </div>
        <button
          onClick={nextMonth}
          className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Calendar stats */}
      <div className="flex flex-wrap gap-3">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
          <span className="text-xs text-zinc-500">Scheduled</span>
          <p className="text-lg font-semibold text-violet-400">{posts.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
          <span className="text-xs text-zinc-500">Days with posts</span>
          <p className="text-lg font-semibold text-emerald-400">
            {Object.keys(postsByDate).length}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
          <span className="text-xs text-zinc-500">Platforms</span>
          <p className="text-lg font-semibold text-blue-400">
            {new Set(posts.map((p) => p.platform)).size}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : (
        <>
          {/* Calendar Grid */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
            {/* Day headers */}
            <div className="grid grid-cols-7 border-b border-zinc-800">
              {DAY_NAMES.map((day) => (
                <div
                  key={day}
                  className="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wider text-zinc-500"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar cells */}
            <div className="grid grid-cols-7">
              {calendarDays.map((day, idx) => {
                if (day === null) {
                  return (
                    <div
                      key={`empty-${idx}`}
                      className="min-h-28 border-b border-r border-zinc-800/50 bg-zinc-950/30"
                    />
                  );
                }

                const dateKey = `${currentYear}-${String(currentMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                const dayPosts = postsByDate[dateKey] || [];
                const isToday = dateKey === todayStr;
                const isSelected = dateKey === selectedDay;
                const isDragOver = dateKey === dragOverDay;

                return (
                  <div
                    key={dateKey}
                    className={`min-h-28 border-b border-r border-zinc-800/50 p-1.5 cursor-pointer transition-colors ${
                      isToday ? "bg-violet-950/20" : ""
                    } ${isSelected ? "bg-zinc-800/50 ring-1 ring-violet-500/50" : ""} ${
                      isDragOver ? "bg-violet-900/30 ring-1 ring-violet-400/50" : ""
                    } hover:bg-zinc-800/30`}
                    onClick={() => setSelectedDay(dateKey)}
                    onDragOver={(e) => handleDragOver(e, dateKey)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, dateKey)}
                  >
                    {/* Day number */}
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                          isToday
                            ? "bg-violet-500 text-white"
                            : "text-zinc-400"
                        }`}
                      >
                        {day}
                      </span>
                      {dayPosts.length > 0 && (
                        <span className="text-xs text-zinc-500">
                          {dayPosts.length}
                        </span>
                      )}
                    </div>

                    {/* Post pills */}
                    <div className="space-y-0.5">
                      {dayPosts.slice(0, 3).map((post) => (
                        <div
                          key={post.id}
                          draggable
                          onDragStart={() => handleDragStart(post)}
                          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs truncate cursor-grab active:cursor-grabbing hover:brightness-110 transition-all"
                          style={{
                            backgroundColor: `${getPlatformColor(post.platform)}20`,
                            borderLeft: `2px solid ${getPlatformColor(post.platform)}`,
                          }}
                          title={`${post.platform}: ${post.product_name || "Post #" + post.id}`}
                        >
                          <GripVertical className="h-3 w-3 shrink-0 text-zinc-500" />
                          <span
                            className="font-medium truncate"
                            style={{ color: getPlatformColor(post.platform) }}
                          >
                            {post.platform}
                          </span>
                        </div>
                      ))}
                      {dayPosts.length > 3 && (
                        <div className="text-xs text-zinc-500 pl-1">
                          +{dayPosts.length - 3} more
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected day detail panel */}
          {selectedDay && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                  {new Date(selectedDay + "T12:00:00").toLocaleDateString(undefined, {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openScheduleModal(selectedDay)}
                    className="inline-flex items-center gap-1 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500"
                  >
                    <Clock className="h-3.5 w-3.5" />
                    Add Post
                  </button>
                  <button
                    onClick={() => setSelectedDay(null)}
                    className="rounded p-1 text-zinc-400 hover:text-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {selectedDayPosts.length === 0 ? (
                <p className="text-sm text-zinc-500">
                  No posts scheduled for this day.
                </p>
              ) : (
                <div className="space-y-3">
                  {selectedDayPosts.map((post) => (
                    <div
                      key={post.id}
                      className="rounded-lg border border-zinc-800 bg-zinc-900 p-4"
                      style={{
                        borderLeftWidth: "3px",
                        borderLeftColor: getPlatformColor(post.platform),
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className="rounded px-2 py-0.5 text-xs font-semibold"
                              style={{
                                backgroundColor: `${getPlatformColor(post.platform)}20`,
                                color: getPlatformColor(post.platform),
                              }}
                            >
                              {post.platform}
                            </span>
                            <span className="text-xs text-zinc-500">
                              {post.product_name || `Product #${post.product_id}`}
                            </span>
                            <span className="text-xs text-zinc-600">
                              {formatTime(post.scheduled_at)}
                            </span>
                          </div>
                          <p className="text-sm text-zinc-300 line-clamp-2">
                            {post.caption}
                          </p>
                        </div>
                        <button
                          onClick={() => handleUnschedule(post.id)}
                          className="shrink-0 rounded p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Unschedule"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Platform legend */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(PLATFORM_COLORS)
              .filter(([platform]) =>
                posts.some((p) => p.platform === platform)
              )
              .map(([platform, color]) => (
                <span
                  key={platform}
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
                  style={{
                    backgroundColor: `${color}15`,
                    color: color,
                    border: `1px solid ${color}30`,
                  }}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {platform}
                </span>
              ))}
          </div>
        </>
      )}

      {/* AI Tips Modal */}
      {showSuggestions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-amber-400" />
                AI Posting Tips
              </h3>
              <button
                onClick={() => setShowSuggestions(false)}
                className="rounded p-1 text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="max-h-96 overflow-y-auto space-y-3">
              {suggestions.map((s) => (
                <div
                  key={s.platform}
                  className="rounded-lg border border-zinc-800 p-3"
                  style={{
                    borderLeftWidth: "3px",
                    borderLeftColor: s.color,
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: `${s.color}20`,
                        color: s.color,
                      }}
                    >
                      {s.platform}
                    </span>
                    <span className="text-xs text-zinc-500">{s.timezone}</span>
                  </div>
                  <p className="text-sm text-zinc-300 mb-2">{s.tip}</p>
                  <div className="flex flex-wrap gap-1">
                    {s.best_days.map((day) => (
                      <span
                        key={day}
                        className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400"
                      >
                        {day}
                      </span>
                    ))}
                    {s.best_hours.map((h) => (
                      <span
                        key={h}
                        className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-emerald-400"
                      >
                        {h}:00
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Batch Schedule Modal */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Layers className="h-5 w-5 text-blue-400" />
                Batch Schedule Products
              </h3>
              <button
                onClick={() => setShowBatchModal(false)}
                className="rounded p-1 text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Select Products
                </label>
                <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg border border-zinc-800 p-2">
                  {products.length === 0 ? (
                    <p className="text-sm text-zinc-500 p-2">No products found</p>
                  ) : (
                    products.map((p) => (
                      <label
                        key={p.id}
                        className="flex items-center gap-2 rounded p-2 hover:bg-zinc-800 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedProductIds.includes(p.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedProductIds([...selectedProductIds, p.id]);
                            } else {
                              setSelectedProductIds(
                                selectedProductIds.filter((id) => id !== p.id)
                              );
                            }
                          }}
                          className="rounded border-zinc-600 bg-zinc-800 text-violet-500 focus:ring-violet-500"
                        />
                        <span className="text-sm text-zinc-300 truncate">
                          {p.name}
                        </span>
                        <span className="ml-auto text-xs text-zinc-500">
                          #{p.id}
                        </span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">
                    Days to spread across
                  </label>
                  <input
                    type="number"
                    value={batchDays}
                    onChange={(e) => setBatchDays(Number(e.target.value))}
                    min={1}
                    max={365}
                    className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">
                    Posts per day
                  </label>
                  <input
                    type="number"
                    value={batchPostsPerDay}
                    onChange={(e) => setBatchPostsPerDay(Number(e.target.value))}
                    min={1}
                    max={10}
                    className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                  />
                </div>
              </div>

              <p className="text-xs text-zinc-500">
                Schedule {selectedProductIds.length} product(s) across {batchDays} days,
                {" "}{batchPostsPerDay} post(s) per day. AI will pick optimal times per platform.
              </p>

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowBatchModal(false)}
                  className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBatchSchedule}
                  disabled={batchScheduling || selectedProductIds.length === 0}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {batchScheduling ? (
                    <Spinner className="h-4 w-4" />
                  ) : (
                    `Schedule ${selectedProductIds.length} Products`
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Individual Post Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Clock className="h-5 w-5 text-violet-400" />
                Schedule a Post
              </h3>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="rounded p-1 text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Select Post
                </label>
                <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg border border-zinc-800 p-2">
                  {unscheduledPosts.length === 0 ? (
                    <p className="text-sm text-zinc-500 p-2">
                      No unscheduled posts available
                    </p>
                  ) : (
                    unscheduledPosts.map((p) => (
                      <label
                        key={p.id}
                        className={`flex items-center gap-2 rounded p-2 cursor-pointer transition-colors ${
                          schedulePostId === p.id
                            ? "bg-violet-500/10 ring-1 ring-violet-500/50"
                            : "hover:bg-zinc-800"
                        }`}
                      >
                        <input
                          type="radio"
                          name="schedulePost"
                          checked={schedulePostId === p.id}
                          onChange={() => setSchedulePostId(p.id)}
                          className="text-violet-500 focus:ring-violet-500"
                        />
                        <span
                          className="rounded px-1.5 py-0.5 text-xs font-semibold"
                          style={{
                            backgroundColor: `${getPlatformColor(p.platform)}20`,
                            color: getPlatformColor(p.platform),
                          }}
                        >
                          {p.platform}
                        </span>
                        <span className="text-sm text-zinc-300 truncate flex-1">
                          {p.caption?.substring(0, 60)}...
                        </span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Date & Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduleDateTime}
                  onChange={(e) => setScheduleDateTime(e.target.value)}
                  className="w-full rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowScheduleModal(false)}
                  className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSchedulePost}
                  disabled={!schedulePostId || !scheduleDateTime}
                  className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                >
                  Schedule
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
