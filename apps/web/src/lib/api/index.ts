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
  price: number | null;
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

export interface Recommendation {
  id: string;
  wine_id: number;
  wine_name: string | null;
  wine_producer: string | null;
  quantity: number;
  market_price: number;
  priority_score: number;
  recommendation_reason: string;
  created_at: string;
}

export type WineCardSeason = "spring" | "summer" | "autumn" | "winter";
export type VatCountry = "LU" | "FR" | "BE" | "DE";
export type WineCardTriggerReason = "manual" | "wine_sold" | "low_stock_scan";

export interface WineCardInventoryItem {
  wine_id: number;
  producer: string;
  wine_name: string;
  region: string | null;
  country: string | null;
  appellation: string | null;
  wine_color: string | null;
  vintage: string | null;
  grape_variety: string | null;
  drink_from: number | null;
  drink_to: number | null;
  quantity: number;
  purchase_price_ht: number;
  avg_market_price: number | null;
}

export interface WineCardPricingResult {
  purchase_price_ht: number;
  vat_country: VatCountry;
  markup_coefficient: number;
  vat_rate: number;
  selling_price_ht: number;
  selling_price_ttc: number;
  glass_price_ttc: number;
}

export interface WineCardMenuItem {
  section: string;
  vat_country: VatCountry;
  vat_rate: number;
  wine_id: number;
  producer: string;
  wine_name: string;
  vintage: string | null;
  region: string | null;
  appellation: string | null;
  country: string | null;
  quantity: number;
  purchase_price_ht: number;
  avg_market_price: number | null;
  selling_price_ttc: number;
  glass_price_ttc: number;
}

export interface WineCardMenuExportResult {
  season: WineCardSeason;
  vat_country: VatCountry;
  items_count: number;
  markdown: string;
  menu_items: WineCardMenuItem[];
}

export interface WineCardMenuAnalysis {
  season: WineCardSeason;
  strategy: {
    focus: string[];
    avoid: string[];
    notes: string;
  };
  summary: string;
  missing_categories: string[];
  low_stock_warnings: string[];
  by_the_glass_suggestions: string[];
  seasonal_inventory_guidance: string[];
  section_counts: Record<string, number>;
}

export interface CellarReferenceDeletionResult {
  status: string;
  wine_id: number;
  summary: string;
  replacement_suggestions: {
    wine_id: number;
    name: string;
    producer: string;
    vintage: string | null;
    region: string | null;
    color: string;
    market_price: number | null;
  }[];
}

export interface WineCardTriggerReport {
  trigger_reason: WineCardTriggerReason;
  triggered_at: string;
  season: WineCardSeason;
  vat_country: VatCountry;
  min_stock_threshold: number;
  inventory_items: number;
  low_stock_count: number;
  should_refresh_menu: boolean;
  should_consider_purchase: boolean;
  low_stock_items: string[];
  procurement_suggestions: string[];
  sales_boost_suggestions: string[];
  wine_fair_watchlist: string[];
  menu_export: WineCardMenuExportResult | null;
  menu_analysis: WineCardMenuAnalysis | null;
}

export const api = {
  wines: {
    list: (params?: { color?: string; region?: string; appellation?: string, search?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.color) q.set("color", params.color);
      if (params?.region) q.set("region", params.region);
      if (params?.appellation) q.set("appellation", params.appellation);
      if (params?.search) q.set("search", params.search);
      if (params?.limit) q.set("limit", String(params.limit));
      return fetchApi<{ wines: Wine[]; total: number }>(`/wines?${q}`);
    },
    get: (id: number) => fetchApi<Wine>(`/wines/${id}`),
    regions: () => fetchApi<{ regions: string[] }>("/wines/filters/regions"),
    colors: () => fetchApi<{ colors: string[] }>("/wines/filters/colors"),
    appellations: () => fetchApi<{ appellations: string[] }>("/wines/filters/appellations"),
  },

  cellar: {
    summary: () => fetchApi<CellarSummary>("/summary"),
    wines: () => fetchApi<{ wines: (Wine & { stock: number })[]; total: number }>("/cellar"),
    deleteReference: (wineId: number) =>
      fetchApi<CellarReferenceDeletionResult>(`/cellar/reference/${wineId}`, {
        method: "DELETE",
      }),
  },

  transactions: {
    list: (params?: { type?: "purchase" | "sale"; limit?: number; offset?: number }) => {
      const q = new URLSearchParams();
      if (params?.type) q.set("type", params.type);
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      return fetchApi<{ transactions: Transaction[] }>(`/transactions?${q}`);
    },
    create: (data: {
      wine_id: number;
      quantity: number;
      price?: number;
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
        price?: number;
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
      fetchApi<{ status: string; trigger: string }>("/agents/run", {
        method: "POST",
        body: JSON.stringify({ trigger }),
      }),
    status: () => fetchApi<{ status: string; subscriber_count: number; recent_events: number }>("/agent/status"),
  },

  recommendations: {
    list: (params?: { limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit) q.set("limit", String(params.limit));
      return fetchApi<{ recommendations: Recommendation[] }>(`/recommendations?${q}`);
    },
  },

  wineCard: {
    inventory: () =>
      fetchApi<{ items: WineCardInventoryItem[]; total: number }>("/wine-card/inventory"),
    previewPricing: (purchase_price_ht: number, vat_country: VatCountry = "LU") =>
      fetchApi<WineCardPricingResult>("/wine-card/pricing/preview", {
        method: "POST",
        body: JSON.stringify({ purchase_price_ht, vat_country }),
      }),
    exportEditableMenu: (season: WineCardSeason, vat_country: VatCountry = "LU") =>
      fetchApi<WineCardMenuExportResult>(
        `/wine-card/menu/export?season=${season}&vat_country=${vat_country}`
      ),
    analyzeMenu: (season: WineCardSeason, vat_country: VatCountry = "LU") =>
      fetchApi<WineCardMenuAnalysis>(
        `/wine-card/menu/analysis?season=${season}&vat_country=${vat_country}`
      ),
    generateOneShotMenu: (
      occasion: WineCardOccasion,
      vat_country: VatCountry = "LU",
      service_count = 3,
      menu_total_price_ttc?: number,
    ) =>
      fetchApi<WineCardOneShotResult>("/wine-card/menu/one-shot", {
        method: "POST",
        body: JSON.stringify({
          occasion,
          vat_country,
          service_count,
          menu_total_price_ttc,
        }),
      }),
    runTrigger: (
      reason: WineCardTriggerReason = "manual",
      season: WineCardSeason = "winter",
      vat_country: VatCountry = "LU",
      min_stock_threshold = 2,
    ) =>
      fetchApi<WineCardTriggerReport>(
        `/wine-card/trigger/run?reason=${reason}&season=${season}&vat_country=${vat_country}&min_stock_threshold=${min_stock_threshold}`,
        { method: "POST" }
      ),
    latestTrigger: () => fetchApi<WineCardTriggerReport | null>("/wine-card/trigger/latest"),
  },
};
