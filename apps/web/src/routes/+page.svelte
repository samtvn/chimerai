<script lang="ts">
  import { ArrowRightLeft, BottleWine, AlertTriangle, TrendingUp, Bot } from "@lucide/svelte";
  import {
    mockKpis,
    mockRegionBalance,
    mockAlerts,
    mockRecentActivity,
  } from "$lib/mock/dashboard";

  let inventoryValueMode: "purchase" | "market" = $state("purchase");

  const switchMode = () => {
    inventoryValueMode = inventoryValueMode === "purchase" ? "market" : "purchase";
  };

  const inventoryValue = $derived(
    inventoryValueMode === "purchase" ? mockKpis.purchaseValue : mockKpis.marketValue,
  );

  const actionBadge: Record<string, string> = {
    sold: "badge-error",
    restocked: "badge-success",
    added: "badge-info",
  };

  const alertBadge: Record<string, string> = {
    error: "alert-error",
    warning: "alert-warning",
    info: "alert-info",
  };
</script>

<div class="flex flex-col gap-6 p-4 md:p-6">

  <!-- KPI Cards -->
  <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">

    <!-- Cellar Value -->
    <div class="card bg-base-100 border border-primary-content col-span-2 lg:col-span-1">
      <div class="card-body p-4">
        <div class="text-base-content/60 text-sm font-medium">Cellar Value</div>
        <button
          type="button"
          onclick={switchMode}
          class="group mt-1 flex items-center gap-2 cursor-pointer hover:bg-primary rounded-lg px-2 py-1 transition-colors w-fit"
        >
          <span class="text-2xl font-bold group-hover:text-primary-content transition-colors">
            {inventoryValue.toLocaleString()}€
          </span>
          <ArrowRightLeft size="16" class="group-hover:text-primary-content transition-colors" />
        </button>
        <div class="text-base-content/50 text-xs mt-1">
          {inventoryValueMode === "purchase" ? "Purchase" : "Market"} value
        </div>
      </div>
    </div>

    <!-- Total Bottles -->
    <div class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4">
        <div class="text-base-content/60 text-sm font-medium">Total Bottles</div>
        <div class="mt-1 flex items-end gap-2">
          <span class="text-2xl font-bold">{mockKpis.totalBottles}</span>
          <BottleWine size="20" class="text-base-content/40 mb-0.5" />
        </div>
        <div class="text-base-content/50 text-xs mt-1">In cellar</div>
      </div>
    </div>

    <!-- Active Alerts -->
    <div class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4">
        <div class="text-base-content/60 text-sm font-medium">Active Alerts</div>
        <div class="mt-1 flex items-end gap-2">
          <span class="text-2xl font-bold text-warning">{mockKpis.activeAlerts}</span>
          <AlertTriangle size="20" class="text-warning mb-0.5" />
        </div>
        <div class="text-base-content/50 text-xs mt-1">Require attention</div>
      </div>
    </div>

    <!-- Top Selling Wine -->
    <div class="card bg-base-100 border border-primary-content">
      <div class="card-body p-4">
        <div class="text-base-content/60 text-sm font-medium">Top Wine (60d)</div>
        <div class="mt-1">
          <span class="text-lg font-bold leading-tight">{mockKpis.topWine.name}</span>
        </div>
        <div class="text-base-content/50 text-xs mt-1 flex items-center gap-1">
          <TrendingUp size="12" />
          {mockKpis.topWine.bottlesSold} bottles sold
        </div>
      </div>
    </div>

  </div>

  <!-- Middle section: chart + agent stream -->
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-5">

    <!-- Region Balance Chart -->
    <div class="card bg-base-100 border border-primary-content lg:col-span-3">
      <div class="card-body p-4">
        <h2 class="card-title text-base">Cellar Balance by Region</h2>
        <div class="mt-4 flex flex-col gap-3">
          {#each mockRegionBalance as item (item.region)}
            <div class="flex items-center gap-3">
              <span class="w-20 shrink-0 text-right text-xs text-base-content/60">{item.region}</span>
              <div class="flex-1 rounded-full bg-base-300 h-3 overflow-hidden">
                <div
                  class="h-full rounded-full bg-primary transition-all duration-500"
                  style="width: {item.pct}%"
                ></div>
              </div>
              <span class="w-8 shrink-0 text-xs text-base-content/50">{item.pct}%</span>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Agent Activity Stream placeholder -->
    <div class="card bg-base-100 border border-primary-content border-dashed lg:col-span-2">
      <div class="card-body p-4 flex flex-col items-center justify-center gap-3 text-center min-h-52">
        <Bot size="32" class="text-base-content/30" />
        <div class="text-base-content/40 text-sm">
          Agent activity stream<br />coming soon
        </div>
        <div class="flex items-center gap-2 text-xs text-base-content/30">
          <span class="inline-block size-2 rounded-full bg-base-content/20"></span>
          Waiting for backend SSE
        </div>
      </div>
    </div>

  </div>

  <!-- Alerts -->
  <div class="flex flex-col gap-2">
    <h2 class="font-semibold text-base">Alerts</h2>
    {#each mockAlerts as alert (alert.id)}
      <div class="alert {alertBadge[alert.severity]} py-2 px-4 text-sm">
        <AlertTriangle size="16" />
        {alert.message}
      </div>
    {/each}
  </div>

  <!-- Recent Activity -->
  <div class="card bg-base-100 border border-primary-content">
    <div class="card-body p-4">
      <h2 class="card-title text-base mb-2">Recent Activity</h2>
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Wine</th>
              <th>Action</th>
              <th>Qty</th>
              <th class="hidden sm:table-cell">Date</th>
            </tr>
          </thead>
          <tbody>
            {#each mockRecentActivity as item (item.id)}
              <tr>
                <td class="font-medium">{item.wine}</td>
                <td>
                  <span class="badge {actionBadge[item.action]} badge-sm capitalize">
                    {item.action}
                  </span>
                </td>
                <td>{item.quantity}</td>
                <td class="hidden sm:table-cell text-base-content/50 text-xs">{item.timestamp}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div>
