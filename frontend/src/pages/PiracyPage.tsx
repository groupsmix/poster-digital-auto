import { useEffect, useState } from "react";
import { Shield, FileWarning, Loader2, Plus, X, Check } from "lucide-react";
import {
  fetchPiracyStatus, createWatermark,
  fetchDMCARequests, generateDMCA, updateDMCAStatus,
  fetchProducts,
} from "@/lib/api";
import type { PiracyProtection, Product } from "@/lib/types";
import type { DMCARequest } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

export default function PiracyPage() {
  const [tab, setTab] = useState<"protection" | "dmca">("protection");
  const [protections, setProtections] = useState<PiracyProtection[]>([]);
  const [dmcaRequests, setDmcaRequests] = useState<DMCARequest[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  // DMCA form
  const [showDmcaForm, setShowDmcaForm] = useState(false);
  const [dmcaProductId, setDmcaProductId] = useState(0);
  const [dmcaUrl, setDmcaUrl] = useState("");
  const [dmcaName, setDmcaName] = useState("");
  const [generating, setGenerating] = useState(false);

  async function loadData() {
    try {
      const [pRes, dRes, prRes] = await Promise.all([
        fetchPiracyStatus(),
        fetchDMCARequests(),
        fetchProducts(),
      ]);
      setProtections(pRes.protections);
      setDmcaRequests(dRes.requests);
      setProducts(prRes.products);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleWatermark(productId: number) {
    try {
      const res = await createWatermark(productId);
      toast.success(res.message || `Watermark created: ${res.watermark_id}`);
      setLoading(true); loadData();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  async function handleGenerateDMCA() {
    if (!dmcaProductId) { toast.error("Select a product"); return; }
    setGenerating(true);
    try {
      const res = await generateDMCA(dmcaProductId, { infringer_url: dmcaUrl, infringer_name: dmcaName });
      toast.success(res.message || "DMCA template generated!");
      setShowDmcaForm(false); setDmcaUrl(""); setDmcaName("");
      setLoading(true); loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally { setGenerating(false); }
  }

  async function handleStatusChange(dmcaId: number, status: string) {
    try {
      await updateDMCAStatus(dmcaId, status);
      toast.success(`DMCA status updated to ${status}`);
      setLoading(true); loadData();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed"); }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Piracy Protection</h1>
          <p className="mt-1 text-sm text-zinc-400">Watermarks, piracy scanning, and DMCA takedown management</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setTab("protection")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "protection" ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            <Shield className="inline h-4 w-4 mr-1" /> Protection
          </button>
          <button onClick={() => setTab("dmca")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "dmca" ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
            <FileWarning className="inline h-4 w-4 mr-1" /> DMCA ({dmcaRequests.length})
          </button>
        </div>
      </div>

      {tab === "protection" && (
        <>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <h3 className="text-sm font-semibold text-zinc-200 mb-3">Watermark a Product</h3>
            <div className="flex flex-wrap gap-2">
              {products.map(p => (
                <button
                  key={p.id}
                  onClick={() => handleWatermark(p.id)}
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:border-violet-500 hover:text-violet-400 transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {protections.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <Shield className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No products protected yet. Click a product above to generate a watermark.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {protections.map(p => (
                <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-200">{p.product_name || `Product #${p.product_id}`}</h3>
                      <p className="mt-1 text-sm text-zinc-400">Watermark: <span className="font-mono text-violet-400">{p.watermark_id}</span></p>
                    </div>
                    <span className={`rounded px-2 py-0.5 text-xs ${p.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"}`}>{p.status}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
                    <span>Scans: {p.scan_count}</span>
                    {p.last_scan && <span>Last scan: {new Date(p.last_scan).toLocaleDateString()}</span>}
                    {p.fingerprint && <span>Fingerprint: {p.fingerprint.substring(0, 12)}...</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "dmca" && (
        <>
          <button onClick={() => setShowDmcaForm(!showDmcaForm)} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            {showDmcaForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showDmcaForm ? "Cancel" : "Generate DMCA Template"}
          </button>

          {showDmcaForm && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Product</label>
                  <select value={dmcaProductId} onChange={e => setDmcaProductId(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                    <option value={0}>Select product...</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Infringer URL</label>
                  <input type="text" value={dmcaUrl} onChange={e => setDmcaUrl(e.target.value)} placeholder="https://..." className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Infringer Name</label>
                  <input type="text" value={dmcaName} onChange={e => setDmcaName(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                </div>
              </div>
              <button onClick={handleGenerateDMCA} disabled={generating} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {generating ? "Generating..." : "Generate DMCA"}
              </button>
            </div>
          )}

          {dmcaRequests.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
              <FileWarning className="mx-auto h-10 w-10 text-zinc-600" />
              <p className="mt-3 text-zinc-400">No DMCA requests yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {dmcaRequests.map(d => (
                <div key={d.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-zinc-200">{d.product_name || `Product #${d.product_id}`}</h3>
                      {d.infringer_url && <p className="mt-1 text-sm text-zinc-400 break-all">{d.infringer_url}</p>}
                      {d.infringer_name && <p className="text-sm text-zinc-500">Infringer: {d.infringer_name}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={d.status}
                        onChange={e => handleStatusChange(d.id, e.target.value)}
                        className="rounded-lg border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300 focus:border-violet-500 focus:outline-none"
                      >
                        <option value="draft">Draft</option>
                        <option value="sent">Sent</option>
                        <option value="resolved">Resolved</option>
                        <option value="escalated">Escalated</option>
                      </select>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-zinc-600">Created: {new Date(d.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
