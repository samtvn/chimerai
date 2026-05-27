<script lang="ts">
  import {
    ArrowRightLeft,
    BottleWine,
    TriangleAlert,
    TrendingUp,
  } from "@lucide/svelte";
  import { api, type CellarSummary, type Alert as AlertType } from "$lib/api";
  import AgentActivityStream from "$lib/components/AgentActivityStream.svelte";
  import agentStore from "$lib/stores/agent.svelte";

  let loading = $state(true);
  let summary = $state<CellarSummary | null>(null);
  let alerts = $state<AlertType[]>([]);
  let inventoryValueMode: "purchase" | "market" = $state("purchase");

  const switchMode = () => {
    inventoryValueMode =
      inventoryValueMode === "purchase" ? "market" : "purchase";
  };
  const inventoryValue = $derived(
    inventoryValueMode === "purchase"
      ? (summary?.purchase_value ?? 0)
      : (summary?.market_value ?? 0),
  );
  const alertBadge: Record<string, string> = {
    error: "alert-error",
    warning: "alert-warning",
    info: "alert-info",
  };

  async function loadData() {
    loading = true;
    try {
      const [s, a] = await Promise.all([
        api.cellar.summary(),
        api.alerts.list(),
      ]);
      summary = s;
      alerts = a.alerts;
    } catch {
      /* ignore */
    }
    loading = false;
  }

  $effect(() => {
    loadData();
    agentStore.connect();
  });
</script>

<div class="flex flex-col gap-6 p-4 md:p-6">
  {#if loading}
    <div class="flex items-center justify-center py-12 text-base-content/40">
      <span class="loading loading-spinner loading-md"></span><span class="ml-2"
        >Loading...</span
      >
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div
        class="card bg-base-100 border border-primary-content col-span-2 lg:col-span-1"
      >
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Cellar Value
          </div>
          <button
            type="button"
            onclick={switchMode}
            class="group mt-1 flex items-center gap-2 cursor-pointer hover:bg-primary rounded-lg px-2 py-1 transition-colors w-fit"
          >
            <span
              class="text-2xl font-bold group-hover:text-primary-content transition-colors"
              >€{inventoryValue.toLocaleString()}</span
            >
            <ArrowRightLeft
              size="16"
              class="group-hover:text-primary-content transition-colors"
            />
          </button>
          <div class="text-base-content/50 text-xs mt-1">
            {inventoryValueMode === "purchase" ? "Purchase" : "Market"} value
          </div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Total Bottles
          </div>
          <div class="mt-1 flex items-end gap-2">
            <span class="text-2xl font-bold">{summary?.total_bottles ?? 0}</span
            ><BottleWine size="20" class="text-base-content/40 mb-0.5" />
          </div>
          <div class="text-base-content/50 text-xs mt-1">
            {summary?.total_wines ?? 0} wines
          </div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Active Alerts
          </div>
          <div class="mt-1 flex items-end gap-2">
            <span class="text-2xl font-bold text-warning">{alerts.length}</span
            ><TriangleAlert size="20" class="text-warning mb-0.5" />
          </div>
          <div class="text-base-content/50 text-xs mt-1">Require attention</div>
        </div>
      </div>
      <div class="card bg-base-100 border border-primary-content">
        <div class="card-body p-4">
          <div class="text-base-content/60 text-sm font-medium">
            Most Stocked Wine
          </div>
          <div class="mt-1">
            <span class="text-lg font-bold leading-tight"
              >{summary?.top_wines?.[0]?.name ?? "No wine in stock"}</span
            >
          </div>
          <div
            class="text-base-content/50 text-xs mt-1 flex items-center gap-1"
          >
            <TrendingUp size="12" />{summary?.top_wines?.[0]?.bottles ?? 0}
            bottles in cellar
          </div>
        </div>
      </div>
    </div>

    {#if alerts.length > 0}
      <div class="flex flex-col gap-2">
        <h2 class="font-semibold text-base">Alerts</h2>
        {#each alerts as alert (alert.id)}
          <div class="alert {alertBadge[alert.severity]} py-2 px-4 text-sm">
            <TriangleAlert size="16" />{alert.message}
          </div>
        {/each}
      </div>
    {/if}
    <AgentActivityStream />
  {/if}
</div>
