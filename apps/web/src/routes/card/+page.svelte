<script lang="ts">
  import { ScrollText, Sparkles, AlertTriangle, RefreshCcw, Download } from "@lucide/svelte";
  import { api, type VatCountry, type WineCardInventoryItem, type WineCardMenuAnalysis, type WineCardMenuExportResult, type WineCardOccasion, type WineCardPricingResult, type WineCardSeason, type WineCardTriggerReport } from "$lib/api";

  const seasons: WineCardSeason[] = ["spring", "summer", "autumn", "winter"];
  const vatCountries: VatCountry[] = ["LU", "FR", "BE", "DE"];
  const occasions: WineCardOccasion[] = ["christmas", "valentine", "easter", "banquet"];
  const menuSectionOrder = ["rose", "sparkling", "white", "red", "dessert", "fortified"];
  const menuSectionLabel: Record<string, string> = {
    rose: "Rosé",
    sparkling: "Sparkling",
    white: "White",
    red: "Red",
    dessert: "Dessert",
    fortified: "Fortified",
  };
  const occasionLabels: Record<WineCardOccasion, string> = {
    christmas: "Christmas",
    valentine: "Valentine",
    easter: "Easter",
    banquet: "Banquet",
  };

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
  let oneShotOccasion = $state<WineCardOccasion>("christmas");
  let oneShotRunning = $state(false);
  let oneShotSummary = $state("");
  let oneShotNotes = $state<string[]>([]);
  let oneShotServiceCount = $state(3);
  let oneShotMenuTotalPrice = $state<number | null>(null);
  let oneShotSuggestedPairingPrice = $state<number | null>(null);
  let oneShotSuggestedPerServicePrice = $state<number | null>(null);
  let oneShotPrompt = $state("");
  let oneShotResultOccasion = $state<WineCardOccasion | null>(null);
  let menuViewMode = $state<"preview" | "raw">("preview");
  let activeMenuLayout = $state<"seasonal" | "one-shot">("seasonal");

  const menuPreviewGroups = $derived.by(() => {
    const items = exportedMenu?.menu_items ?? [];
    return menuSectionOrder
      .map((section) => ({
        section,
        label: menuSectionLabel[section] ?? section,
        items: items.filter((item) => item.section === section),
      }))
      .filter((group) => group.items.length > 0);
  });

  function extractRestaurantTitle(markdown: string | undefined): string {
    if (!markdown) return "Restaurant Wine Menu";
    const firstLine = markdown.split("\n").find((line) => line.startsWith("# "));
    if (!firstLine) return "Restaurant Wine Menu";
    return firstLine.replace(/^#\s+/, "").trim();
  }

  function buildOneShotTastingNote(item: {
    section: string;
    appellation?: string | null;
    region?: string | null;
    country?: string | null;
  }): string {
    const profileBySection: Record<string, string> = {
      sparkling: "Bulles fines, tension citronnee et finale nette a dominante crayeuse.",
      white: "Noyau de fruits frais, acidite equilibree et trame minerale precise.",
      rose: "Aromes de petits fruits rouges, belle fraicheur et finale seche et gourmande.",
      red: "Fruits noirs murs, tanins souples et touche epicee en finale.",
      dessert: "Fruit bien concentre, douceur soyeuse et acidite vive en soutien.",
      fortified: "Notes de fruits secs, epices chaudes et structure persistante.",
    };
    const base = profileBySection[item.section] ?? "Profil fruite equilibre, avec de la fraicheur et une finale nette.";
    const origin = item.appellation || item.region || item.country;
    return origin ? `${base} Belle expression de ${origin}.` : base;
  }

  function buildOneShotCardTitle(occasion: WineCardOccasion | null): string {
    const key = occasion ?? oneShotOccasion;
    const labels: Record<WineCardOccasion, string> = {
      christmas: "Christmas Special Food Pairing Card",
      valentine: "Valentine Special Food Pairing Card",
      easter: "Easter Special Food Pairing Card",
      banquet: "Banquet Special Food Pairing Card",
    };
    return labels[key];
  }

  const oneShotSelectedGlassTotal = $derived.by(() => {
    if (activeMenuLayout !== "one-shot" || !exportedMenu) return null;
    const total = exportedMenu.menu_items.reduce((sum, item) => sum + item.glass_price_ttc, 0);
    return Math.round(total * 100) / 100;
  });

  function downloadCurrentMenuMarkdown() {
    if (!exportedMenu?.markdown) return;
    const restaurantName = extractRestaurantTitle(exportedMenu.markdown)
      .replace(/[^\w\s-]/g, "")
      .trim()
      .replace(/\s+/g, "-")
      .toLowerCase();
    const dateStr = new Date().toISOString().slice(0, 10);
    const filename = `${restaurantName || "wine-menu"}-${exportedMenu.season}-${dateStr}.md`;
    const blob = new Blob([exportedMenu.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

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
      activeMenuLayout = "seasonal";
      oneShotSummary = "";
      oneShotNotes = [];
      oneShotPrompt = "";
      oneShotResultOccasion = null;
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
      activeMenuLayout = "seasonal";
      oneShotResultOccasion = null;
    } catch (e: any) {
      error = e.message || "Failed to refresh wine strategy";
    } finally {
      triggerRunning = false;
    }
  }

  async function runOneShotMenu() {
    oneShotRunning = true;
    error = "";
    try {
      const normalizedMenuPrice =
        typeof oneShotMenuTotalPrice === "number" &&
        Number.isFinite(oneShotMenuTotalPrice) &&
        oneShotMenuTotalPrice > 0
          ? oneShotMenuTotalPrice
          : undefined;
      const result = await api.wineCard.generateOneShotMenu(
        oneShotOccasion,
        vatCountry,
        oneShotServiceCount,
        normalizedMenuPrice,
      );
      season = result.season;
      exportedMenu = result.menu_export;
      analysis = result.menu_analysis;
      inventory = result.menu_export.menu_items.map((item) => ({
        wine_id: item.wine_id,
        producer: item.producer,
        wine_name: item.wine_name,
        region: item.region,
        country: item.country,
        appellation: item.appellation,
        wine_color: item.section,
        vintage: item.vintage,
        grape_variety: null,
        drink_from: null,
        drink_to: null,
        quantity: item.quantity,
        purchase_price_ht: item.purchase_price_ht,
        avg_market_price: item.avg_market_price,
      }));
      oneShotSummary = result.summary;
      oneShotNotes = result.pairing_notes;
      oneShotSuggestedPairingPrice = result.suggested_pairing_price_ttc;
      oneShotSuggestedPerServicePrice = result.suggested_per_service_price_ttc;
      oneShotPrompt = result.llm_prompt;
      oneShotResultOccasion = result.occasion;
      activeMenuLayout = "one-shot";
      menuViewMode = "preview";
    } catch (e: any) {
      error = e.message || "Failed to generate one-shot menu";
    } finally {
      oneShotRunning = false;
    }
  }

  function scrollToFullMenuOutput() {
    const el = document.getElementById("menu-output");
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
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
        Refresh Wine Strategy
      </button>
      <select class="select select-sm select-bordered" bind:value={oneShotOccasion}>
        {#each occasions as o}
          <option value={o}>{occasionLabels[o]}</option>
        {/each}
      </select>
      <select class="select select-sm select-bordered" bind:value={oneShotServiceCount}>
        <option value={3}>3 services</option>
        <option value={4}>4 services</option>
        <option value={5}>5 services</option>
      </select>
      <input
        class="input input-bordered input-sm w-36"
        type="number"
        min="0"
        step="0.5"
        placeholder="Menu price €"
        bind:value={oneShotMenuTotalPrice}
      />
      <button class="btn btn-sm btn-outline" onclick={runOneShotMenu} disabled={oneShotRunning}>
        {#if oneShotRunning}<span class="loading loading-spinner loading-xs"></span>{/if}
        One-shot menu
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
          <div class="text-base-content/60 text-sm">Selected for menu</div>
          <div class="text-2xl font-bold">
            {analysis?.selected_for_menu ?? exportedMenu?.items_count ?? 0}
            <span class="text-sm font-normal text-base-content/60">
              / {analysis?.total_inventory_candidates ?? inventory.length}
            </span>
          </div>
          <div class="text-xs text-base-content/50">Seasonal curation (not full cellar)</div>
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
        {#if oneShotSummary}
          <div class="text-sm bg-base-200 rounded-md p-2">
            <div class="font-medium">One-shot summary</div>
            <div class="text-base-content/80">{oneShotSummary}</div>
            {#if oneShotSuggestedPairingPrice !== null}
              <div class="mt-1 text-xs">
                Suggested pairing price:
                <span class="font-medium">€{oneShotSuggestedPairingPrice.toFixed(2)} TTC</span>
                {#if oneShotSuggestedPerServicePrice !== null}
                  · per service target
                  <span class="font-medium">€{oneShotSuggestedPerServicePrice.toFixed(2)}</span>
                {/if}
              </div>
            {/if}
            {#if oneShotNotes.length > 0}
              <div class="mt-2 text-xs text-base-content/70">
                {oneShotNotes.join(" · ")}
              </div>
            {/if}
            {#if exportedMenu && exportedMenu.menu_items.length > 0}
              <div class="mt-3 rounded-md border border-base-300 bg-base-100 p-2">
                <div class="flex items-center justify-between gap-2">
                  <div class="text-xs font-medium">{buildOneShotCardTitle(oneShotResultOccasion)} (quick preview)</div>
                  <button class="btn btn-xs btn-outline" onclick={scrollToFullMenuOutput}>
                    Open full menu
                  </button>
                </div>
                <div class="mt-1 text-[11px] text-base-content/60">
                  Showing first 8 wines · full editable version is in Menu Output below.
                </div>
                <div class="mt-2 overflow-x-auto">
                  {#if activeMenuLayout === "one-shot"}
                    <table class="table table-xs w-full">
                      <thead>
                        <tr>
                          <th>Section</th>
                          <th>Wine</th>
                          <th class="text-center">Vintage</th>
                          <th>Tasting note</th>
                          <th class="text-right">12cl TTC</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each exportedMenu.menu_items.slice(0, 8) as item}
                          <tr>
                            <td>{menuSectionLabel[item.section] ?? item.section}</td>
                            <td class="font-medium">{item.producer} — {item.wine_name}</td>
                            <td class="text-center">{item.vintage || "NV"}</td>
                            <td class="text-xs text-base-content/70">{buildOneShotTastingNote(item)}</td>
                            <td class="text-right font-medium">€{item.glass_price_ttc.toFixed(2)}</td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                    {#if oneShotSelectedGlassTotal !== null}
                      <div class="mt-2 border-t border-base-300 pt-2 text-right text-sm font-semibold">
                        Forfait accord mets: €{oneShotSelectedGlassTotal.toFixed(2)} TTC
                      </div>
                    {/if}
                  {:else}
                    <table class="table table-xs w-full">
                      <thead>
                        <tr>
                          <th>Section</th>
                          <th>Wine</th>
                          <th class="text-center">Vintage</th>
                          <th class="text-right">Glass</th>
                          <th class="text-right">Bottle</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each exportedMenu.menu_items.slice(0, 8) as item}
                          <tr>
                            <td>{menuSectionLabel[item.section] ?? item.section}</td>
                            <td class="font-medium">{item.producer} — {item.wine_name}</td>
                            <td class="text-center">{item.vintage || "NV"}</td>
                            <td class="text-right">€{item.glass_price_ttc.toFixed(2)}</td>
                            <td class="text-right">€{item.selling_price_ttc.toFixed(2)}</td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  {/if}
                </div>
              </div>
            {/if}
            {#if oneShotPrompt}
              <details class="mt-2">
                <summary class="cursor-pointer text-xs font-medium">LLM prompt preview</summary>
                <pre class="mt-1 text-[11px] whitespace-pre-wrap bg-base-100 rounded p-2 border border-base-300">{oneShotPrompt}</pre>
              </details>
            {/if}
          </div>
        {/if}
        <h3 class="font-semibold">Wine Strategy Check</h3>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span class="badge badge-outline">Min stock threshold</span>
          <input class="input input-bordered input-sm w-24" type="number" min="1" bind:value={minStockThreshold} />
        </div>
        {#if triggerReport}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
            <div>Last audit type</div><div class="font-medium">{triggerReport.trigger_reason}</div>
            <div>Last run</div><div class="font-medium">{new Date(triggerReport.triggered_at).toLocaleString()}</div>
            <div>Items needing attention</div><div class="font-medium">{triggerReport.low_stock_count}</div>
            <div>Restock recommended</div><div class="font-medium">{triggerReport.should_consider_purchase ? "yes" : "no"}</div>
          </div>
          {#if triggerReport.procurement_suggestions.length > 0}
            <div class="mt-2 flex flex-col gap-1">
              <div class="font-medium text-sm">Restock suggestions</div>
              {#each triggerReport.procurement_suggestions as suggestion}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{suggestion}</div>
              {/each}
            </div>
          {/if}
          {#if triggerReport.wine_fair_watchlist.length > 0}
            <div class="mt-2 flex flex-col gap-1">
              <div class="font-medium text-sm">Market watchlist</div>
              {#each triggerReport.wine_fair_watchlist as item}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{item}</div>
              {/each}
            </div>
          {/if}
        {:else}
          <div class="text-sm text-base-content/60">No strategy check run yet. Click Refresh Wine Strategy to create the first report.</div>
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4 gap-3">
          <h3 class="font-semibold flex items-center gap-2"><Sparkles size="15" /> Menu Analysis</h3>
          <p class="text-sm text-base-content/80">{analysis?.summary}</p>
          {#if analysis}
            <div class="text-sm">
              <span class="font-medium">Selection:</span>
              <span class="text-base-content/70">
                {" "}
                {analysis.selected_for_menu} / {analysis.total_inventory_candidates} references on menu
              </span>
            </div>
          {/if}
          <div class="text-sm">
            <span class="font-medium">Strategy focus:</span>
            <span class="text-base-content/70"> {analysis?.strategy.focus.join(", ")}</span>
          </div>
          <div class="text-sm">
            <span class="font-medium">Strategy avoid:</span>
            <span class="text-base-content/70"> {analysis?.strategy.avoid.join(", ")}</span>
          </div>
          <div class="text-sm text-base-content/70">{analysis?.strategy.notes}</div>
          {#if analysis && (analysis.seasonal_inventory_guidance?.length ?? 0) > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm">Seasonal inventory guidance</div>
              {#each analysis.seasonal_inventory_guidance ?? [] as item}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{item}</div>
              {/each}
            </div>
          {/if}
          {#if analysis && analysis.low_stock_warnings.length > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm flex items-center gap-2"><AlertTriangle size="14" /> Low stock</div>
              {#each analysis.low_stock_warnings as warning}
                <div class="badge badge-warning badge-outline">{warning}</div>
              {/each}
            </div>
          {/if}
          {#if analysis && analysis.cheap_wine_low_stock_alerts.length > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm flex items-center gap-2"><AlertTriangle size="14" /> Cheap wines to replenish</div>
              {#each analysis.cheap_wine_low_stock_alerts as alertText}
                <div class="text-sm bg-warning/15 border border-warning/40 rounded-md px-2 py-1">
                  {alertText}
                </div>
              {/each}
              {#if analysis.reprint_menu_recommended}
                <div class="text-sm font-medium text-warning">
                  Recommendation: replenish first, then reprint wine list.
                </div>
              {/if}
            </div>
          {/if}
          {#if analysis && analysis.duplicate_vintage_alerts.length > 0}
            <div class="mt-2 flex flex-col gap-2">
              <div class="font-medium text-sm">Multi-vintage decision needed (big wines)</div>
              {#each analysis.duplicate_vintage_alerts as alertText}
                <div class="text-sm bg-base-200 rounded-md px-2 py-1">{alertText}</div>
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

    <div id="menu-output" class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4 gap-3">
        <div class="flex items-center justify-between gap-2">
          <h3 class="font-semibold">Menu Output</h3>
          <div class="flex items-center gap-2">
            <button
              class="btn btn-xs btn-outline"
              onclick={downloadCurrentMenuMarkdown}
              disabled={!exportedMenu?.markdown}
            >
              <Download size="12" /> Download .md
            </button>
            <div class="join">
            <button
              class="btn btn-xs join-item {menuViewMode === 'preview' ? 'btn-primary' : 'btn-ghost'}"
              onclick={() => (menuViewMode = "preview")}
            >
              Preview
            </button>
            <button
              class="btn btn-xs join-item {menuViewMode === 'raw' ? 'btn-primary' : 'btn-ghost'}"
              onclick={() => (menuViewMode = "raw")}
            >
              Raw Markdown
            </button>
            </div>
          </div>
        </div>

        {#if menuViewMode === "raw"}
          <textarea class="textarea textarea-bordered min-h-[420px] font-mono text-xs" readonly>{exportedMenu?.markdown ?? ""}</textarea>
        {:else if exportedMenu}
          <div class="border border-base-300 rounded-xl p-4 bg-base-100">
            <div class="text-center mb-4">
              <h4 class="text-xl font-semibold">{extractRestaurantTitle(exportedMenu.markdown)}</h4>
              <div class="text-sm text-base-content/70 mt-1">
                {activeMenuLayout === "one-shot" ? buildOneShotCardTitle(oneShotResultOccasion) : `Wine Menu — ${exportedMenu.season}`}
              </div>
              <div class="text-xs text-base-content/60 mt-1">
                Prices TTC • Service compris
              </div>
            </div>

            {#if activeMenuLayout === "one-shot"}
              <div class="overflow-x-auto">
                <table class="table table-zebra table-sm w-full">
                  <thead>
                    <tr>
                      <th>Section</th>
                      <th>Wine</th>
                      <th>Origin</th>
                      <th class="text-center">Vintage</th>
                      <th>Tasting note</th>
                      <th class="text-right">12cl TTC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each exportedMenu.menu_items as item}
                      <tr>
                        <td>{menuSectionLabel[item.section] ?? item.section}</td>
                        <td class="font-medium">{item.producer} — {item.wine_name}</td>
                        <td>{[item.appellation, item.region, item.country].filter(Boolean).join(" / ") || "—"}</td>
                        <td class="text-center">{item.vintage || "NV"}</td>
                        <td class="text-sm text-base-content/75">{buildOneShotTastingNote(item)}</td>
                        <td class="text-right font-semibold">€{item.glass_price_ttc.toFixed(2)}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
              {#if oneShotSelectedGlassTotal !== null}
                <div class="mt-3 border-t border-base-300 pt-3 text-right text-sm font-semibold">
                  Forfait accord mets: €{oneShotSelectedGlassTotal.toFixed(2)} TTC
                </div>
              {/if}
            {:else}
              <div class="flex flex-col gap-4">
                {#each menuPreviewGroups as group}
                  <div class="overflow-x-auto">
                    <h5 class="font-semibold mb-2">{group.label}</h5>
                    <table class="table table-zebra table-xs w-full">
                      <thead>
                        <tr>
                          <th>Wine</th>
                          <th>Origin</th>
                          <th class="text-center">Vintage</th>
                          <th class="text-right">Glass 12cl TTC</th>
                          <th class="text-right">Bottle 75cl TTC</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each group.items as item}
                          <tr>
                            <td class="font-medium">{item.producer} — {item.wine_name}</td>
                            <td>{[item.appellation, item.region, item.country].filter(Boolean).join(" / ") || "—"}</td>
                            <td class="text-center">{item.vintage || "NV"}</td>
                            <td class="text-right">€{item.glass_price_ttc.toFixed(2)}</td>
                            <td class="text-right">€{item.selling_price_ttc.toFixed(2)}</td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/each}
              </div>
            {/if}

            <div class="mt-4 pt-3 border-t border-base-300 text-xs text-base-content/70 space-y-1">
              <div><span class="font-medium">Prix TTC service compris.</span></div>
              <div>L’abus d’alcool est dangereux pour la santé, à consommer avec modération.</div>
              <div>La vente d’alcool est interdite aux mineurs.</div>
            </div>
          </div>
        {:else}
          <div class="text-sm text-base-content/60">No menu generated yet.</div>
        {/if}
      </div>
    </div>
  {/if}
</div>
