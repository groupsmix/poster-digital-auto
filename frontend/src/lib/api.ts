import type { Product, ProductCreate, Stats, AIProvider, SocialPost, AutoPostConfig } from "./types";

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

// Social Posts
export async function fetchSocialPosts(filters?: {
  product_id?: number;
  platform?: string;
  post_status?: string;
}): Promise<{ posts: SocialPost[]; count: number }> {
  const params = new URLSearchParams();
  if (filters?.product_id) params.set("product_id", String(filters.product_id));
  if (filters?.platform) params.set("platform", filters.platform);
  if (filters?.post_status) params.set("post_status", filters.post_status);
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/social-posts${query}`);
}

export async function updateSocialPost(
  id: number,
  data: { caption?: string; post_status?: string },
): Promise<SocialPost> {
  return request<SocialPost>(`/api/social-posts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function triggerAutoPost(id: number): Promise<{ success: boolean; message: string; post_url: string; platform: string }> {
  return request(`/api/social-posts/${id}/post`, { method: "POST" });
}

export async function generateCaptions(productId: number): Promise<unknown> {
  return request(`/api/products/${productId}/captions`, { method: "POST" });
}

export async function fetchAutoPostConfig(): Promise<AutoPostConfig> {
  return request<AutoPostConfig>("/api/auto-post/config");
}
