import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlusCircle, Rocket } from "lucide-react";
import { createProduct, generateProduct } from "@/lib/api";
import { toast } from "sonner";
import Spinner from "@/components/Spinner";

const SELLING_PLATFORMS = ["Gumroad", "Payhip", "Lemon Squeezy"];
const SOCIAL_PLATFORMS = ["Reddit", "Tumblr", "Twitter", "Pinterest", "Telegram", "Instagram", "TikTok", "Facebook", "Quora"];

export default function NewProductPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [productType, setProductType] = useState("digital");
  const [brief, setBrief] = useState("");
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [planMode, setPlanMode] = useState("A");
  const [saving, setSaving] = useState(false);

  function togglePlatform(p: string) {
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  }

  async function handleCreate(andGenerate: boolean) {
    if (!name.trim()) {
      toast.error("Product name is required");
      return;
    }
    setSaving(true);
    try {
      const product = await createProduct({
        name: name.trim(),
        product_type: productType,
        brief: brief.trim(),
        target_platforms: platforms,
        target_languages: ["en"],
        status: "pending",
        plan_mode: planMode,
      });
      toast.success(`Product "${product.name}" created!`);

      if (andGenerate) {
        try {
          await generateProduct(product.id);
          toast.success("AI pipeline triggered!");
        } catch {
          toast.error("Product created, but pipeline trigger failed. The endpoint may not be implemented yet.");
        }
      }

      navigate(`/products/${product.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create product");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold">New Product</h1>
        <p className="mt-1 text-zinc-400">Create a new digital product and let AI handle the rest</p>
      </div>

      <div className="space-y-6 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        {/* Product Name */}
        <div>
          <label className="block text-sm font-medium text-zinc-300">Product Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. 2026 Minimalist Digital Planner"
            className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-zinc-100 placeholder-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>

        {/* Product Type */}
        <div>
          <label className="block text-sm font-medium text-zinc-300">Product Type</label>
          <select
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-zinc-100 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="digital">Digital Product</option>
            <option value="template">Template</option>
            <option value="ebook">E-Book</option>
            <option value="course">Course</option>
            <option value="printable">Printable</option>
          </select>
        </div>

        {/* Brief Description */}
        <div>
          <label className="block text-sm font-medium text-zinc-300">Brief Description</label>
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Describe your product idea in a few sentences..."
            rows={3}
            className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-zinc-100 placeholder-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>

        {/* Platform Selection */}
        <div>
          <label className="block text-sm font-medium text-zinc-300">Selling Platforms</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {SELLING_PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                  platforms.includes(p)
                    ? "border-violet-500 bg-violet-500/20 text-violet-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-zinc-300">Social Platforms</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {SOCIAL_PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                  platforms.includes(p)
                    ? "border-fuchsia-500 bg-fuchsia-500/20 text-fuchsia-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Plan Mode Toggle */}
        <div>
          <label className="block text-sm font-medium text-zinc-300">Plan Mode</label>
          <div className="mt-2 flex gap-3">
            <button
              type="button"
              onClick={() => setPlanMode("A")}
              className={`flex-1 rounded-lg border p-3 text-left transition-colors ${
                planMode === "A"
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-zinc-700 bg-zinc-800 hover:border-zinc-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${planMode === "A" ? "bg-violet-500" : "bg-zinc-600"}`} />
                <span className="font-medium text-zinc-200">Plan A: Draft</span>
              </div>
              <p className="mt-1 text-sm text-zinc-400">Review and approve before publishing</p>
            </button>
            <button
              type="button"
              onClick={() => setPlanMode("B")}
              className={`flex-1 rounded-lg border p-3 text-left transition-colors ${
                planMode === "B"
                  ? "border-fuchsia-500 bg-fuchsia-500/10"
                  : "border-zinc-700 bg-zinc-800 hover:border-zinc-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${planMode === "B" ? "bg-fuchsia-500" : "bg-zinc-600"}`} />
                <span className="font-medium text-zinc-200">Plan B: Auto</span>
              </div>
              <p className="mt-1 text-sm text-zinc-400">Auto-publish after CEO AI approval</p>
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 pt-2 sm:flex-row">
          <button
            onClick={() => handleCreate(false)}
            disabled={saving}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-700 disabled:opacity-50"
          >
            {saving ? <Spinner className="h-4 w-4" /> : <PlusCircle className="h-4 w-4" />}
            Create Product
          </button>
          <button
            onClick={() => handleCreate(true)}
            disabled={saving}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? <Spinner className="h-4 w-4" /> : <Rocket className="h-4 w-4" />}
            Create & Generate
          </button>
        </div>
      </div>
    </div>
  );
}
