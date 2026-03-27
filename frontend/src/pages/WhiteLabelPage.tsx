import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2, Building2, X, Check, Crown } from "lucide-react";
import {
  fetchWhiteLabelTiers, fetchTenants, createTenant, deleteTenant,
  fetchWhiteLabelStats,
} from "@/lib/api";
import type { WhiteLabelTenant, WhiteLabelTier } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function WhiteLabelPage() {
  const [tab, setTab] = useState<"tenants" | "tiers" | "stats">("tenants");
  const [tenants, setTenants] = useState<WhiteLabelTenant[]>([]);
  const [tiers, setTiers] = useState<WhiteLabelTier[]>([]);
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);

  // Form
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formBrand, setFormBrand] = useState("");
  const [formColor, setFormColor] = useState("#7c3aed");
  const [formTier, setFormTier] = useState("free");
  const [formDomain, setFormDomain] = useState("");
  const [adding, setAdding] = useState(false);

  async function loadData() {
    try {
      const [tRes, tiRes, sRes] = await Promise.all([
        fetchTenants(),
        fetchWhiteLabelTiers(),
        fetchWhiteLabelStats(),
      ]);
      setTenants(tRes.tenants);
      setTiers(tiRes.tiers);
      setStats(sRes);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate() {
    if (!formName.trim() || !formEmail.trim()) { toast.error("Name and email required"); return; }
    setAdding(true);
    try {
      const res = await createTenant({
        name: formName, owner_email: formEmail, brand_name: formBrand,
        brand_color: formColor, tier: formTier, custom_domain: formDomain,
      });
      toast.success(res.message || "Tenant created!");
      setShowForm(false); setFormName(""); setFormEmail(""); setFormBrand(""); setFormDomain("");
      setLoading(true); loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally { setAdding(false); }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this tenant?")) return;
    try {
      await deleteTenant(id);
      toast.success("Tenant deleted");
      setTenants(prev => prev.filter(t => t.id !== id));
    } catch (e) { toast.error(e instanceof Error ? e.message : "Delete failed"); }
  }

  const tierColors: Record<string, string> = {
    free: "bg-zinc-500/20 text-zinc-400",
    pro: "bg-violet-500/20 text-violet-400",
    agency: "bg-amber-500/20 text-amber-400",
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">White-Label Resell</h1>
          <p className="mt-1 text-sm text-zinc-400">Multi-tenant SaaS management with branded dashboards</p>
        </div>
        <div className="flex gap-2">
          {(["tenants", "tiers", "stats"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-lg px-4 py-2 text-sm font-medium capitalize ${tab === t ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === "tenants" && (
        <>
          <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "Cancel" : "Add Tenant"}
          </button>

          {showForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200">New Tenant</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tenant Name</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Owner Email</label>
                  <input type="email" value={formEmail} onChange={e => setFormEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Brand Name</label>
                  <input type="text" value={formBrand} onChange={e => setFormBrand(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Brand Color</label>
                  <div className="mt-1 flex items-center gap-2">
                    <input type="color" value={formColor} onChange={e => setFormColor(e.target.value)} className="h-10 w-10 rounded border border-zinc-700 bg-zinc-800 cursor-pointer" />
                    <input type="text" value={formColor} onChange={e => setFormColor(e.target.value)} className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tier</label>
                  <select value={formTier} onChange={e => setFormTier(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                    <option value="free">Free</option>
                    <option value="pro">Pro</option>
                    <option value="agency">Agency</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Custom Domain</label>
                  <input type="text" value={formDomain} onChange={e => setFormDomain(e.target.value)} placeholder="app.example.com" className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
                </div>
              </div>
              <button onClick={handleCreate} disabled={adding} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
                {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {adding ? "Creating..." : "Create Tenant"}
              </button>
            </div>
          )}

          {tenants.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <Building2 className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No tenants yet. Create one to start reselling.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {tenants.map(t => (
                <div key={t.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: t.brand_color + "33" }}>
                        <Building2 className="h-4 w-4" style={{ color: t.brand_color }} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-zinc-200">{t.name}</h3>
                        <p className="text-xs text-zinc-500">{t.owner_email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${tierColors[t.tier] || "bg-zinc-700 text-zinc-400"}`}>{t.tier}</span>
                      <span className={`rounded px-2 py-0.5 text-xs ${t.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>{t.status}</span>
                      <button onClick={() => handleDelete(t.id)} className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
                    <span>Slug: <span className="font-mono text-zinc-400">{t.slug}</span></span>
                    {t.brand_name && <span>Brand: {t.brand_name}</span>}
                    {t.custom_domain && <span>Domain: {t.custom_domain}</span>}
                    <span>API Key: <span className="font-mono text-zinc-400">{t.api_key.substring(0, 12)}...</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "tiers" && (
        <div className="grid gap-6 sm:grid-cols-3">
          {tiers.map(tier => (
            <div key={tier.name} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Crown className={`h-5 w-5 ${tier.name === "agency" ? "text-amber-400" : tier.name === "pro" ? "text-violet-400" : "text-zinc-400"}`} />
                <h3 className="text-lg font-bold capitalize text-zinc-200">{tier.name}</h3>
              </div>
              <p className="text-3xl font-bold text-zinc-100">${tier.price}<span className="text-sm font-normal text-zinc-500">/mo</span></p>
              <div className="mt-4 space-y-2 text-sm text-zinc-400">
                <p>Max Products: <span className="text-zinc-200">{tier.max_products === -1 ? "Unlimited" : tier.max_products}</span></p>
                <p>Max Platforms: <span className="text-zinc-200">{tier.max_platforms === -1 ? "Unlimited" : tier.max_platforms}</span></p>
              </div>
              {tier.features && tier.features.length > 0 && (
                <ul className="mt-4 space-y-1">
                  {tier.features.map((f, i) => (
                    <li key={i} className="text-xs text-zinc-400 flex items-center gap-1">
                      <Check className="h-3 w-3 text-emerald-400" /> {f}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "stats" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <h2 className="text-lg font-semibold text-zinc-200 mb-4">White-Label Statistics</h2>
          <pre className="text-sm text-zinc-400 whitespace-pre-wrap">{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
