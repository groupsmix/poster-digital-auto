import { useEffect, useState } from "react";
import {
  Settings, Plus, Trash2, Edit3, Loader2, X, Check, Key, Bell, Sliders, Users,
  Monitor, Share2, ToggleLeft, ToggleRight,
} from "lucide-react";
import {
  fetchPlatformSettings, createPlatformSetting, updatePlatformSetting, deletePlatformSetting,
  fetchPersonas, createPersona, updatePersona, deletePersona,
  fetchPreferences, updatePreference,
  fetchAPIKeyStatus,
} from "@/lib/api";
import type { PlatformSetting, CustomerPersona, APIKeyStatus, UserPreferences } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

type SettingsTab = "platforms" | "personas" | "api-keys" | "preferences" | "notifications";

const TABS: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: "platforms", label: "Platforms", icon: Monitor },
  { id: "personas", label: "Personas", icon: Users },
  { id: "api-keys", label: "API Keys", icon: Key },
  { id: "preferences", label: "Defaults", icon: Sliders },
  { id: "notifications", label: "Notifications", icon: Bell },
];

const TONE_OPTIONS = ["professional", "casual", "friendly", "formal", "playful", "luxury", "minimalist"];
const PLAN_MODES = ["A", "B", "C"];

export default function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>("platforms");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6 text-violet-400" />
          Settings
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Manage platforms, personas, API keys, and default preferences
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 rounded-xl border border-zinc-800 bg-zinc-900/50 p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === id
                ? "bg-violet-600 text-white"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "platforms" && <PlatformsTab />}
      {tab === "personas" && <PersonasTab />}
      {tab === "api-keys" && <APIKeysTab />}
      {tab === "preferences" && <DefaultsTab />}
      {tab === "notifications" && <NotificationsTab />}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PLATFORMS TAB
   ════════════════════════════════════════════════════════════════════ */

function PlatformsTab() {
  const [platforms, setPlatforms] = useState<PlatformSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  // Add form
  const [newName, setNewName] = useState("");
  const [newTone, setNewTone] = useState("professional");
  const [newPlanMode, setNewPlanMode] = useState("A");
  const [newMaxTitle, setNewMaxTitle] = useState(200);
  const [newMaxDesc, setNewMaxDesc] = useState(5000);
  const [newInstructions, setNewInstructions] = useState("");
  const [newType, setNewType] = useState("social");
  const [saving, setSaving] = useState(false);

  // Edit form
  const [editTone, setEditTone] = useState("");
  const [editPlanMode, setEditPlanMode] = useState("");
  const [editMaxTitle, setEditMaxTitle] = useState(200);
  const [editMaxDesc, setEditMaxDesc] = useState(5000);
  const [editInstructions, setEditInstructions] = useState("");

  async function load() {
    try {
      const res = await fetchPlatformSettings();
      setPlatforms(res.platforms);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load platforms");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd() {
    if (!newName.trim()) { toast.error("Platform name is required"); return; }
    setSaving(true);
    try {
      await createPlatformSetting({
        platform: newName,
        tone: newTone,
        plan_mode: newPlanMode,
        max_title_length: newMaxTitle,
        max_description_length: newMaxDesc,
        custom_instructions: newInstructions,
        platform_type: newType,
      });
      toast.success(`Platform "${newName}" added`);
      setShowAdd(false);
      setNewName("");
      setNewInstructions("");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to add platform");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      await updatePlatformSetting(id, {
        tone: editTone,
        plan_mode: editPlanMode,
        max_title_length: editMaxTitle,
        max_description_length: editMaxDesc,
        custom_instructions: editInstructions,
      });
      toast.success("Platform updated");
      setEditId(null);
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete platform "${name}"?`)) return;
    try {
      await deletePlatformSetting(id);
      toast.success(`Platform "${name}" deleted`);
      setPlatforms((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function handleToggle(p: PlatformSetting) {
    try {
      await updatePlatformSetting(p.id, { enabled: !p.enabled });
      setPlatforms((prev) =>
        prev.map((x) => (x.id === p.id ? { ...x, enabled: x.enabled ? 0 : 1 } : x)),
      );
      toast.success(`${p.platform} ${p.enabled ? "disabled" : "enabled"}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Platform Settings</h2>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
        >
          {showAdd ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showAdd ? "Cancel" : "Add Platform"}
        </button>
      </div>

      {/* Add Form */}
      {showAdd && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200">New Platform</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Shopify, TikTok"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Type</label>
              <select value={newType} onChange={(e) => setNewType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                <option value="social">Social</option>
                <option value="selling">Selling</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tone</label>
              <select value={newTone} onChange={(e) => setNewTone(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                {TONE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Plan Mode</label>
              <select value={newPlanMode} onChange={(e) => setNewPlanMode(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                {PLAN_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Title Length</label>
              <input type="number" value={newMaxTitle} onChange={(e) => setNewMaxTitle(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Description Length</label>
              <input type="number" value={newMaxDesc} onChange={(e) => setNewMaxDesc(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Custom Instructions</label>
            <textarea value={newInstructions} onChange={(e) => setNewInstructions(e.target.value)}
              placeholder="Optional: specific instructions for AI content generation..."
              rows={3}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y" />
          </div>
          <button onClick={handleAdd} disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {saving ? "Saving..." : "Save Platform"}
          </button>
        </div>
      )}

      {/* Platform List */}
      {platforms.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Share2 className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No platforms configured. Add one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {platforms.map((p) => (
            <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              {editId === p.id ? (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-zinc-200">{p.platform}</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-medium text-zinc-500">Tone</label>
                      <select value={editTone} onChange={(e) => setEditTone(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                        {TONE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-500">Plan Mode</label>
                      <select value={editPlanMode} onChange={(e) => setEditPlanMode(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                        {PLAN_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-500">Max Title</label>
                      <input type="number" value={editMaxTitle} onChange={(e) => setEditMaxTitle(Number(e.target.value))}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-500">Max Description</label>
                      <input type="number" value={editMaxDesc} onChange={(e) => setEditMaxDesc(Number(e.target.value))}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-zinc-500">Custom Instructions</label>
                    <textarea value={editInstructions} onChange={(e) => setEditInstructions(e.target.value)} rows={2}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none resize-y" />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleUpdate(p.id)}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500">Save</button>
                    <button onClick={() => setEditId(null)}
                      className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600">Cancel</button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-sm font-semibold text-zinc-200">{p.platform}</h3>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        p.enabled ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-500"
                      }`}>
                        {p.enabled ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-zinc-500">
                      <span>Tone: <span className="text-zinc-400">{p.tone || "default"}</span></span>
                      <span>Plan: <span className="text-zinc-400">{p.plan_mode}</span></span>
                      <span>Title: <span className="text-zinc-400">{p.max_title_length} chars</span></span>
                      <span>Desc: <span className="text-zinc-400">{p.max_description_length} chars</span></span>
                    </div>
                    {p.custom_instructions && (
                      <p className="mt-2 text-xs text-zinc-500 italic">{p.custom_instructions}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={() => handleToggle(p)}
                      className="text-zinc-400 hover:text-violet-400 transition-colors" title="Toggle">
                      {p.enabled ? <ToggleRight className="h-5 w-5 text-emerald-400" /> : <ToggleLeft className="h-5 w-5" />}
                    </button>
                    <button onClick={() => {
                      setEditId(p.id);
                      setEditTone(p.tone || "professional");
                      setEditPlanMode(p.plan_mode || "A");
                      setEditMaxTitle(p.max_title_length);
                      setEditMaxDesc(p.max_description_length);
                      setEditInstructions(p.custom_instructions || "");
                    }}
                      className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200">
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={() => handleDelete(p.id, p.platform)}
                      className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PERSONAS TAB
   ════════════════════════════════════════════════════════════════════ */

function PersonasTab() {
  const [personas, setPersonas] = useState<CustomerPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // Add form
  const [newName, setNewName] = useState("");
  const [newAgeRange, setNewAgeRange] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPlatforms, setNewPlatforms] = useState("");

  // Edit form
  const [editName, setEditName] = useState("");
  const [editAgeRange, setEditAgeRange] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPlatforms, setEditPlatforms] = useState("");

  async function load() {
    try {
      const res = await fetchPersonas();
      setPersonas(res.personas);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load personas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd() {
    if (!newName.trim()) { toast.error("Persona name is required"); return; }
    setSaving(true);
    try {
      await createPersona({
        name: newName,
        age_range: newAgeRange,
        description: newDescription,
        platforms: newPlatforms.split(",").map((s) => s.trim()).filter(Boolean),
      });
      toast.success(`Persona "${newName}" created`);
      setShowAdd(false);
      setNewName("");
      setNewAgeRange("");
      setNewDescription("");
      setNewPlatforms("");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create persona");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      await updatePersona(id, {
        name: editName,
        age_range: editAgeRange,
        description: editDescription,
        platforms: editPlatforms.split(",").map((s) => s.trim()).filter(Boolean),
      });
      toast.success("Persona updated");
      setEditId(null);
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete persona "${name}"?`)) return;
    try {
      await deletePersona(id);
      toast.success(`Persona "${name}" deleted`);
      setPersonas((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Customer Personas</h2>
        <button onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
          {showAdd ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showAdd ? "Cancel" : "Add Persona"}
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200">New Persona</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Budget-Conscious Student"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Age Range</label>
              <input type="text" value={newAgeRange} onChange={(e) => setNewAgeRange(e.target.value)}
                placeholder="e.g. 18-25"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Description</label>
            <textarea value={newDescription} onChange={(e) => setNewDescription(e.target.value)}
              placeholder="Describe this persona's buying behavior, interests, and pain points..."
              rows={3}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y" />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Platforms (comma-separated)</label>
            <input type="text" value={newPlatforms} onChange={(e) => setNewPlatforms(e.target.value)}
              placeholder="e.g. Gumroad, Instagram, Twitter"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
          </div>
          <button onClick={handleAdd} disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {saving ? "Saving..." : "Save Persona"}
          </button>
        </div>
      )}

      {personas.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Users className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No personas created yet. Add one to target your content.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {personas.map((p) => (
            <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              {editId === p.id ? (
                <div className="space-y-3">
                  <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  <input type="text" value={editAgeRange} onChange={(e) => setEditAgeRange(e.target.value)} placeholder="Age range"
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={2}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none resize-y" />
                  <input type="text" value={editPlatforms} onChange={(e) => setEditPlatforms(e.target.value)} placeholder="Platforms (comma-separated)"
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  <div className="flex gap-2">
                    <button onClick={() => handleUpdate(p.id)}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500">Save</button>
                    <button onClick={() => setEditId(null)}
                      className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600">Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-200">{p.name}</h3>
                      {p.age_range && <span className="text-xs text-zinc-500">Age: {p.age_range}</span>}
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button onClick={() => {
                        setEditId(p.id);
                        setEditName(p.name);
                        setEditAgeRange(p.age_range || "");
                        setEditDescription(p.description || "");
                        setEditPlatforms((p.platforms || []).join(", "));
                      }}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200">
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDelete(p.id, p.name)}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {p.description && <p className="mt-2 text-xs text-zinc-400">{p.description}</p>}
                  {p.platforms && p.platforms.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {p.platforms.map((pl) => (
                        <span key={pl} className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{pl}</span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   API KEYS TAB
   ════════════════════════════════════════════════════════════════════ */

function APIKeysTab() {
  const [status, setStatus] = useState<APIKeyStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAPIKeyStatus()
      .then(setStatus)
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load API key status"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;
  if (!status) return null;

  const KEY_LABELS: Record<string, string> = {
    GEMINI_API_KEY: "Google Gemini",
    GROQ_API_KEY: "Groq",
    CLOUDFLARE_API_TOKEN: "Cloudflare Workers AI",
    CLOUDFLARE_ACCOUNT_ID: "Cloudflare Account",
    CEREBRAS_API_KEY: "Cerebras",
    MISTRAL_API_KEY: "Mistral AI",
    ELEVENLABS_API_KEY: "ElevenLabs TTS",
    TELEGRAM_BOT_TOKEN: "Telegram Bot",
    TUMBLR_CONSUMER_KEY: "Tumblr",
    PINTEREST_ACCESS_TOKEN: "Pinterest",
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">API Key Status</h2>
        <p className="text-sm text-zinc-400 mt-1">
          {status.configured} of {status.total} API keys configured. Keys are set via environment variables.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(status.keys).map(([key, configured]) => (
          <div key={key} className={`rounded-xl border p-4 ${
            configured
              ? "border-emerald-500/30 bg-emerald-500/5"
              : "border-zinc-800 bg-zinc-900/50"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Key className={`h-4 w-4 ${configured ? "text-emerald-400" : "text-zinc-600"}`} />
                <div>
                  <p className="text-sm font-medium text-zinc-200">{KEY_LABELS[key] || key}</p>
                  <p className="text-xs text-zinc-500 font-mono">{key}</p>
                </div>
              </div>
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                configured
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-zinc-700 text-zinc-500"
              }`}>
                {configured ? "Configured" : "Not Set"}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <p className="text-xs text-zinc-500">
          API keys are managed through environment variables. Set them in your <code className="text-violet-400">.env</code> file
          or server configuration. Never expose API keys in the frontend.
        </p>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   DEFAULTS TAB
   ════════════════════════════════════════════════════════════════════ */

function DefaultsTab() {
  const [prefs, setPrefs] = useState<UserPreferences>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    fetchPreferences()
      .then((res) => setPrefs(res.preferences))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setLoading(false));
  }, []);

  async function save(key: string, value: string) {
    setSaving(key);
    try {
      await updatePreference(key, value);
      setPrefs((prev) => ({ ...prev, [key]: value }));
      toast.success("Preference saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  const defaultPlatforms = (() => {
    try { return JSON.parse(prefs.default_platforms || "[]") as string[]; } catch { return []; }
  })();
  const defaultLanguages = (() => {
    try { return JSON.parse(prefs.default_languages || "[]") as string[]; } catch { return []; }
  })();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Default Preferences</h2>

      <div className="space-y-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200">Product Defaults</h3>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Default Platforms</label>
              <input type="text" value={defaultPlatforms.join(", ")}
                onChange={(e) => {
                  const val = JSON.stringify(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                  setPrefs((prev) => ({ ...prev, default_platforms: val }));
                }}
                onBlur={(e) => {
                  const val = JSON.stringify(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                  save("default_platforms", val);
                }}
                placeholder="Gumroad, Twitter, Instagram"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Default Languages</label>
              <input type="text" value={defaultLanguages.join(", ")}
                onChange={(e) => {
                  const val = JSON.stringify(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                  setPrefs((prev) => ({ ...prev, default_languages: val }));
                }}
                onBlur={(e) => {
                  const val = JSON.stringify(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                  save("default_languages", val);
                }}
                placeholder="en, es, fr"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Default Plan Mode</label>
              <select value={prefs.default_plan_mode || "A"}
                onChange={(e) => save("default_plan_mode", e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                {PLAN_MODES.map((m) => <option key={m} value={m}>Plan {m}</option>)}
              </select>
              {saving === "default_plan_mode" && <Loader2 className="mt-1 h-3 w-3 animate-spin text-violet-400" />}
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Default Product Type</label>
              <select value={prefs.default_product_type || "digital"}
                onChange={(e) => save("default_product_type", e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                <option value="digital">Digital</option>
                <option value="physical">Physical</option>
                <option value="service">Service</option>
                <option value="subscription">Subscription</option>
              </select>
              {saving === "default_product_type" && <Loader2 className="mt-1 h-3 w-3 animate-spin text-violet-400" />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   NOTIFICATIONS TAB
   ════════════════════════════════════════════════════════════════════ */

function NotificationsTab() {
  const [prefs, setPrefs] = useState<UserPreferences>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPreferences()
      .then((res) => setPrefs(res.preferences))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setLoading(false));
  }, []);

  async function toggle(key: string) {
    const current = prefs[key] === "true";
    const newVal = current ? "false" : "true";
    try {
      await updatePreference(key, newVal);
      setPrefs((prev) => ({ ...prev, [key]: newVal }));
      toast.success("Notification preference updated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  const notifications = [
    { key: "notify_pipeline_complete", label: "Pipeline Complete", desc: "Notify when AI pipeline finishes processing a product" },
    { key: "notify_ab_test_winner", label: "A/B Test Winner", desc: "Notify when an A/B test has a clear winner" },
    { key: "notify_trend_alerts", label: "Trend Alerts", desc: "Notify when trending opportunities are detected" },
    { key: "notify_goal_reached", label: "Revenue Goal Reached", desc: "Notify when a revenue goal milestone is hit" },
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Notification Preferences</h2>
      <div className="space-y-3">
        {notifications.map(({ key, label, desc }) => (
          <div key={key} className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div>
              <p className="text-sm font-medium text-zinc-200">{label}</p>
              <p className="text-xs text-zinc-500">{desc}</p>
            </div>
            <button onClick={() => toggle(key)} className="transition-colors">
              {prefs[key] === "true" ? (
                <ToggleRight className="h-6 w-6 text-emerald-400" />
              ) : (
                <ToggleLeft className="h-6 w-6 text-zinc-600" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
