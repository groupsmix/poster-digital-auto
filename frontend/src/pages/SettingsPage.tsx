import { useEffect, useState } from "react";
import {
  Settings, Plus, Trash2, Edit3, X, Check, Loader2,
  Key, Bell, Users, Globe, Shield, Store, Share2,
} from "lucide-react";
import {
  fetchPlatformSettings, createPlatformSetting, updatePlatformSetting, deletePlatformSetting,
  fetchPersonas, createPersona, updatePersona, deletePersona,
  fetchPreferences, updatePreference,
  fetchAPIKeyStatus,
} from "@/lib/api";
import type { PlatformSetting, CustomerPersona, APIKeyStatus, SettingsPreferences } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

type TabKey = "platforms" | "api-keys" | "preferences" | "notifications" | "personas";

const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "platforms", label: "Platforms", icon: Globe },
  { key: "api-keys", label: "API Keys", icon: Key },
  { key: "preferences", label: "Defaults", icon: Settings },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "personas", label: "Personas", icon: Users },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("platforms");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Manage platforms, API keys, preferences, and customer personas
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex flex-wrap gap-1 rounded-xl border border-zinc-800 bg-zinc-900/50 p-1">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-violet-600 text-white"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "platforms" && <PlatformsTab />}
      {activeTab === "api-keys" && <APIKeysTab />}
      {activeTab === "preferences" && <PreferencesTab />}
      {activeTab === "notifications" && <NotificationsTab />}
      {activeTab === "personas" && <PersonasTab />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PLATFORMS TAB
// ═══════════════════════════════════════════════════════════════

function PlatformsTab() {
  const [platforms, setPlatforms] = useState<PlatformSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // Add form state
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("selling");
  const [newTone, setNewTone] = useState("");
  const [newPlanMode, setNewPlanMode] = useState("A");
  const [newMaxTitle, setNewMaxTitle] = useState(100);
  const [newMaxDesc, setNewMaxDesc] = useState(5000);
  const [newInstructions, setNewInstructions] = useState("");
  const [adding, setAdding] = useState(false);

  // Edit form state
  const [editTone, setEditTone] = useState("");
  const [editPlanMode, setEditPlanMode] = useState("A");
  const [editMaxTitle, setEditMaxTitle] = useState(100);
  const [editMaxDesc, setEditMaxDesc] = useState(5000);
  const [editInstructions, setEditInstructions] = useState("");
  const [editType, setEditType] = useState("selling");

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

  useEffect(() => { load(); }, []);

  async function handleAdd() {
    if (!newName.trim()) { toast.error("Platform name is required"); return; }
    setAdding(true);
    try {
      await createPlatformSetting({
        name: newName, type: newType, tone: newTone, plan_mode: newPlanMode,
        max_title_length: newMaxTitle, max_description_length: newMaxDesc,
        custom_instructions: newInstructions, enabled: true,
      });
      toast.success("Platform added!");
      setShowAdd(false);
      setNewName(""); setNewTone(""); setNewInstructions("");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to add platform");
    } finally {
      setAdding(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      await updatePlatformSetting(id, {
        tone: editTone, plan_mode: editPlanMode, type: editType,
        max_title_length: editMaxTitle, max_description_length: editMaxDesc,
        custom_instructions: editInstructions,
      });
      setEditingId(null);
      toast.success("Platform updated!");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleToggle(p: PlatformSetting) {
    try {
      await updatePlatformSetting(p.id, { enabled: !p.enabled });
      toast.success(`${p.platform} ${p.enabled ? "disabled" : "enabled"}`);
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete platform "${name}"?`)) return;
    try {
      await deletePlatformSetting(id);
      toast.success("Platform deleted");
      setPlatforms(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(p: PlatformSetting) {
    setEditingId(p.id);
    setEditTone(p.tone);
    setEditPlanMode(p.plan_mode);
    setEditMaxTitle(p.max_title_length);
    setEditMaxDesc(p.max_description_length);
    setEditInstructions(p.custom_instructions);
    setEditType(p.type || "selling");
  }

  const sellingPlatforms = platforms.filter(p => p.type === "selling");
  const socialPlatforms = platforms.filter(p => p.type === "social");

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Platform Management</h2>
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
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
              <input type="text" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. LinkedIn"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Type</label>
              <select value={newType} onChange={e => setNewType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                <option value="selling">Selling</option>
                <option value="social">Social</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tone</label>
              <input type="text" value={newTone} onChange={e => setNewTone(e.target.value)} placeholder="e.g. professional"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Plan Mode</label>
              <select value={newPlanMode} onChange={e => setNewPlanMode(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                <option value="A">Plan A (Manual/Review)</option>
                <option value="B">Plan B (Auto-publish)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Title Length</label>
              <input type="number" value={newMaxTitle} onChange={e => setNewMaxTitle(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Description Length</label>
              <input type="number" value={newMaxDesc} onChange={e => setNewMaxDesc(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Custom Instructions for AI</label>
            <textarea value={newInstructions} onChange={e => setNewInstructions(e.target.value)} rows={3}
              placeholder="Instructions for how AI should write content for this platform..."
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y" />
          </div>
          <button onClick={handleAdd} disabled={adding}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {adding ? "Adding..." : "Add Platform"}
          </button>
        </div>
      )}

      {/* Selling Platforms */}
      <PlatformGroup
        title="Selling Platforms" icon={Store} platforms={sellingPlatforms}
        editingId={editingId} onStartEdit={startEdit} onToggle={handleToggle}
        onDelete={handleDelete} onUpdate={handleUpdate} onCancel={() => setEditingId(null)}
        editTone={editTone} setEditTone={setEditTone} editPlanMode={editPlanMode} setEditPlanMode={setEditPlanMode}
        editMaxTitle={editMaxTitle} setEditMaxTitle={setEditMaxTitle} editMaxDesc={editMaxDesc} setEditMaxDesc={setEditMaxDesc}
        editInstructions={editInstructions} setEditInstructions={setEditInstructions}
        editType={editType} setEditType={setEditType}
      />

      {/* Social Platforms */}
      <PlatformGroup
        title="Social Platforms" icon={Share2} platforms={socialPlatforms}
        editingId={editingId} onStartEdit={startEdit} onToggle={handleToggle}
        onDelete={handleDelete} onUpdate={handleUpdate} onCancel={() => setEditingId(null)}
        editTone={editTone} setEditTone={setEditTone} editPlanMode={editPlanMode} setEditPlanMode={setEditPlanMode}
        editMaxTitle={editMaxTitle} setEditMaxTitle={setEditMaxTitle} editMaxDesc={editMaxDesc} setEditMaxDesc={setEditMaxDesc}
        editInstructions={editInstructions} setEditInstructions={setEditInstructions}
        editType={editType} setEditType={setEditType}
      />
    </div>
  );
}

function PlatformGroup({
  title, icon: Icon, platforms, editingId,
  onStartEdit, onToggle, onDelete, onUpdate, onCancel,
  editTone, setEditTone, editPlanMode, setEditPlanMode,
  editMaxTitle, setEditMaxTitle, editMaxDesc, setEditMaxDesc,
  editInstructions, setEditInstructions, editType, setEditType,
}: {
  title: string;
  icon: React.ElementType;
  platforms: PlatformSetting[];
  editingId: number | null;
  onStartEdit: (p: PlatformSetting) => void;
  onToggle: (p: PlatformSetting) => void;
  onDelete: (id: number, name: string) => void;
  onUpdate: (id: number) => void;
  onCancel: () => void;
  editTone: string; setEditTone: (v: string) => void;
  editPlanMode: string; setEditPlanMode: (v: string) => void;
  editMaxTitle: number; setEditMaxTitle: (v: number) => void;
  editMaxDesc: number; setEditMaxDesc: (v: number) => void;
  editInstructions: string; setEditInstructions: (v: string) => void;
  editType: string; setEditType: (v: string) => void;
}) {
  if (platforms.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="h-4 w-4 text-zinc-400" />
        <h3 className="text-sm font-semibold text-zinc-300">{title}</h3>
        <span className="text-xs text-zinc-500">({platforms.length})</span>
      </div>
      <div className="space-y-3">
        {platforms.map(p => (
          <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            {editingId === p.id ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-zinc-200">{p.platform}</h4>
                  <span className="text-xs text-zinc-500">Editing</span>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Type</label>
                    <select value={editType} onChange={e => setEditType(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                      <option value="selling">Selling</option>
                      <option value="social">Social</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Tone</label>
                    <input type="text" value={editTone} onChange={e => setEditTone(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Plan Mode</label>
                    <select value={editPlanMode} onChange={e => setEditPlanMode(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none">
                      <option value="A">Plan A (Manual/Review)</option>
                      <option value="B">Plan B (Auto-publish)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Title Length</label>
                    <input type="number" value={editMaxTitle} onChange={e => setEditMaxTitle(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Max Description Length</label>
                    <input type="number" value={editMaxDesc} onChange={e => setEditMaxDesc(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Custom Instructions</label>
                  <textarea value={editInstructions} onChange={e => setEditInstructions(e.target.value)} rows={3}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none resize-y" />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => onUpdate(p.id)}
                    className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500">Save</button>
                  <button onClick={onCancel}
                    className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600">Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h4 className="font-semibold text-zinc-200">{p.platform}</h4>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                      p.enabled ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"
                    }`}>
                      {p.enabled ? "Enabled" : "Disabled"}
                    </span>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                      p.plan_mode === "B" ? "bg-blue-500/20 text-blue-400" : "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      Plan {p.plan_mode}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => onToggle(p)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        p.enabled ? "bg-violet-600" : "bg-zinc-700"
                      }`}>
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        p.enabled ? "translate-x-6" : "translate-x-1"
                      }`} />
                    </button>
                    <button onClick={() => onStartEdit(p)}
                      className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200">
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={() => onDelete(p.id, p.platform)}
                      className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500">
                  <span>Tone: <span className="text-zinc-400">{p.tone || "—"}</span></span>
                  <span>Title max: <span className="text-zinc-400">{p.max_title_length}</span></span>
                  <span>Desc max: <span className="text-zinc-400">{p.max_description_length}</span></span>
                </div>
                {p.custom_instructions && (
                  <p className="mt-2 text-xs text-zinc-500 italic">{p.custom_instructions}</p>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// API KEYS TAB
// ═══════════════════════════════════════════════════════════════

function APIKeysTab() {
  const [keys, setKeys] = useState<APIKeyStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [configuredCount, setConfiguredCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchAPIKeyStatus()
      .then(res => {
        setKeys(res.api_keys);
        setConfiguredCount(res.configured_count);
        setTotalCount(res.total_count);
      })
      .catch(e => toast.error(e instanceof Error ? e.message : "Failed to load API key status"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  const priorityOrder = ["MUST HAVE", "For auto-post", "For email marketing", "Nice to have"];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">API Key Status</h2>
        <span className="text-sm text-zinc-400">
          {configuredCount} / {totalCount} configured
        </span>
      </div>

      {/* Progress bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-300">Configuration Progress</span>
          <span className="text-sm font-medium text-zinc-200">
            {totalCount > 0 ? Math.round((configuredCount / totalCount) * 100) : 0}%
          </span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-zinc-800">
          <div
            className={`h-full rounded-full transition-all ${
              configuredCount === totalCount ? "bg-emerald-500" : configuredCount > totalCount / 2 ? "bg-blue-500" : "bg-yellow-500"
            }`}
            style={{ width: `${totalCount > 0 ? (configuredCount / totalCount) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Keys grouped by priority */}
      {priorityOrder.map(priority => {
        const group = keys.filter(k => k.priority === priority);
        if (group.length === 0) return null;
        return (
          <div key={priority}>
            <div className="flex items-center gap-2 mb-3">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                priority === "MUST HAVE" ? "bg-red-500/20 text-red-400" :
                priority === "For auto-post" ? "bg-blue-500/20 text-blue-400" :
                priority === "For email marketing" ? "bg-purple-500/20 text-purple-400" :
                "bg-zinc-700 text-zinc-400"
              }`}>{priority}</span>
            </div>
            <div className="space-y-2">
              {group.map(k => (
                <div key={k.env_var}
                  className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                  <div className="flex items-center gap-3">
                    <div className={`rounded-lg p-2 ${k.configured ? "bg-emerald-500/20" : "bg-zinc-800"}`}>
                      {k.configured
                        ? <Shield className="h-4 w-4 text-emerald-400" />
                        : <Key className="h-4 w-4 text-zinc-500" />
                      }
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-200">{k.name}</p>
                      <p className="text-xs text-zinc-500 font-mono">{k.env_var}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {k.configured && k.masked_value && (
                      <span className="text-xs font-mono text-zinc-500">{k.masked_value}</span>
                    )}
                    <span className={`rounded px-2 py-1 text-xs font-medium ${
                      k.configured ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"
                    }`}>
                      {k.configured ? "Configured" : "Not set"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-400">
        <p>API keys are configured via environment variables on the server. Update them in your <code className="text-zinc-300">.env</code> file and restart the backend.</p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PREFERENCES TAB
// ═══════════════════════════════════════════════════════════════

function PreferencesTab() {
  const [prefs, setPrefs] = useState<SettingsPreferences | null>(null);
  const [platforms, setPlatforms] = useState<PlatformSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchPreferences(), fetchPlatformSettings()])
      .then(([p, pl]) => {
        setPrefs(p.preferences as SettingsPreferences);
        setPlatforms(pl.platforms);
      })
      .catch(e => toast.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setLoading(false));
  }, []);

  async function savePref(key: string, value: unknown) {
    setSaving(key);
    try {
      await updatePreference(key, value);
      setPrefs(prev => prev ? { ...prev, [key]: value } : null);
      toast.success("Preference saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(null);
    }
  }

  if (loading || !prefs) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  const allPlatformNames = platforms.map(p => p.platform);
  const defaultPlatforms = (prefs.default_platforms || []) as string[];
  const defaultLanguages = (prefs.default_languages || ["en"]) as string[];
  const defaultPlanMode = (prefs.default_plan_mode || "A") as string;
  const priceRange = (prefs.default_price_range || { min: 5, max: 15 }) as { min: number; max: number };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Default Preferences</h2>

      {/* Default Platforms */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-200">Default Platforms</h3>
        <p className="text-xs text-zinc-500">Select platforms that will be pre-selected for new products</p>
        <div className="flex flex-wrap gap-2">
          {allPlatformNames.map(name => {
            const selected = defaultPlatforms.includes(name);
            return (
              <button key={name} onClick={() => {
                const updated = selected
                  ? defaultPlatforms.filter(n => n !== name)
                  : [...defaultPlatforms, name];
                savePref("default_platforms", updated);
              }}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  selected
                    ? "border-violet-500 bg-violet-500/20 text-violet-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                }`}>
                {saving === "default_platforms" ? <Loader2 className="inline h-3 w-3 animate-spin mr-1" /> : null}
                {name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Default Languages */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-200">Default Languages</h3>
        <p className="text-xs text-zinc-500">Languages to use when creating new products</p>
        <div className="flex flex-wrap gap-2">
          {["en", "ar", "fr", "es", "de", "pt", "zh", "ja", "ko", "hi"].map(lang => {
            const selected = defaultLanguages.includes(lang);
            return (
              <button key={lang} onClick={() => {
                const updated = selected
                  ? defaultLanguages.filter(l => l !== lang)
                  : [...defaultLanguages, lang];
                savePref("default_languages", updated);
              }}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  selected
                    ? "border-violet-500 bg-violet-500/20 text-violet-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
                }`}>
                {lang.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      {/* Default Plan Mode */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-200">Default Plan Mode</h3>
        <div className="flex gap-3">
          {[
            { value: "A", label: "Plan A", desc: "Draft/Review - You review before publishing" },
            { value: "B", label: "Plan B", desc: "Auto-publish - CEO AI reviews, auto-posts" },
          ].map(opt => (
            <button key={opt.value} onClick={() => savePref("default_plan_mode", opt.value)}
              className={`flex-1 rounded-xl border p-4 text-left transition-colors ${
                defaultPlanMode === opt.value
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-zinc-700 bg-zinc-800 hover:border-zinc-600"
              }`}>
              <p className={`text-sm font-medium ${defaultPlanMode === opt.value ? "text-violet-300" : "text-zinc-300"}`}>
                {opt.label}
              </p>
              <p className="mt-1 text-xs text-zinc-500">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Default Price Range */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-200">Default Price Range</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-400">Min $</span>
            <input type="number" value={priceRange.min}
              onChange={e => savePref("default_price_range", { ...priceRange, min: Number(e.target.value) })}
              className="w-24 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
          </div>
          <span className="text-zinc-500">—</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-400">Max $</span>
            <input type="number" value={priceRange.max}
              onChange={e => savePref("default_price_range", { ...priceRange, max: Number(e.target.value) })}
              className="w-24 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// NOTIFICATIONS TAB
// ═══════════════════════════════════════════════════════════════

function NotificationsTab() {
  const [prefs, setPrefs] = useState<SettingsPreferences | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPreferences()
      .then(p => setPrefs(p.preferences as SettingsPreferences))
      .catch(e => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  async function toggle(key: string) {
    if (!prefs) return;
    const newVal = !prefs[key];
    try {
      await updatePreference(key, newVal);
      setPrefs(prev => prev ? { ...prev, [key]: newVal } : null);
      toast.success("Setting saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    }
  }

  async function setMethod(method: string) {
    try {
      await updatePreference("notification_method", method);
      setPrefs(prev => prev ? { ...prev, notification_method: method } : null);
      toast.success("Notification method updated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    }
  }

  if (loading || !prefs) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  const notifSettings = [
    { key: "notification_niche_finder", label: "Niche Finder Alerts", desc: "Get notified when AI discovers new product opportunities" },
    { key: "notification_trend_alerts", label: "Trend Alerts", desc: "Get notified about trending topics before they peak" },
    { key: "notification_ceo_rejections", label: "CEO Rejection Alerts", desc: "Get notified when CEO AI rejects content" },
    { key: "notification_revenue_milestones", label: "Revenue Milestones", desc: "Get notified when you hit revenue goals" },
  ];

  const methods = [
    { value: "dashboard", label: "Dashboard", desc: "Show in app notifications" },
    { value: "email", label: "Email", desc: "Send email notifications" },
    { value: "telegram", label: "Telegram", desc: "Send via Telegram bot" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Notification Preferences</h2>

      <div className="space-y-3">
        {notifSettings.map(({ key, label, desc }) => (
          <div key={key} className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
            <div>
              <p className="text-sm font-medium text-zinc-200">{label}</p>
              <p className="mt-0.5 text-xs text-zinc-500">{desc}</p>
            </div>
            <button onClick={() => toggle(key)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                prefs[key] ? "bg-violet-600" : "bg-zinc-700"
              }`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                prefs[key] ? "translate-x-6" : "translate-x-1"
              }`} />
            </button>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-200">Notification Method</h3>
        <div className="flex gap-3">
          {methods.map(m => (
            <button key={m.value} onClick={() => setMethod(m.value)}
              className={`flex-1 rounded-xl border p-4 text-left transition-colors ${
                prefs.notification_method === m.value
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-zinc-700 bg-zinc-800 hover:border-zinc-600"
              }`}>
              <p className={`text-sm font-medium ${prefs.notification_method === m.value ? "text-violet-300" : "text-zinc-300"}`}>
                {m.label}
              </p>
              <p className="mt-1 text-xs text-zinc-500">{m.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PERSONAS TAB
// ═══════════════════════════════════════════════════════════════

function PersonasTab() {
  const [personas, setPersonas] = useState<CustomerPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // Add form
  const [newName, setNewName] = useState("");
  const [newAge, setNewAge] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPlatforms, setNewPlatforms] = useState("");

  // Edit form
  const [editName, setEditName] = useState("");
  const [editAge, setEditAge] = useState("");
  const [editDesc, setEditDesc] = useState("");
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

  useEffect(() => { load(); }, []);

  async function handleAdd() {
    if (!newName.trim()) { toast.error("Name is required"); return; }
    setAdding(true);
    try {
      await createPersona({
        name: newName, age_range: newAge, description: newDesc,
        preferences: {},
        platforms: newPlatforms ? newPlatforms.split(",").map(s => s.trim()) : [],
      });
      toast.success("Persona created!");
      setShowAdd(false);
      setNewName(""); setNewAge(""); setNewDesc(""); setNewPlatforms("");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create persona");
    } finally {
      setAdding(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      await updatePersona(id, {
        name: editName, age_range: editAge, description: editDesc,
        platforms: editPlatforms ? editPlatforms.split(",").map(s => s.trim()) : [],
      });
      setEditingId(null);
      toast.success("Persona updated!");
      setLoading(true);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this persona?")) return;
    try {
      await deletePersona(id);
      toast.success("Persona deleted");
      setPersonas(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(p: CustomerPersona) {
    setEditingId(p.id);
    setEditName(p.name);
    setEditAge(p.age_range);
    setEditDesc(p.description);
    setEditPlatforms(p.platforms.join(", "));
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Customer Personas</h2>
          <p className="mt-1 text-xs text-zinc-400">Define target customer profiles to guide AI content generation</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
          {showAdd ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showAdd ? "Cancel" : "Add Persona"}
        </button>
      </div>

      {/* Add Form */}
      {showAdd && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200">New Persona</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
              <input type="text" value={newName} onChange={e => setNewName(e.target.value)}
                placeholder="e.g. Young Professional"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Age Range</label>
              <input type="text" value={newAge} onChange={e => setNewAge(e.target.value)}
                placeholder="e.g. 25-35"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Description</label>
            <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3}
              placeholder="Describe the persona's interests, buying habits, pain points..."
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none resize-y" />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Preferred Platforms (comma-separated)</label>
            <input type="text" value={newPlatforms} onChange={e => setNewPlatforms(e.target.value)}
              placeholder="e.g. Gumroad, Instagram, TikTok"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-violet-500 focus:outline-none" />
          </div>
          <button onClick={handleAdd} disabled={adding}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {adding ? "Creating..." : "Create Persona"}
          </button>
        </div>
      )}

      {/* Persona List */}
      {personas.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Users className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No personas yet. Create your first customer persona!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {personas.map(p => (
            <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              {editingId === p.id ? (
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Name</label>
                      <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                    </div>
                    <div>
                      <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Age Range</label>
                      <input type="text" value={editAge} onChange={e => setEditAge(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Description</label>
                    <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={3}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none resize-y" />
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">Platforms (comma-separated)</label>
                    <input type="text" value={editPlatforms} onChange={e => setEditPlatforms(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 focus:border-violet-500 focus:outline-none" />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleUpdate(p.id)}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500">Save</button>
                    <button onClick={() => setEditingId(null)}
                      className="rounded-md bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-600">Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-sm font-semibold text-zinc-200">{p.name}</h3>
                        {p.age_range && (
                          <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{p.age_range}</span>
                        )}
                      </div>
                      {p.description && (
                        <p className="mt-2 text-sm text-zinc-400">{p.description}</p>
                      )}
                      {p.platforms.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {p.platforms.map(pl => (
                            <span key={pl} className="rounded bg-violet-500/10 px-2 py-0.5 text-xs text-violet-400">{pl}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button onClick={() => startEdit(p)}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200">
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDelete(p.id)}
                        className="rounded-md border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-400 hover:bg-red-900/50 hover:text-red-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-zinc-500">
                    Created: {new Date(p.created_at).toLocaleDateString()}
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
