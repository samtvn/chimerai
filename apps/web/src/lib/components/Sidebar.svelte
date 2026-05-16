<script lang="ts">
  import { LayoutDashboard } from "@lucide/svelte";
</script>

<div class="drawer-side">
  <label for="my-drawer-3" aria-label="close sidebar" class="drawer-overlay"
  ></label>
  <ul class="menu bg-base-200 min-h-full w-40 p-4">
    <!-- Sidebar content here -->
    <li><a href="/"><LayoutDashboard size="14" /> Dashboard</a></li>
    <li><a href="/">Sidebar Item 2</a></li>
  </ul>
</div>
