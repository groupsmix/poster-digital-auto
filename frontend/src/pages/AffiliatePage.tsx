import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2, Users, Link2, X, Check, Sparkles } from "lucide-react";
import {
  fetchAffiliates, createAffiliate, deleteAffiliate,
  fetchReferralLinks, createReferralLink,
  fetchReferralStats, generateMarketingKit,
  fetchProducts,
} from "@/lib/api";
import type { Affiliate, ReferralLink, Product } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function AffiliatePage() {
  const [tab, setTab] = useState<"affiliates" | "links" | "stats">("affiliates");
  const [affiliates, setAffiliates] = useState<Affiliate[]>([]);
  const [links, setLinks] = useState<ReferralLink[]>([]);
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  // Add form
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formRate, setFormRate] = useState(20);
  const [adding, setAdding] = useState(false);

  // Link form
  const [showLinkForm, setShowLinkForm] = useState(false);
  const [linkAffiliateId, setLinkAffiliateId] = useState(0);
  const [linkProductId, setLinkProductId] = useState(0);

  async function loadData() {
    try {
      const [aRes, lRes, sRes, pRes] = await Promise.all([
        fetchAffiliates(),
        fetchReferralLinks(),
        fetchReferralStats(),
        fetchProducts(),
      ]);
      setAffiliates(aRes.affiliates);
      setLinks(lRes.links);
      setStats(sRes);
      setProducts(pRes.products);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate() {
    if (!formName.trim()) { toast.error("Name is required"); return; }
    setAdding(true);
    try {
      await createAffiliate({ name: formName, email: formEmail, commission_rate: formRate });
      toast.success("Affiliate created!");
      setShowForm(false); setFormName(""); setFormEmail("");
      setLoading(true); loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally { setAdding(false); }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this affiliate?")) return;
    try {
      await deleteAffiliate(id);
      toast.success("Affiliate deleted");
      setAffiliates(prev => prev.filter(a => a.id !== id));
    } catch (e) { toast.error(e instanceof Error ? e.message : "Delete failed"); }
  }

  async function handleCreateLink() {
    if (!linkAffiliateId || !linkProductId) { toast.error("Select both affiliate and product"); return; }
    try {
      const res = await createReferralLink(linkAffiliateId, linkProductId);
      toast.success(res.message || "Referral link created!");
      setShowLinkForm(false);
      setLoading(true); loadData();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  async function handleMarketingKit(productId: number) {
    try {
      const res = await generateMarketingKit(productId);
      toast.success(res.message || "Marketing kit generated!");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Affiliate & Referral System</h1>
          <p className="mt-1 text-sm text-zinc-400">Manage affiliates, referral links, and commission tracking</p>
        </div>
        <div className="flex gap-2">
          {(["affiliates", "links", "stats"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-lg px-4 py-2 text-sm font-medium capitalize ${tab === t ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === "affiliates" && (
        <>
          <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "Cancel" : "Add Affiliate"}
          </button>

          {showForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200">New Affiliate</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Email</label>
                  <input type="email" value={formEmail} onChange={e => setFormEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Commission %</label>
                  <input type="number" value={formRate} onChange={e => setFormRate(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
              </div>
              <button onClick={handleCreate} disabled={adding} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
                {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {adding ? "Creating..." : "Save Affiliate"}
              </button>
            </div>
          )}

          {affiliates.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <Users className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No affiliates yet. Add partners to start your referral program.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {affiliates.map(a => (
                <div key={a.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-200">{a.name}</h3>
                      <p className="text-sm text-zinc-400">{a.email || "No email"}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-2 py-0.5 text-xs ${a.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"}`}>{a.status}</span>
                      <button onClick={() => handleDelete(a.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm text-zinc-400">
                    <span>Code: <span className="font-mono text-violet-400">{a.affiliate_code}</span></span>
                    <span>Commission: {a.commission_rate}%</span>
                    <span>Earned: <span className="text-emerald-400">${a.total_earned.toFixed(2)}</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "links" && (
        <>
          <button onClick={() => setShowLinkForm(!showLinkForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showLinkForm ? <X className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
            {showLinkForm ? "Cancel" : "Create Referral Link"}
          </button>

          {showLinkForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Affiliate</label>
                  <select value={linkAffiliateId} onChange={e => setLinkAffiliateId(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                    <option value={0}>Select affiliate...</option>
                    {affiliates.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Product</label>
                  <select value={linkProductId} onChange={e => setLinkProductId(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                    <option value={0}>Select product...</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={handleCreateLink} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500">
                <Check className="h-4 w-4" /> Create Link
              </button>
            </div>
          )}

          {links.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <Link2 className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No referral links yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {links.map(l => (
                <div key={l.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-violet-400">{l.ref_code}</span>
                    <button onClick={() => handleMarketingKit(l.product_id)} className="inline-flex items-center gap-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:bg-violet-900/50 hover:text-violet-400">
                      <Sparkles className="h-3 w-3" /> Marketing Kit
                    </button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-4 text-xs text-zinc-500">
                    {l.affiliate_name && <span>Affiliate: {l.affiliate_name}</span>}
                    {l.product_name && <span>Product: {l.product_name}</span>}
                    <span>Clicks: {l.clicks}</span>
                    <span>Conversions: {l.conversions}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "stats" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <h2 className="text-lg font-semibold text-zinc-200 mb-4">Referral Statistics</h2>
          <pre className="text-sm text-zinc-400 whitespace-pre-wrap">{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
