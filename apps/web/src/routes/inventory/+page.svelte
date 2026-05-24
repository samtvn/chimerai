<script lang="ts">
  import {
    Plus,
    Search,
    Filter,
    X,
    ArrowUpRight,
    ArrowDownLeft,
    Wine as WineIcon,
    Package,
    TrendingUp,
    ChevronRight,
    Minus,
  } from "@lucide/svelte";
  import type { Wine as WineType, CellarSummary } from "$lib/api";
  import { api } from "$lib/api";
  import agentStore from "$lib/stores/agent.svelte";
  import { debounce } from "$lib/utils/debounce";
  import AgentActivityStream from "$lib/components/AgentActivityStream.svelte";

  let loading = $state(true);
  let wines = $state<(WineType & { stock: number })[]>([]);
  let summary = $state<CellarSummary | null>(null);
  let regions = $state<string[]>([]);
  let colors = $state<string[]>([]);
  let appellations = $state<string[]>([]);

  let searchQuery = $state("");
  let filterColor = $state("");
  let filterRegion = $state("");
  let filterAppellation = $state("");
  let selectedWine = $state<(WineType & { stock: number }) | null>(null);
  let showFilters = $state(false);
  let showAddModal = $state(false);
  let error = $state("");

  let addForm = $state({
    wine_id: 0,
    wineSearch: "",
    quantity: 1,
    purchase_price: 0,
    type: "purchase" as "purchase" | "sale",
    date: new Date().toISOString().slice(0, 16),
  });

  async function loadData() {
    loading = true;
    try {
      const [cellarRes, summaryRes, regionRes, colorRes, appellationRes] =
        await Promise.all([
          api.cellar.wines(),
          api.cellar.summary(),
          api.wines.regions(),
          api.wines.colors(),
          api.wines.appellations(),
        ]);
      wines = cellarRes.wines;
      summary = summaryRes;
      regions = regionRes.regions;
      colors = colorRes.colors;
      appellations = appellationRes.appellations;
    } catch (e: any) {
      error = e.message;
    }
    loading = false;
  }

  async function searchWines(query: string) {
    if (query.length < 2) return [];
    try {
      const res = await api.wines.list({ search: query, limit: 20 });
      return res.wines;
    } catch {
      return [];
    }
  }

  let wineSearchResults = $state<WineType[]>([]);
  let searching = $state(false);

  const debouncedSearchWines = debounce(async (q: string) => {
    if (q.length < 2) {
      wineSearchResults = [];
      return;
    }
    searching = true;
    wineSearchResults = await searchWines(q);
    searching = false;
  }, 300);

  function invalidateAll() {
    loadData();
  }

  async function createTransaction() {
    try {
      await api.transactions.create({
        wine_id: addForm.wine_id,
        quantity: addForm.quantity,
        purchase_price: addForm.purchase_price || undefined,
        type: addForm.type,
        date: addForm.date ? new Date(addForm.date).toISOString() : undefined,
      });
      showAddModal = false;
      resetAddForm();
      invalidateAll();
    } catch (e: any) {
      error = e.message;
    }
  }

  function resetAddForm() {
    addForm = {
      wine_id: 0,
      wineSearch: "",
      quantity: 1,
      purchase_price: 0,
      type: "purchase",
      date: new Date().toISOString().slice(0, 16),
    };
    wineSearchResults = [];
  }

  function openAddModal(type: "purchase" | "sale", wineId?: number) {
    resetAddForm();
    addForm.type = type;
    if (wineId) {
      addForm.wine_id = wineId;
      const wine = wines.find((w) => w.id === wineId);
      if (wine) {
        addForm.wineSearch = `${wine.name} ${wine.vintage || ""}`;
        addForm.purchase_price = wine.market_price || 0;
      }
    }
    showAddModal = true;
  }

  function selectWine(wine: WineType & { stock: number }) {
    selectedWine = selectedWine?.id === wine.id ? null : wine;
  }

  const wineColorLabel: Record<string, string> = {
    red: "red",
    white: "white",
    rosé: "rose",
    sparkling: "sparkling",
    fortified: "fortified",
    dessert: "dessert",
  };
  const wineColorClass: Record<string, string> = {
    red: "wine-color-red",
    white: "wine-color-white",
    rosé: "wine-color-rose",
    sparkling: "wine-color-sparkling",
    fortified: "wine-color-fortified",
    dessert: "wine-color-dessert",
  };

  function getWineColorKey(input: string | null | undefined): string {
    const key = (input || "").trim().toLowerCase();
    if (key === "rose" || key === "rosé") return "rosé";
    return key;
  }

  function getStockLevel(stock: number): "normal" | "low" | "critical" {
    if (stock <= 1) return "critical";
    if (stock <= 2) return "low";
    return "normal";
  }

  function stockBadgeClass(stock: number): string {
    const level = getStockLevel(stock);
    if (level === "critical") return "stock-badge-critical";
    if (level === "low") return "stock-badge-low";
    return "stock-badge-normal";
  }

  function stockTextClass(stock: number): string {
    const level = getStockLevel(stock);
    if (level === "critical") return "stock-text-critical font-bold";
    if (level === "low") return "stock-text-low font-semibold";
    return "";
  }

  const filteredWines = $derived.by(() => {
    if (!searchQuery && !filterColor && !filterRegion && !filterAppellation)
      return wines;
    return wines.filter((w) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (
          !w.name.toLowerCase().includes(q) &&
          !w.producer.toLowerCase().includes(q) &&
          !w.region.toLowerCase().includes(q) &&
          !w.grape_variety?.toLowerCase().includes(q)
        )
          return false;
      }
      if (filterColor && w.color !== filterColor) return false;
      if (filterRegion && w.region !== filterRegion) return false;
      if (filterAppellation && w.appellation !== filterAppellation)
        return false;
      return true;
    });
  });

  $effect(() => {
    loadData();
    agentStore.connect();
  });
</script>

<div class="flex flex-col gap-6 p-4 md:p-6">
  {#if error}
    <div class="alert alert-error">
      <span>{error}</span>
      <button class="btn btn-sm btn-ghost" onclick={() => (error = "")}
        ><X size="14" /></button
      >
    </div>
  {/if}

  <!-- KPI Cards -->
  {#if summary}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Total Bottles
          </div>
          <div class="mt-1 flex items-end gap-2">
            <span class="text-2xl font-bold">{summary.total_bottles}</span>
            <Package size="18" class="text-base-content/40 mb-0.5" />
          </div>
          <div class="text-base-content/50 text-xs mt-1">
            {summary.total_wines} wines
          </div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Market Value
          </div>
          <div class="mt-1 flex items-end gap-2">
            <span class="text-2xl font-bold"
              >€{summary.market_value?.toLocaleString() ?? "—"}</span
            >
            <TrendingUp size="18" class="text-base-content/40 mb-0.5" />
          </div>
          <div class="text-base-content/50 text-xs mt-1">
            Purchase: €{summary.purchase_value?.toLocaleString() ?? "—"}
          </div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">Sold</div>
          <div class="mt-1 flex items-end gap-2">
            <span class="text-2xl font-bold">{summary.sold_bottles}</span>
            <ArrowUpRight size="18" class="text-base-content/40 mb-0.5" />
          </div>
          <div class="text-base-content/50 text-xs mt-1">Lifetime</div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">Regions</div>
          <div class="mt-1 flex flex-wrap gap-1">
            {#each summary.region_balance.slice(0, 4) as r}
              <span class="badge badge-sm badge-outline"
                >{r.region} {r.pct}%</span
              >
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Search + Actions -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
    <div class="flex-1 relative">
      <Search
        size="16"
        class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40"
      />
      <input
        type="text"
        placeholder="Search wines by name, producer, region..."
        class="input input-bordered w-full pl-9"
        bind:value={searchQuery}
      />
    </div>
    <div class="flex items-center gap-2">
      <button
        class="btn btn-sm {showFilters ? 'btn-primary' : 'btn-ghost'}"
        onclick={() => (showFilters = !showFilters)}
      >
        <Filter size="14" /> Filters
      </button>
      <button
        class="btn btn-sm btn-success"
        onclick={() => openAddModal("purchase")}
      >
        <Plus size="14" /> Purchase
      </button>
    </div>
  </div>

  <!-- Filters -->
  {#if showFilters}
    <div class="flex flex-wrap gap-3 items-center bg-base-200 p-3 rounded-lg">
      <select class="select select-sm select-bordered" bind:value={filterColor}>
        <option value="">All colors</option>
        {#each colors as c}<option value={c}>{c}</option>{/each}
      </select>
      <select
        class="select select-sm select-bordered"
        bind:value={filterRegion}
      >
        <option value="">All regions</option>
        {#each regions as r}<option value={r}>{r}</option>{/each}
      </select>
      <select
        class="select select-sm select-bordered"
        bind:value={filterAppellation}
      >
        <option value="">All appellations</option>
        {#each appellations as c}<option value={c}>{c}</option>{/each}
      </select>
      <button
        class="btn btn-xs btn-ghost"
        onclick={() => {
          filterColor = "";
          filterRegion = "";
          filterAppellation = "";
        }}
      >
        <X size="12" /> Clear
      </button>
    </div>
  {/if}

  <!-- Wine Cards + Detail -->
  <div class="grid grid-cols-1 gap-4 {selectedWine ? 'lg:grid-cols-3' : ''}">
    <div class={selectedWine ? "lg:col-span-2" : ""}>
      <h2 class="font-semibold text-base mb-3 flex items-center gap-2">
        <WineIcon size="16" /> Cellar ({wines.length} wines)
      </h2>

      {#if loading}
        <div
          class="flex items-center justify-center py-12 text-base-content/40"
        >
          <span class="loading loading-spinner loading-md"></span><span
            class="ml-2">Loading cellar...</span
          >
        </div>
      {:else if wines.length === 0}
        <div class="text-center py-12 text-base-content/40">
          <WineIcon size="32" class="mx-auto mb-2" />
          <p>No wines in cellar</p>
          <button
            class="btn btn-sm btn-primary mt-3"
            onclick={() => openAddModal("purchase")}
          >
            <Plus size="14" /> Add your first wine
          </button>
        </div>
      {:else}
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {#each filteredWines as wine (wine.id)}
            {@const isSelected = selectedWine?.id === wine.id}
            {@const colorKey = getWineColorKey(wine.color)}
            <button
              class="card bg-base-100 border wine-card {isSelected
                ? 'wine-card-selected shadow-md'
                : ''} transition-all text-left cursor-pointer"
              onclick={() => selectWine(wine)}
            >
              <div class="card-body p-4">
                <div class="flex items-start justify-between">
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-sm truncate">{wine.name}</h3>
                    <p class="text-xs text-base-content/50 truncate">
                      {wine.producer} · {wine.vintage || "NV"}
                    </p>
                  </div>
                  <span
                    class="badge badge-xs shrink-0 wine-badge {wineColorClass[
                      colorKey
                    ] || 'wine-color-default'}"
                  >
                    {wineColorLabel[colorKey] || wine.color}
                  </span>
                </div>
                <div class="flex items-center justify-between mt-2">
                  <span class="text-xs text-base-content/50"
                    >{wine.region}, {wine.country}</span
                  >
                  <span
                    class="badge badge-sm stock-badge {stockBadgeClass(
                      wine.stock,
                    )}"
                  >
                    {wine.stock}
                    {wine.stock === 1 ? "btl" : "btls"}
                  </span>
                </div>
                {#if wine.market_price}
                  <div class="text-xs text-base-content/40 mt-1">
                    Market: €{wine.market_price.toFixed(0)}
                    {#if wine.stock > 1}
                      · Total: €{(wine.market_price * wine.stock).toFixed(
                        0,
                      )}{/if}
                  </div>
                {/if}
                {#if isSelected}<ChevronRight
                    size="14"
                    class="text-primary mt-1"
                  />{/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Detail Panel -->
    {#if selectedWine}
      <div class="lg:col-span-1">
        <div class="card bg-base-100 border border-primary-content sticky top-20">
          <div class="card-body p-4">
            <div class="flex items-start justify-between">
              <h3 class="font-bold text-lg">{selectedWine.name}</h3>
              <button
                class="btn btn-xs btn-ghost btn-circle"
                onclick={() => (selectedWine = null)}><X size="14" /></button
              >
            </div>
            <p class="text-sm text-base-content/60">
              {selectedWine.producer} · {selectedWine.vintage || "NV"}
            </p>
            <div class="divider my-2"></div>
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span class="text-base-content/40 text-xs">Region</span>
                <p>{selectedWine.region}</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Country</span>
                <p>{selectedWine.country}</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Appellation</span>
                <p>{selectedWine.appellation || "—"}</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Grape</span>
                <p>{selectedWine.grape_variety || "—"}</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Alcohol</span>
                <p>{selectedWine.alcohol}%</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Stock</span>
                <p class={stockTextClass(selectedWine.stock)}>
                  {selectedWine.stock} bottle{selectedWine.stock !== 1
                    ? "s"
                    : ""}
                </p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Drink from</span>
                <p>{selectedWine.drink_from || "—"}</p>
              </div>
              <div>
                <span class="text-base-content/40 text-xs">Drink until</span>
                <p>{selectedWine.drink_to || "—"}</p>
              </div>
            </div>
            {#if selectedWine.market_price}
              <div class="mt-3 bg-base-200 rounded-lg p-3">
                <div class="text-xs text-base-content/40">Market Price</div>
                <div class="text-xl font-bold">
                  €{selectedWine.market_price.toFixed(0)}
                </div>
                <div class="text-xs text-base-content/40 mt-1">
                  Cellar value: €{(
                    selectedWine.market_price * selectedWine.stock
                  ).toFixed(0)}
                </div>
              </div>
            {/if}
            <div class="flex gap-2 mt-3">
              <button
                class="btn btn-sm btn-success flex-1"
                onclick={() => openAddModal("purchase", selectedWine!.id)}
                ><ArrowDownLeft size="14" /> Purchase</button
              >
              <button
                class="btn btn-sm btn-error flex-1"
                onclick={() => openAddModal("sale", selectedWine!.id)}
                ><ArrowUpRight size="14" /> Sell</button
              >
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Add Transaction Modal -->
{#if showAddModal}
  <div class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg mb-4">
        {addForm.type === "purchase" ? "📥 Record Purchase" : "📤 Record Sale"}
      </h3>
      {#if !addForm.wine_id}
        <div class="form-control mb-3">
          <label class="label"
            ><span class="label-text">Search wine</span></label
          >
          <input
            type="text"
            placeholder="Type to search wines..."
            class="input input-bordered"
            bind:value={addForm.wineSearch}
            oninput={() => debouncedSearchWines(addForm.wineSearch)}
          />
          {#if searching}
            <div class="mt-2 text-xs text-base-content/40">Searching...</div>
          {:else if wineSearchResults.length > 0}
            <div
              class="mt-2 max-h-40 overflow-y-auto border border-base-300 rounded-lg"
            >
              {#each wineSearchResults as sr (sr.id)}
                <button
                  class="w-full text-left px-3 py-2 hover:bg-base-200 text-sm border-b border-base-200 last:border-0"
                  onclick={() => {
                    addForm.wine_id = sr.id;
                    addForm.wineSearch = `${sr.name} ${sr.vintage || ""}`;
                    addForm.purchase_price = sr.market_price || 0;
                    wineSearchResults = [];
                  }}
                >
                  <span class="font-medium">{sr.name}</span>
                  <span class="text-base-content/50">
                    {sr.vintage || "NV"} · {sr.region}</span
                  >
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {:else}
        <div
          class="bg-base-200 rounded-lg p-3 mb-3 flex items-center justify-between"
        >
          <span class="text-sm font-medium">{addForm.wineSearch}</span>
          <button
            class="btn btn-xs btn-ghost"
            onclick={() => {
              addForm.wine_id = 0;
              addForm.wineSearch = "";
              wineSearchResults = [];
            }}><X size="12" /></button
          >
        </div>
      {/if}
      <div class="grid grid-cols-2 gap-3">
        <div class="form-control">
          <label class="label"><span class="label-text">Quantity</span></label
          ><input
            type="number"
            class="input input-bordered"
            bind:value={addForm.quantity}
            min="1"
          />
        </div>
        <div class="form-control">
          <label class="label"
            ><span class="label-text">Price per unit (€)</span></label
          ><input
            type="number"
            class="input input-bordered"
            bind:value={addForm.purchase_price}
            step="0.01"
            min="0"
          />
        </div>
      </div>
      <div class="form-control mt-3">
        <label class="label"><span class="label-text">Date</span></label><input
          type="datetime-local"
          class="input input-bordered"
          bind:value={addForm.date}
        />
      </div>
      <div class="modal-action">
        <button
          class="btn btn-ghost"
          onclick={() => {
            showAddModal = false;
            resetAddForm();
          }}>Cancel</button
        >
        <button
          class="btn {addForm.type === 'purchase'
            ? 'btn-success'
            : 'btn-error'}"
          onclick={createTransaction}
          disabled={!addForm.wine_id || addForm.quantity < 1}
        >
          {addForm.type === "purchase" ? "Record Purchase" : "Record Sale"}
        </button>
      </div>
    </div>
    <div
      class="modal-backdrop"
      onclick={() => {
        showAddModal = false;
        resetAddForm();
      }}
    ></div>
  </div>
{/if}

<style>
  .wine-card {
    border-color: hsl(var(--bc) / 0.12);
  }

  .wine-card:hover {
    border-color: hsl(var(--bc) / 0.28);
  }

  .wine-card-selected {
    border-color: #7a3342;
    box-shadow: 0 0 0 1px rgb(122 51 66 / 0.2);
  }

  .wine-badge {
    border-width: 1px;
    border-style: solid;
    font-weight: 600;
    text-transform: lowercase;
    letter-spacing: 0.01em;
  }

  .wine-color-default {
    background: #f1f1f1;
    color: #4a4a4a;
    border-color: #d4d4d4;
  }

  .wine-color-red {
    background: #f6e7ea;
    color: #5f1622;
    border-color: #ca8f9b;
  }

  .wine-color-white {
    background: #edf8ee;
    color: #3f6d46;
    border-color: #bdd9c1;
  }

  .wine-color-sparkling {
    background: #fff5dc;
    color: #8a6b1f;
    border-color: #e4ce93;
    box-shadow: inset 0 0 0 1px rgb(255 236 179 / 0.85),
      0 0 0 1px rgb(214 186 112 / 0.35);
  }

  .wine-color-fortified,
  .wine-color-dessert {
    background: #f9eee6;
    color: #97572a;
    border-color: #e0b894;
  }

  .wine-color-rose {
    background: #fdebf3;
    color: #b03e6f;
    border-color: #e5abc4;
  }

  .stock-badge {
    border-width: 1px;
    border-style: solid;
    font-weight: 600;
  }

  .stock-badge-normal {
    background: #f2f4f7;
    color: #4b5563;
    border-color: #d2d7df;
  }

  .stock-badge-low {
    background: #feecef;
    color: #b4233d;
    border-color: #f3a6b4;
  }

  .stock-badge-critical {
    background: #ffe4e8;
    color: #981b32;
    border-color: #ea7d94;
    animation: stock-critical-pulse 1.9s ease-in-out infinite;
    will-change: box-shadow, transform;
  }

  .stock-text-low {
    color: #b4233d;
  }

  .stock-text-critical {
    color: #981b32;
  }

  @keyframes stock-critical-pulse {
    0%,
    100% {
      box-shadow: 0 0 0 0 rgb(234 125 148 / 0);
      transform: translateZ(0) scale(1);
    }
    50% {
      box-shadow: 0 0 0 3px rgb(234 125 148 / 0.26);
      transform: translateZ(0) scale(1.02);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .stock-badge-critical {
      animation: none;
    }
  }
</style>
