<script lang="ts">
  import { ScrollText, Sparkles, AlertTriangle, RefreshCcw } from "@lucide/svelte";
  import { api, type VatCountry, type WineCardInventoryItem, type WineCardMenuAnalysis, type WineCardMenuExportResult, type WineCardPricingResult, type WineCardSeason, type WineCardTriggerReport } from "$lib/api";

  const seasons: WineCardSeason[] = ["spring", "summer", "autumn", "winter"];
  const vatCountries: VatCountry[] = ["LU", "FR", "BE", "DE"];

  let loading = $state(true);
  let error = $state("");
  let season = $state<WineCardSeason>("winter");
  let vatCountry = $state<VatCountry>("LU");
  let inventory = $state<WineCardInventoryItem[]>([]);
  let exportedMenu = $state<WineCardMenuExportResult | null>(null);
  let analysis = $state<WineCardMenuAnalysis | null>(null);
  let pricingPreviewInput = $state(18);
  let pricingPreview = $state<WineCardPricingResult | null>(null);
  let triggerReport = $state<WineCardTriggerReport | null>(null);
  let triggerRunning = $state(false);
  let minStockThreshold = $state(2);

  async function loadWineCardData() {
    loading = true;
    error = "";
    try {
      const [inv, menu, report] = await Promise.all([
        api.wineCard.inventory(),
        api.wineCard.exportEditableMenu(season, vatCountry),
        api.wineCard.analyzeMenu(season, vatCountry),
      ]);
      inventory = inv.items;
      exportedMenu = menu;
      analysis = report;
      pricingPreview = await api.wineCard.previewPricing(pricingPreviewInput, vatCountry);
      triggerReport = await api.wineCard.latestTrigger();
    } catch (e: any) {
      error = e.message || "Failed to load wine-card data";
    } finally {
      loading = false;
    }
  }

  async function refreshPricing() {
    pricingPreview = await api.wineCard.previewPricing(pricingPreviewInput, vatCountry);
  }

  async function runTriggerNow() {
    triggerRunning = true;
    error = "";
    try {
      triggerReport = await api.wineCard.runTrigger(
        "manual",
        season,
        vatCountry,
        minStockThreshold,
      );
      if (triggerReport.menu_export) {
        exportedMenu = triggerReport.menu_export;
      }
      if (triggerReport.menu_analysis) {
        analysis = triggerReport.menu_analysis;
      }
    } catch (e: any) {
      error = e.message || "Failed to run trigger";
    } finally {
      triggerRunning = false;
    }
  }

  $effect(() => {
    loadWineCardData();
  });
</script>

<div class="flex flex-col gap-6 p-4 md:p-6">
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <h2 class="font-semibold text-base flex items-center gap-2">
      <ScrollText size="16" /> Wine Card Builder
    </h2>
    <div class="flex items-center gap-2">
      <select class="select select-sm select-bordered" bind:value={season} onchange={loadWineCardData}>
        {#each seasons as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
      <select class="select select-sm select-bordered" bind:value={vatCountry} onchange={loadWineCardData}>
        {#each vatCountries as c}
          <option value={c}>VAT {c}</option>
        {/each}
      </select>
      <button class="btn btn-sm btn-ghost" onclick={loadWineCardData}>
        <RefreshCcw size="14" /> Refresh
      </button>
      <button class="btn btn-sm btn-primary" onclick={runTriggerNow} disabled={triggerRunning}>
        {#if triggerRunning}<span class="loading loading-spinner loading-xs"></span>{/if}
        Trigger
      </button>
    </div>
  </div>

  {#if error}
    <div class="alert alert-error"><span>{error}</span></div>
  {/if}

  {#if loading}
    <div class="flex items-center justify-center py-12 text-base-content/40">
      <span class="loading loading-spinner loading-md"></span><span class="ml-2">Loading wine card...</span>
    </div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm">Inventory lines</div>
          <div class="text-2xl font-bold">{inventory.length}</div>
          <div class="text-xs text-base-content/50">Based on in-cellar bottles</div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm">Exported menu rows</div>
          <div class="text-2xl font-bold">{exportedMenu?.items_count ?? 0}</div>
          <div class="text-xs text-base-content/50">Season: {season}</div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm">Missing sections</div>
          <div class="text-2xl font-bold">{analysis?.missing_categories.length ?? 0}</div>
          <div class="text-xs text-base-content/50">{analysis?.missing_categories.join(", ") || "None"}</div>
        </div>
      </div>
    </div>

    <div class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4 gap-3">
        <h3 class="font-semibold">Auto Trigger Status</h3>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span class="badge badge-outline">Min stock threshold</span>
          <input class="input input-bordered input-sm w-24" type="number" min="1" bind:value={minStockThreshold} />
        </div>
        {#if triggerReport}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
            <div>Last reason</div><div class="font-medium">{triggerReport.trigger_reason}</div>
            <div>Last run</div><div class="font-medium">{new Date(triggerReport.triggered_at).toLocaleString()}</div>
            <div>Low stock count</div><div class="font-medium">{triggerReport.low_stock_count}</div>
            <div>Needs purchase</div><div class="font-medium">{triggerReport.should_consider_purchase ? "yes" : "no"}</div>
          </div>
          {#if triggerReport.procurement_suggestions.length > 0}
            <div class="mt-2 flex flex-col gap-1">
              <div class="font-medium text-sm">Procurement suggestions</div>
              {#each triggerReport.procurement_suggestions as suggestion}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{suggestion}</div>
              {/each}
            </div>
          {/if}
          {#if triggerReport.wine_fair_watchlist.length > 0}
            <div class="mt-2 flex flex-col gap-1">
              <div class="font-medium text-sm">Wine fair watchlist</div>
              {#each triggerReport.wine_fair_watchlist as item}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{item}</div>
              {/each}
            </div>
          {/if}
        {:else}
          <div class="text-sm text-base-content/60">No trigger run yet. Click Trigger to create the first report.</div>
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4 gap-3">
          <h3 class="font-semibold flex items-center gap-2"><Sparkles size="15" /> Menu Analysis</h3>
          <p class="text-sm text-base-content/80">{analysis?.summary}</p>
          <div class="text-sm">
            <span class="font-medium">Strategy focus:</span>
            <span class="text-base-content/70"> {analysis?.strategy.focus.join(", ")}</span>
          </div>
          <div class="text-sm">
            <span class="font-medium">Strategy avoid:</span>
            <span class="text-base-content/70"> {analysis?.strategy.avoid.join(", ")}</span>
          </div>
          <div class="text-sm text-base-content/70">{analysis?.strategy.notes}</div>
          {#if analysis && analysis.low_stock_warnings.length > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm flex items-center gap-2"><AlertTriangle size="14" /> Low stock</div>
              {#each analysis.low_stock_warnings as warning}
                <div class="badge badge-warning badge-outline">{warning}</div>
              {/each}
            </div>
          {/if}
          {#if analysis && analysis.by_the_glass_suggestions.length > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm">By-the-glass suggestions</div>
              {#each analysis.by_the_glass_suggestions as item}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{item}</div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4 gap-3">
          <h3 class="font-semibold">Pricing Preview</h3>
          <div class="flex items-center gap-2">
            <input
              class="input input-bordered input-sm w-32"
              type="number"
              min="0"
              step="0.5"
              bind:value={pricingPreviewInput}
            />
            <button class="btn btn-sm btn-primary" onclick={refreshPricing}>Compute</button>
          </div>
          {#if pricingPreview}
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>Markup</div><div class="font-medium">{pricingPreview.markup_coefficient.toFixed(2)}x</div>
              <div>Selling HT</div><div class="font-medium">€{pricingPreview.selling_price_ht.toFixed(2)}</div>
              <div>Selling TTC</div><div class="font-medium">€{pricingPreview.selling_price_ttc.toFixed(2)}</div>
              <div>Glass TTC</div><div class="font-medium">€{pricingPreview.glass_price_ttc.toFixed(2)}</div>
              <div>VAT</div><div class="font-medium">{(pricingPreview.vat_rate * 100).toFixed(0)}% ({pricingPreview.vat_country})</div>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4 gap-3">
        <h3 class="font-semibold">Editable Markdown</h3>
        <textarea class="textarea textarea-bordered min-h-[420px] font-mono text-xs" readonly>{exportedMenu?.markdown ?? ""}</textarea>
      </div>
    </div>
  {/if}
</div>
