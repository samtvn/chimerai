<script lang="ts">
  import { Brain, Play, Eye, BadgeCheck, Bell, Bot, RefreshCw } from "@lucide/svelte";
  import agentStore from "$lib/stores/agent.svelte";

  let autoScroll = $state(true);
  let containerEl: HTMLDivElement | undefined = $state();

  const sourceColors: Record<string, string> = {
    orchestrator: "badge-primary",
    inventory_audit: "badge-secondary",
    sales_analysis: "badge-accent",
    purchase_agent: "badge-info",
    menu_generator: "badge-success",
  };

  const typeIcons: Record<string, typeof Brain> = {
    thought: Brain,
    action: Play,
    observation: Eye,
    final: BadgeCheck,
    alert: Bell,
  };

  const typeColors: Record<string, string> = {
    thought: "text-info",
    action: "text-warning",
    observation: "text-secondary",
    final: "text-success",
    alert: "text-error",
  };

  const sourceLabels: Record<string, string> = {
    orchestrator: "Orchestrator",
    inventory_audit: "Inventory",
    sales_analysis: "Sales",
    purchase_agent: "Purchase",
    menu_generator: "Menu",
  };

  $effect(() => {
    if (autoScroll && containerEl) {
      containerEl.scrollTop = containerEl.scrollHeight;
    }
  });

  let hasFailure = $derived(agentStore.events.some((e) => e.type === "alert"));

  function formatTime(ts: string) {
    try {
      return new Date(ts).toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "";
    }
  }
</script>

<div class="card bg-base-100 border border-primary-content h-full">
  <div class="card-body p-3">
    <div class="flex items-center justify-between mb-2">
      <h3 class="card-title text-sm flex items-center gap-2">
        <Bot size="16" />
        Agent Activity
        {#if agentStore.agentRunning}
          <span class="badge badge-primary badge-sm">Running</span>
        {:else if agentStore.connected}
          <span class="badge badge-ghost badge-sm">Idle</span>
        {:else}
          <span class="badge badge-ghost badge-sm">Disconnected</span>
        {/if}
      </h3>
      <div class="flex items-center gap-1">
        <button
          class="btn btn-ghost btn-xs"
          onclick={() => agentStore.trigger("manual")}
          title="Trigger agent"
        >
          <Play size="12" /> Run
        </button>
        {#if hasFailure}
          <button
            class="btn btn-ghost btn-xs text-warning"
            onclick={() => agentStore.trigger("manual")}
            title="Resume from last checkpoint"
          >
            <RefreshCw size="12" /> Resume
          </button>
        {/if}
        <button
          class="btn btn-ghost btn-xs"
          onclick={() => agentStore.clear()}
          title="Clear events"
        >
          Clear
        </button>
      </div>
    </div>

    <div
      bind:this={containerEl}
      class="flex flex-col gap-1.5 overflow-y-auto max-h-80 scroll-smooth"
    >
      {#if agentStore.events.length === 0}
        <div
          class="flex flex-col items-center justify-center py-8 text-base-content/30 text-sm"
        >
          <Bot size="24" />
          <span class="mt-2">No agent activity yet</span>
          <span class="text-xs">Click "Run" to trigger the orchestrator</span>
        </div>
      {/if}

      {#each agentStore.events as event (event.timestamp + event.message)}
        {@const Icon = typeIcons[event.type] || Eye}
        <div
          class="flex items-start gap-2 text-xs py-1 px-2 rounded-lg hover:bg-base-200/50 transition-colors"
        >
          <div class="shrink-0 mt-0.5">
            <Icon
              size="12"
              class={typeColors[event.type] || "text-base-content/50"}
            />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 mb-0.5">
              <span
                class="badge {sourceColors[event.source] ||
                  'badge-ghost'} badge-xs"
              >
                {sourceLabels[event.source] || event.source}
              </span>
              <span class="capitalize text-base-content/40">{event.type}</span>
              <span class="text-base-content/30 ml-auto"
                >{formatTime(event.timestamp)}</span
              >
            </div>
            <p class="text-base-content/70 leading-relaxed wrap-break-word">
              {event.message}
            </p>
          </div>
        </div>
      {/each}
    </div>
  </div>
</div>
