const API_BASE = `http://${window.location.hostname}:8000/api`;

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

export interface Wine {
  id: number;
  name: string;
  producer: string;
  country: string;
  region: string;
  appellation: string | null;
  vintage: string | null;
  grape_variety: string | null;
  color: string;
  alcohol: number;
  drink_from: number | null;
  drink_to: number | null;
  market_price: number | null;
  stock?: number;
}

export interface Transaction {
  id: string;
  wine_id: number;
  wine_name: string;
  wine_producer: string;
  wine_vintage: string | null;
  wine_region: string;
  wine_color: string;
  quantity: number;
  purchase_price: number | null;
  type: "purchase" | "sale";
  date: string | null;
}

export interface Alert {
  id: string;
  message: string;
  severity: "error" | "warning" | "info";
  source_agent: string | null;
  read: boolean;
  created_at: string;
}

export interface CellarSummary {
  total_bottles: number;
  total_wines: number;
  purchase_value: number;
  market_value: number;
  sold_bottles: number;
  region_balance: { region: string; pct: number }[];
  color_distribution: Record<string, number>;
  top_wines: { name: string; bottles: number }[];
}

export interface AgentEvent {
  source: string;
  type: "thought" | "action" | "observation" | "final" | "alert";
  message: string;
  timestamp: string;
}

export const api = {
  wines: {
    list: (params?: { color?: string; region?: string; search?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.color) q.set("color", params.color);
      if (params?.region) q.set("region", params.region);
      if (params?.search) q.set("search", params.search);
      if (params?.limit) q.set("limit", String(params.limit));
      return fetchApi<{ wines: Wine[]; total: number }>(`/wines?${q}`);
    },
    get: (id: number) => fetchApi<Wine>(`/wines/${id}`),
    regions: () => fetchApi<{ regions: string[] }>("/wines/filters/regions"),
    colors: () => fetchApi<{ colors: string[] }>("/wines/filters/colors"),
  },

  cellar: {
    summary: () => fetchApi<CellarSummary>("/summary"),
    wines: () => fetchApi<{ wines: (Wine & { stock: number })[]; total: number }>("/cellar"),
  },

  transactions: {
    list: (params?: { type?: "purchase" | "sale" }) => {
      const q = new URLSearchParams();
      if (params?.type) q.set("type", params.type);
      return fetchApi<{ transactions: Transaction[] }>(`/transactions?${q}`);
    },
    create: (data: {
      wine_id: number;
      quantity: number;
      purchase_price?: number;
      type: "purchase" | "sale";
      date?: string;
    }) =>
      fetchApi<Transaction>("/transactions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      id: string,
      data: {
        quantity?: number;
        purchase_price?: number;
        type?: "purchase" | "sale";
        date?: string;
      },
    ) =>
      fetchApi<Transaction>(`/transactions/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      fetchApi<{ status: string }>(`/transactions/${id}`, { method: "DELETE" }),
  },

  alerts: {
    list: () => fetchApi<{ alerts: Alert[] }>("/alerts"),
    unreadCount: () => fetchApi<{ count: number }>("/alerts/unread-count"),
    markRead: (id: string) =>
      fetchApi<{ status: string }>(`/alerts/${id}/read`, { method: "PUT" }),
    markAllRead: () =>
      fetchApi<{ marked_read: number }>("/alerts/mark-all-read", { method: "PUT" }),
    create: (data: { message: string; severity?: string; source_agent?: string }) =>
      fetchApi<Alert>("/alerts", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  agent: {
    trigger: (trigger = "manual", data?: Record<string, unknown>) =>
      fetchApi<{ status: string; trigger: string }>("/agent/trigger", {
        method: "POST",
        body: JSON.stringify({ trigger, data }),
      }),
    status: () => fetchApi<{ status: string; subscriber_count: number; recent_events: number }>("/agent/status"),
  },
};
