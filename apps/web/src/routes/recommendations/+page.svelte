<script lang="ts">
  import { Info, X, Sparkles, Wine } from "@lucide/svelte";
  import type { Recommendation } from "$lib/api";
  import { api } from "$lib/api";

  let loading = $state(true);
  let recommendations = $state<Recommendation[]>([]);
  let error = $state("");

  async function loadData() {
    loading = true;
    try {
      const res = await api.recommendations.list();
      recommendations = res.recommendations;
    } catch (e: any) {
      error = e.message;
    }
    loading = false;
  }

  function formatDate(d: string) {
    try {
      return new Date(d).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    } catch {
      return d;
    }
  }

  function priorityBadge(score: number) {
    if (score >= 8) return "badge-error";
    if (score >= 5) return "badge-warning";
    return "badge-info";
  }

  $effect(() => {
    loadData();
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

  <div class="flex flex-col md:flex-row justify-between items-center mb-3">
    <h2 class="font-semibold text-base flex items-center gap-2">
      <Sparkles size="16" /> Recommendations
    </h2>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-12 text-base-content/40">
      <span class="loading loading-spinner loading-md"></span><span class="ml-2"
        >Loading recommendations...</span
      >
    </div>
  {:else if recommendations.length === 0}
    <div class="text-center py-12 text-base-content/40">
      <Info size="32" class="mx-auto mb-2" />
      <p>No recommendations yet</p>
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each recommendations as rec (rec.id)}
        <div class="card bg-base-100 border border-primary-content">
          <div class="card-body p-4 flex flex-col gap-3">
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-2">
                <div
                  class="size-9 rounded-full bg-primary/20 flex items-center justify-center shrink-0"
                >
                  <Wine size="16" class="text-primary" />
                </div>
                <div class="min-w-0">
                  <div class="font-semibold text-sm truncate">
                    {rec.wine_name ?? `Wine #${rec.wine_id}`}
                  </div>
                  <div class="text-xs text-base-content/50 truncate">
                    {rec.wine_producer ?? ""}
                  </div>
                </div>
              </div>
            </div>

            <p class="text-sm text-base-content/80 leading-relaxed">
              {rec.recommendation_reason}
            </p>

            <div class="flex flex-wrap gap-2 text-xs text-base-content/60">
              <span class="bg-base-200 rounded-md px-2 py-1">
                Quantity: <span class="font-medium text-base-content"
                  >{rec.quantity}</span
                >
              </span>
              <span class="bg-base-200 rounded-md px-2 py-1">
                Market Price: <span class="font-medium text-base-content"
                  >€{rec.market_price.toFixed(2)}</span
                >
              </span>
              <span class="bg-base-200 rounded-md px-2 py-1">
                Total: <span class="font-medium text-base-content"
                  >€{(rec.market_price * rec.quantity).toFixed(2)}</span
                >
              </span>
              <span class="bg-base-200 rounded-md px-2 py-1">
                {formatDate(rec.created_at)}
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
