import type { Product, ProductCreate, Stats, AIProvider } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  return request<Stats>("/api/stats");
}

export async function fetchProducts(status?: string): Promise<{ products: Product[]; count: number }> {
  const query = status ? `?status=${status}` : "";
  return request(`/api/products${query}`);
}

export async function fetchProduct(id: number): Promise<Product> {
  return request<Product>(`/api/products/${id}`);
}

export async function createProduct(data: ProductCreate): Promise<Product> {
  return request<Product>("/api/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteProduct(id: number): Promise<{ message: string }> {
  return request(`/api/products/${id}`, { method: "DELETE" });
}

export async function generateProduct(id: number): Promise<unknown> {
  return request(`/api/products/${id}/generate`, { method: "POST" });
}

export async function fetchAIStatus(): Promise<{ providers: AIProvider[]; count: number }> {
  return request("/api/ai-status");
}

export async function resetAILimits(): Promise<{ message: string }> {
  return request("/api/ai-status/reset", { method: "POST" });
}
