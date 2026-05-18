<script lang="ts">
  import { LayoutDashboard, BottleWine, Scroll, Info } from "@lucide/svelte";
  import Logo from "./Logo.svelte";
</script>

<div class="drawer-side z-40 border-r border-base-content">
  <label class="drawer-overlay" for="drawer" aria-label="close sidebar"></label>
  <aside class="bg-base-100 min-h-screen w-56">
    <div
      class="bg-base-100/90 navbar sticky top-0 z-20 hidden items-center gap-2 px-4 py-0 backdrop-blur lg:flex"
    >
      <Logo class="ms-2 me-2 flex size-12 shrink-0 items-center gap-2" />
    </div>
    <div class="h-4"></div>
    <ul class="menu w-full px-4 py-0">
      <li>
        <a href="/"><LayoutDashboard size="14" /> Dashboard</a>
      </li>
      <li><a href="/inventory"><BottleWine size="14" /> Inventory</a></li>
      <li><a href="/card"><Scroll size="14" /> Wine Card</a></li>
      <li><a href="/recommendations"><Info size="14" /> Recommendations</a></li>
    </ul>
  </aside>
</div>
