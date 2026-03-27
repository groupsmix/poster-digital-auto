import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package, Trash2 } from "lucide-react";
import { fetchProducts, deleteProduct } from "@/lib/api";
import type { Product } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import Spinner from "@/components/Spinner";
import { toast } from "sonner";

const FILTERS = ["All", "pending", "draft", "researching", "creating", "review", "approved", "published", "rejected"];

export default function ProductListPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");
  const [deleting, setDeleting] = useState<number | null>(null);

  function load(status?: string) {
    setLoading(true);
    fetchProducts(status === "All" ? undefined : status)
      .then((r) => setProducts(r.products))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(filter);
  }, [filter]);

  async function handleDelete(id: number, name: string) {
    if (!window.confirm(`Delete "${name}"? This action cannot be undone.`)) return;
    setDeleting(id);
    try {
      await deleteProduct(id);
      setProducts((prev) => prev.filter((p) => p.id !== id));
      toast.success(`"${name}" deleted`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Products</h1>
        <p className="mt-1 text-zinc-400">Manage all your digital products</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
              filter === f
                ? "border-violet-500 bg-violet-500/20 text-violet-300"
                : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600"
            }`}
          >
            {f.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : products.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-10 text-center">
          <Package className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-3 text-zinc-400">No products found</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <div key={p.id} className="group rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-colors hover:border-zinc-700">
              <div className="flex items-start justify-between">
                <Link to={`/products/${p.id}`} className="flex-1">
                  <h3 className="font-semibold text-zinc-100 group-hover:text-violet-300 transition-colors">{p.name}</h3>
                </Link>
                <button
                  onClick={() => handleDelete(p.id, p.name)}
                  disabled={deleting === p.id}
                  className="ml-2 rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
                  title="Delete product"
                >
                  {deleting === p.id ? <Spinner className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
                </button>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <StatusBadge status={p.status} />
                <span className="text-xs text-zinc-500">
                  Plan {p.plan_mode}
                </span>
              </div>

              {p.target_platforms.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {p.target_platforms.map((pl) => (
                    <span key={pl} className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                      {pl}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                <span>{new Date(p.created_at).toLocaleDateString()}</span>
                <Link to={`/products/${p.id}`} className="text-violet-400 hover:text-violet-300">
                  View details →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
