<script lang="ts">
  import {
    Plus,
    Search,
    Filter,
    X,
    Pencil,
    Trash2,
    ArrowUpRight,
    ArrowDownLeft,
    Minus,
  } from "@lucide/svelte";
  import type { Transaction, Wine as WineType } from "$lib/api";
  import { api } from "$lib/api";
  import { debounce } from "$lib/utils/debounce";

  let loading = $state(true);
  let transactions = $state<Transaction[]>([]);
  let filterType = $state<"" | "purchase" | "sale">("");
  let showAddModal = $state(false);
  let showEditModal = $state(false);
  let showDeleteModal = $state(false);
  let editingTransaction = $state<Transaction | null>(null);
  let error = $state("");
  let hasMore = $state(true);
  let loadingMore = $state(false);

  let addForm = $state({
    wine_id: 0,
    wineSearch: "",
    quantity: 1,
    price: 0,
    type: "purchase" as "purchase" | "sale",
    date: new Date().toISOString().slice(0, 16),
  });

  let editForm = $state({
    quantity: 1,
    price: 0,
    type: "purchase" as "purchase" | "sale",
    date: "",
  });

  let wineSearchResults = $state<WineType[]>([]);
  let searching = $state(false);

  const debouncedSearchWines = debounce(async (q: string) => {
    if (q.length < 2) {
      wineSearchResults = [];
      return;
    }
    searching = true;
    try {
      const res = await api.wines.list({ search: q, limit: 20 });
      wineSearchResults = res.wines;
    } catch {
      wineSearchResults = [];
    }
    searching = false;
  }, 300);

  async function loadData() {
    loading = true;
    transactions = [];
    hasMore = true;
    try {
      const txnRes = await api.transactions.list({
        type: filterType || undefined,
        limit: 50,
        offset: 0,
      });
      transactions = txnRes.transactions;
      hasMore = txnRes.transactions.length === 50;
    } catch (e: any) {
      error = e.message;
    }
    loading = false;
  }

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    loadingMore = true;
    try {
      const txnRes = await api.transactions.list({
        type: filterType || undefined,
        limit: 50,
        offset: transactions.length,
      });
      transactions = [...transactions, ...txnRes.transactions];
      hasMore = txnRes.transactions.length === 50;
    } catch (e: any) {
      error = e.message;
    }
    loadingMore = false;
  }

  function invalidateAll() {
    loadData();
  }

  async function createTransaction() {
    try {
      // Only send date if user explicitly changed it from default
      // Otherwise, let the server set the current timestamp
      let transactionDate: string | undefined = undefined;
      if (addForm.date) {
        const formDate = new Date(addForm.date);
        const now = new Date();
        const diffMinutes = Math.abs(now.getTime() - formDate.getTime()) / (1000 * 60);
        
        // If the selected date differs by more than 2 minutes from now, user modified it
        if (diffMinutes > 2) {
          transactionDate = formDate.toISOString();
        }
      }
      
      await api.transactions.create({
        wine_id: addForm.wine_id,
        quantity: addForm.quantity,
        price: addForm.price || undefined,
        type: addForm.type,
        date: transactionDate,
      });
      showAddModal = false;
      resetAddForm();
      invalidateAll();
    } catch (e: any) {
      error = e.message;
    }
  }

  async function updateTransaction() {
    if (!editingTransaction) return;
    try {
      await api.transactions.update(editingTransaction.id, {
        quantity: editForm.quantity,
        price: editForm.price || undefined,
        type: editForm.type,
        date: editForm.date || undefined,
      });
      showEditModal = false;
      editingTransaction = null;
      invalidateAll();
    } catch (e: any) {
      error = e.message;
    }
  }

  async function deleteTransaction(id: string) {
    try {
      await api.transactions.delete(id);
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
      price: 0,
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
    }
    showAddModal = true;
  }

  function openEditModal(txn: Transaction) {
    editingTransaction = txn;
    editForm = {
      quantity: txn.quantity,
      price: txn.price || 0,
      type: txn.type,
      date: txn.date || "",
    };
    showEditModal = true;
  }

  function openDeleteModal(txn: Transaction) {
    editingTransaction = txn;
    showDeleteModal = true;
  }

  function formatDate(d: string | null) {
    if (!d) return "";
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

  <!-- Transactions -->
  <div class="flex flex-col md:flex-row justify-between items-center mb-3">
    <h2 class="font-semibold text-base">Transaction History</h2>
    <!-- Actions -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div class="flex-1"></div>
      <div class="flex items-center gap-2">
        <select
          class="select select-sm select-bordered"
          bind:value={filterType}
          onchange={loadData}
        >
          <option value="">All transactions</option>
          <option value="purchase">Purchases only</option>
          <option value="sale">Sales only</option>
        </select>
        <button
          class="btn btn-sm btn-success"
          onclick={() => openAddModal("purchase")}
        >
          <Plus size="14" /> Purchase
        </button>
        <button
          class="btn btn-sm btn-error"
          onclick={() => openAddModal("sale")}
        >
          <Minus size="14" /> Sale
        </button>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-12 text-base-content/40">
      <span class="loading loading-spinner loading-md"></span><span class="ml-2"
        >Loading transactions...</span
      >
    </div>
  {:else if transactions.length === 0}
    <div class="text-center py-8 text-base-content/30 text-sm">
      No transactions yet
    </div>
  {:else}
    <div class="flex flex-col gap-2">
      {#each transactions as txn (txn.id)}
        <div class="card bg-base-100 border border-primary-content">
          <div class="card-body p-3 flex-row items-center gap-3">
            <div class="shrink-0">
              {#if txn.type === "purchase"}
                <div
                  class="size-9 rounded-full bg-success/20 flex items-center justify-center"
                >
                  <ArrowDownLeft size="16" class="text-success" />
                </div>
              {:else}
                <div
                  class="size-9 rounded-full bg-error/20 flex items-center justify-center"
                >
                  <ArrowUpRight size="16" class="text-error" />
                </div>
              {/if}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-medium text-sm truncate">{txn.wine_name}</span
                >
              </div>
              <div class="text-xs text-base-content/50">
                {txn.wine_producer} · {txn.wine_vintage || "NV"} · {txn.wine_region}
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-sm font-semibold">
                {txn.type === "purchase" ? "+" : "-"}{txn.quantity} bottle{txn.quantity !==
                1
                  ? "s"
                  : ""}
              </div>
              {#if txn.price}<div class="text-xs text-base-content/50">
                  €{txn.price.toFixed(2)}/unit
                </div>{/if}
              <div class="text-xs text-base-content/30">
                {formatDate(txn.date)}
              </div>
            </div>
            <div class="flex flex-col gap-1 shrink-0">
              <button
                class="btn btn-ghost btn-xs"
                onclick={() => openEditModal(txn)}
                title="Edit"><Pencil size="12" /></button
              >
              <button
                class="btn btn-ghost btn-xs text-error"
                onclick={() => openDeleteModal(txn)}
                title="Delete"><Trash2 size="12" /></button
              >
            </div>
          </div>
        </div>
      {/each}
    </div>
    
    <!-- Load More / Infinite Scroll -->
    {#if hasMore}
      <div class="flex justify-center py-4">
        <button
          class="btn btn-outline btn-sm"
          onclick={loadMore}
          disabled={loadingMore}
        >
          {#if loadingMore}
            <span class="loading loading-spinner loading-sm"></span>
            Loading more...
          {:else}
            Load more transactions
          {/if}
        </button>
      </div>
    {/if}
  {/if}
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
          <label class="label" for="wineSearch"
            ><span class="label-text">Search wine</span></label
          >
          <input
            type="text"
            id="wineSearch"
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
                    addForm.price = sr.market_price || 0;
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
          <label class="label" for="quantity"
            ><span class="label-text">Quantity</span></label
          ><input
            type="number"
            id="quantity"
            class="input input-bordered"
            bind:value={addForm.quantity}
            min="1"
          />
        </div>
        <div class="form-control">
          <label class="label" for="price"
            ><span class="label-text">Price per unit (€)</span></label
          ><input
            type="number"
            id="price"
            class="input input-bordered"
            bind:value={addForm.price}
            step="0.01"
            min="0"
          />
        </div>
      </div>
      <div class="form-control mt-3">
        <label class="label" for="date"
          ><span class="label-text">Date</span></label
        ><input
          type="datetime-local"
          id="date"
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

<!-- Edit Transaction Modal -->
{#if showEditModal && editingTransaction}
  <div class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg mb-4">Edit Transaction</h3>
      <p class="text-sm text-base-content/60 mb-3">
        {editingTransaction.wine_name}
      </p>
      <div class="grid grid-cols-2 gap-3">
        <div class="form-control">
          <label class="label"><span class="label-text">Quantity</span></label
          ><input
            type="number"
            class="input input-bordered"
            bind:value={editForm.quantity}
            min="1"
          />
        </div>
        <div class="form-control">
          <label class="label"
            ><span class="label-text">Price per unit (€)</span></label
          ><input
            type="number"
            class="input input-bordered"
            bind:value={editForm.price}
            step="0.01"
            min="0"
          />
        </div>
      </div>
      <div class="form-control mt-3">
        <label class="label"><span class="label-text">Type</span></label><select
          class="select select-bordered"
          bind:value={editForm.type}
          ><option value="purchase">Purchase</option><option value="sale"
            >Sale</option
          ></select
        >
      </div>
      <div class="modal-action">
        <button
          class="btn btn-ghost"
          onclick={() => {
            showEditModal = false;
            editingTransaction = null;
          }}>Cancel</button
        >
        <button class="btn btn-primary" onclick={updateTransaction}
          >Save Changes</button
        >
      </div>
    </div>
    <div
      class="modal-backdrop"
      onclick={() => {
        showEditModal = false;
        editingTransaction = null;
      }}
    ></div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && editingTransaction}
  <div class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg mb-4">Confirm Deletion</h3>
      <p class="text-sm text-base-content/60 mb-3">
        Are you sure you want to delete this transaction?
      </p>
      <p class="text-sm text-base-content/50 mb-5">
        {editingTransaction.wine_name} · {editingTransaction.quantity} bottle{editingTransaction.quantity !==
        1
          ? "s"
          : ""} · {formatDate(editingTransaction.date)}
      </p>
      <div class="modal-action">
        <button
          class="btn btn-ghost"
          onclick={() => {
            showDeleteModal = false;
            editingTransaction = null;
          }}>Cancel</button
        >
        <button
          class="btn btn-error"
          onclick={() => {
            deleteTransaction(editingTransaction!.id);
            showDeleteModal = false;
            editingTransaction = null;
          }}>Delete</button
        >
      </div>
    </div>
    <div
      class="modal-backdrop"
      onclick={() => {
        showDeleteModal = false;
        editingTransaction = null;
      }}
    ></div>
  </div>
{/if}
