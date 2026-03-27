import { useEffect, useState } from "react";
import { Plus, Search, Trash2, Edit3, Loader2, MessageCircle, Sparkles, X, Check } from "lucide-react";
import { fetchFAQs, createFAQ, updateFAQEntry, deleteFAQEntry, suggestFAQAnswer } from "@/lib/api";
import type { FAQEntry } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function FAQManagerPage() {
  const [faqs, setFaqs] = useState<FAQEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  // Add form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newQuestion, setNewQuestion] = useState("");
  const [newAnswer, setNewAnswer] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [adding, setAdding] = useState(false);

  // AI Suggest
  const [suggestQuestion, setSuggestQuestion] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  // Edit
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editQuestion, setEditQuestion] = useState("");
  const [editAnswer, setEditAnswer] = useState("");
  const [editCategory, setEditCategory] = useState("");

  async function loadFAQs() {
    try {
      const res = await fetchFAQs(
        categoryFilter || undefined,
        search || undefined,
      );
      setFaqs(res.faqs);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load FAQs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFAQs();
  }, [categoryFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch() {
    setLoading(true);
    loadFAQs();
  }

  async function handleAdd() {
    if (!newQuestion.trim() || !newAnswer.trim()) {
      toast.error("Question and answer are required");
      return;
    }
    setAdding(true);
    try {
      const res = await createFAQ(newQuestion, newAnswer, newCategory);
      toast.success(res.message);
      setNewQuestion("");
      setNewAnswer("");
      setNewCategory("general");
      setShowAddForm(false);
      setLoading(true);
      loadFAQs();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to add FAQ");
    } finally {
      setAdding(false);
    }
  }

  async function handleSuggest() {
    if (!suggestQuestion.trim()) {
      toast.error("Enter a question first");
      return;
    }
    setSuggesting(true);
    try {
      const res = await suggestFAQAnswer(suggestQuestion);
      setNewQuestion(suggestQuestion);
      setNewAnswer(res.suggested_answer);
      setNewCategory(res.category);
      setShowAddForm(true);
      setSuggestQuestion("");
      toast.success(`AI suggested an answer (confidence: ${Math.round(res.confidence * 100)}%)`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "AI suggestion failed");
    } finally {
      setSuggesting(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      await updateFAQEntry(id, {
        question: editQuestion,
        answer: editAnswer,
        category: editCategory,
      });
      setEditingId(null);
      toast.success("FAQ updated!");
      setLoading(true);
      loadFAQs();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this FAQ entry?")) return;
    try {
      await deleteFAQEntry(id);
      toast.success("FAQ deleted");
      setFaqs((prev) => prev.filter((f) => f.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  const categories = [...new Set(faqs.map((f) => f.category))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">FAQ Manager</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Manage frequently asked questions with AI-powered answer suggestions
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
        >
          {showAddForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showAddForm ? "Cancel" : "Add FAQ"}
        </button>
      </div>

      {/* AI Suggest Bar */}
      <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-violet-300">AI Answer Suggestion</span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={suggestQuestion}
            onChange={(e) => setSuggestQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSuggest()}
            placeholder="Type a question and AI will draft an answer..."
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
          />
          <button
            onClick={handleSuggest}
            disabled={suggesting}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {suggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {suggesting ? "Thinking..." : "Suggest"}
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200">New FAQ Entry</h3>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Question</label>
            <input
              type="text"
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="What is your return policy?"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Answer</label>
            <textarea
              value={newAnswer}
              onChange={(e) => setNewAnswer(e.target.value)}
              placeholder="Our return policy allows..."
              rows={4}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y"
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Category</label>
            <input
              type="text"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              placeholder="general"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleAdd}
            disabled={adding}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {adding ? "Saving..." : "Save FAQ"}
          </button>
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-1 min-w-[200px] gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search FAQs..."
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
          />
          <button
            onClick={handleSearch}
            className="inline-flex items-center gap-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
          >
            <Search className="h-4 w-4" />
          </button>
        </div>

        {categories.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setCategoryFilter("")}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                !categoryFilter
                  ? "border-violet-500 bg-violet-500/20 text-violet-300"
                  : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
              }`}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  categoryFilter === cat
                    ? "border-violet-500 bg-violet-500/20 text-violet-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* FAQ List */}
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-6 w-6" />
        </div>
      ) : faqs.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <MessageCircle className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">
            No FAQ entries yet. Add one manually or use AI to suggest answers.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {faqs.map((faq) => (
            <div key={faq.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              {editingId === faq.id ? (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={editQuestion}
                    onChange={(e) => setEditQuestion(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
                  />
                  <textarea
                    value={editAnswer}
                    onChange={(e) => setEditAnswer(e.target.value)}
                    rows={4}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none resize-y"
                  />
                  <input
                    type="text"
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdate(faq.id)}
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
                <>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-zinc-200">{faq.question}</h3>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-400">{faq.answer}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => {
                          setEditingId(faq.id);
                          setEditQuestion(faq.question);
                          setEditAnswer(faq.answer);
                          setEditCategory(faq.category);
                        }}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(faq.id)}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-400">{faq.category}</span>
                    <span>Used {faq.times_used} times</span>
                    <span>Updated: {new Date(faq.updated_at).toLocaleDateString()}</span>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
