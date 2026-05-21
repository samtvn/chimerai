<script lang="ts">
  import { page } from "$app/state";
  import { Bell } from "@lucide/svelte";
  import { api, type Alert as AlertType } from "$lib/api";
  import agentStore from "$lib/stores/agent.svelte";

  const pageTitles: Record<string, string> = {
    "/": "Dashboard", "/inventory": "Inventory", "/card": "Wine Card", "/recommendations": "Recommendations",
  };
  const title = $derived(pageTitles[page.url.pathname] ?? "Chimerai");

  let alerts = $state<AlertType[]>([]);
  let unreadCount = $state(0);
  let showAlerts = $state(false);

  async function loadAlerts() {
    try {
      const [res, countRes] = await Promise.all([api.alerts.list(), api.alerts.unreadCount()]);
      alerts = res.alerts;
      unreadCount = countRes.count;
    } catch { /* ignore */ }
  }

  async function markAllRead() {
    try { await api.alerts.markAllRead(); await loadAlerts(); } catch { /* ignore */ }
  }

  function openAlerts() {
    showAlerts = !showAlerts;
    if (showAlerts && unreadCount > 0) markAllRead();
  }

  $effect(() => { loadAlerts(); const i = setInterval(loadAlerts, 30000); return () => clearInterval(i); });

  const alertBadge: Record<string, string> = { error: "alert-error", warning: "alert-warning", info: "alert-info" };
  const statusColor = $derived(agentStore.agentRunning ? "bg-success animate-pulse" : agentStore.connected ? "bg-base-content/40" : "bg-error");
  const statusText = $derived(agentStore.agentRunning ? "Agent running" : agentStore.connected ? "Agent idle" : "Disconnected");
</script>

<div class="bg-base-100/90 text-base-content sticky top-0 z-30 flex h-16 w-full backdrop-blur transition-shadow duration-100 print:hidden">
  <nav class="navbar w-full px-4 py-0">
    <div class="flex flex-1 items-center gap-3">
      <label aria-label="Open menu" for="drawer" class="btn btn-square btn-ghost drawer-button lg:hidden">
        <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="h-5 w-5 stroke-current">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </label>
      <h1 class="text-lg font-semibold">{title}</h1>
    </div>
    <div class="flex items-center gap-2">
      <div class="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-base-200 text-xs text-base-content/50">
        <span class="size-2 rounded-full {statusColor} inline-block"></span>{statusText}
      </div>
      <div class="relative">
        <button class="btn btn-ghost btn-square btn-sm" aria-label="Alerts" onclick={openAlerts}>
          <Bell size="18" />
          {#if unreadCount > 0}<span class="badge badge-warning badge-xs absolute -top-1 -right-1">{unreadCount}</span>{/if}
        </button>
        {#if showAlerts && alerts.length > 0}
          <div class="absolute right-0 top-12 z-50 w-80 bg-base-100 border border-primary-content rounded-lg shadow-xl max-h-80 overflow-y-auto">
            <div class="p-2">
              {#each alerts as alert (alert.id)}
                <div class="alert {alertBadge[alert.severity]} py-2 px-3 text-xs mb-1"><span>{alert.message}</span></div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  </nav>
</div>
