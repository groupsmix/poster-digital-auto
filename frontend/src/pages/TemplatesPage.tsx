import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2, FileText, Package, Sparkles, X, Check, Copy } from "lucide-react";
import {
  fetchTemplates, createTemplate, deleteTemplate, createProductFromTemplate,
  fetchBundles, createBundle, deleteBundle, generateBundleListing,
  fetchProducts,
} from "@/lib/api";
import type { ProductTemplate, ProductBundle, Product } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function TemplatesPage() {
  const [tab, setTab] = useState<"templates" | "bundles">("templates");
  const [templates, setTemplates] = useState<ProductTemplate[]>([]);
  const [bundles, setBundles] = useState<ProductBundle[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  // Template form
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("digital");
  const [formTone, setFormTone] = useState("");
  const [formPriceMin, setFormPriceMin] = useState(5);
  const [formPriceMax, setFormPriceMax] = useState(15);
  const [formBrief, setFormBrief] = useState("");
  const [adding, setAdding] = useState(false);

  // Bundle form
  const [showBundleForm, setShowBundleForm] = useState(false);
  const [bundleName, setBundleName] = useState("");
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>([]);
  const [bundleDiscount, setBundleDiscount] = useState(25);
  const [addingBundle, setAddingBundle] = useState(false);

  // Create product from template
  const [createFromId, setCreateFromId] = useState<number | null>(null);
  const [productName, setProductName] = useState("");

  async function loadData() {
    try {
      const [tRes, bRes, pRes] = await Promise.all([
        fetchTemplates(),
        fetchBundles(),
        fetchProducts(),
      ]);
      setTemplates(tRes.templates);
      setBundles(bRes.bundles);
      setProducts(pRes.products);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreateTemplate() {
    if (!formName.trim()) { toast.error("Name is required"); return; }
    setAdding(true);
    try {
      await createTemplate({
        name: formName, product_type: formType, tone: formTone,
        price_min: formPriceMin, price_max: formPriceMax,
        brief_template: formBrief,
      });
      toast.success("Template created!");
      setShowForm(false);
      setFormName(""); setFormTone(""); setFormBrief("");
      setLoading(true); loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create template");
    } finally { setAdding(false); }
  }

  async function handleDeleteTemplate(id: number) {
    if (!confirm("Delete this template?")) return;
    try {
      await deleteTemplate(id);
      toast.success("Template deleted");
      setTemplates(prev => prev.filter(t => t.id !== id));
    } catch (e) { toast.error(e instanceof Error ? e.message : "Delete failed"); }
  }

  async function handleCreateFromTemplate(templateId: number) {
    if (!productName.trim()) { toast.error("Product name required"); return; }
    try {
      const res = await createProductFromTemplate(templateId, productName);
      toast.success(res.message);
      setCreateFromId(null); setProductName("");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  async function handleCreateBundle() {
    if (!bundleName.trim() || selectedProductIds.length < 2) {
      toast.error("Name and at least 2 products required"); return;
    }
    setAddingBundle(true);
    try {
      await createBundle({
        name: bundleName, product_ids: selectedProductIds,
        discount_percent: bundleDiscount,
      });
      toast.success("Bundle created!");
      setShowBundleForm(false); setBundleName(""); setSelectedProductIds([]);
      setLoading(true); loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally { setAddingBundle(false); }
  }

  async function handleDeleteBundle(id: number) {
    if (!confirm("Delete this bundle?")) return;
    try {
      await deleteBundle(id);
      toast.success("Bundle deleted");
      setBundles(prev => prev.filter(b => b.id !== id));
    } catch (e) { toast.error(e instanceof Error ? e.message : "Delete failed"); }
  }

  async function handleGenerateListing(bundleId: number) {
    try {
      const res = await generateBundleListing(bundleId);
      toast.success(res.message || "Listing generated!");
      setLoading(true); loadData();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Templates & Bundles</h1>
          <p className="mt-1 text-sm text-zinc-400">Reusable product templates and bundle packs</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setTab("templates")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "templates" ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            <FileText className="inline h-4 w-4 mr-1" /> Templates ({templates.length})
          </button>
          <button onClick={() => setTab("bundles")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "bundles" ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            <Package className="inline h-4 w-4 mr-1" /> Bundles ({bundles.length})
          </button>
        </div>
      </div>

      {tab === "templates" && (
        <>
          <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "Cancel" : "New Template"}
          </button>

          {showForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200">Create Template</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Type</label>
                  <select value={formType} onChange={e => setFormType(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                    <option value="digital">Digital</option>
                    <option value="template">Template</option>
                    <option value="course">Course</option>
                    <option value="ebook">E-book</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tone</label>
                  <input type="text" value={formTone} onChange={e => setFormTone(e.target.value)} placeholder="professional, casual..." className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Min Price</label>
                    <input type="number" value={formPriceMin} onChange={e => setFormPriceMin(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Price</label>
                    <input type="number" value={formPriceMax} onChange={e => setFormPriceMax(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Brief Template</label>
                <textarea value={formBrief} onChange={e => setFormBrief(e.target.value)} rows={3} placeholder="Template brief for product generation..." className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y" />
              </div>
              <button onClick={handleCreateTemplate} disabled={adding} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
                {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {adding ? "Creating..." : "Save Template"}
              </button>
            </div>
          )}

          {templates.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <FileText className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No templates yet. Create one to speed up product creation.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {templates.map(t => (
                <div key={t.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <h3 className="font-semibold text-zinc-200">{t.name}</h3>
                    <div className="flex gap-1">
                      <button onClick={() => setCreateFromId(createFromId === t.id ? null : t.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-violet-900/50 hover:text-violet-400">
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDeleteTemplate(t.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {createFromId === t.id && (
                    <div className="mt-3 flex gap-2">
                      <input type="text" value={productName} onChange={e => setProductName(e.target.value)} placeholder="Product name..." className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
                      <button onClick={() => handleCreateFromTemplate(t.id)} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-500">Create</button>
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-zinc-500">
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-400">{t.product_type}</span>
                    {t.tone && <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-400">{t.tone}</span>}
                    <span>${t.price_min} - ${t.price_max}</span>
                    <span>Used {t.times_used}x</span>
                  </div>
                  {t.brief_template && <p className="mt-2 text-xs text-zinc-500 line-clamp-2">{t.brief_template}</p>}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "bundles" && (
        <>
          <button onClick={() => setShowBundleForm(!showBundleForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showBundleForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showBundleForm ? "Cancel" : "New Bundle"}
          </button>

          {showBundleForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200">Create Bundle</h3>
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Bundle Name</label>
                <input type="text" value={bundleName} onChange={e => setBundleName(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Discount %</label>
                <input type="number" value={bundleDiscount} onChange={e => setBundleDiscount(Number(e.target.value))} className="mt-1 w-32 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Select Products</label>
                <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
                  {products.map(p => (
                    <label key={p.id} className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 cursor-pointer hover:border-zinc-600">
                      <input type="checkbox" checked={selectedProductIds.includes(p.id)} onChange={e => {
                        if (e.target.checked) setSelectedProductIds(prev => [...prev, p.id]);
                        else setSelectedProductIds(prev => prev.filter(id => id !== p.id));
                      }} className="rounded border-zinc-600" />
                      <span className="text-sm text-zinc-300">{p.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button onClick={handleCreateBundle} disabled={addingBundle} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
                {addingBundle ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {addingBundle ? "Creating..." : "Create Bundle"}
              </button>
            </div>
          )}

          {bundles.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <Package className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No bundles yet. Bundle products together for higher sales.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {bundles.map(b => (
                <div key={b.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-200">{b.name}</h3>
                      <div className="mt-2 flex flex-wrap gap-3 text-sm text-zinc-400">
                        <span>Individual: <span className="text-zinc-200">${b.individual_total.toFixed(2)}</span></span>
                        <span>Bundle: <span className="text-emerald-400">${b.bundle_price.toFixed(2)}</span></span>
                        <span>Save {b.discount_percent}%</span>
                        <span className={`rounded px-2 py-0.5 text-xs ${b.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"}`}>{b.status}</span>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => handleGenerateListing(b.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-violet-900/50 hover:text-violet-400" title="Generate AI listing">
                        <Sparkles className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDeleteBundle(b.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {b.items && b.items.length > 0 && (
                    <div className="mt-3 text-xs text-zinc-500">
                      {b.items.length} products in bundle
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
