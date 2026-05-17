<script lang="ts">
  import { page } from "$app/state";
  import { Bell, Bot } from "@lucide/svelte";
  import { mockAlerts } from "$lib/mock/dashboard";

  const pageTitles: Record<string, string> = {
    "/": "Dashboard",
    "/inventory": "Inventory",
    "/card": "Wine Card",
    "/recommendations": "Recommendations",
  };

  const title = $derived(pageTitles[page.url.pathname] ?? "Chimerai");
</script>

<div
  class="bg-base-100/90 text-base-content sticky top-0 z-30 flex h-16 w-full backdrop-blur transition-shadow duration-100 print:hidden"
>
  <nav class="navbar w-full px-4 py-0">
    <!-- Left: hamburger (mobile) + page title -->
    <div class="flex flex-1 items-center gap-3">
      <label
        aria-label="Open menu"
        for="drawer"
        class="btn btn-square btn-ghost drawer-button lg:hidden"
      >
        <svg
          width="20"
          height="20"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          class="h-5 w-5 stroke-current"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </label>
      <h1 class="text-lg font-semibold">{title}</h1>
    </div>

    <!-- Right: agent status + alerts + user -->
    <div class="flex items-center gap-2">
      <!-- Agent status -->
      <div
        class="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-base-200 text-xs text-base-content/50"
      >
        <span class="size-2 rounded-full bg-base-content/20 inline-block"
        ></span>
        Agent idle
      </div>

      <!-- Alerts bell -->
      <div class="indicator">
        {#if mockAlerts.length > 0}
          <span class="badge badge-warning badge-xs indicator-item"
            >{mockAlerts.length}</span
          >
        {/if}
        <button class="btn btn-ghost btn-square btn-sm" aria-label="Alerts">
          <Bell size="18" />
        </button>
      </div>
    </div>
  </nav>
</div>
