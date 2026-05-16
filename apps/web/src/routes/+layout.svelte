<script lang="ts">
  import "./layout.css";
  import favicon from "$lib/assets/favicon.svg";
  import Sidebar from "$lib/components/Sidebar.svelte";
  import { Menu } from "@lucide/svelte";

  let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="drawer lg:drawer-open">
  <input id="my-drawer-3" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content flex flex-col">
    <div class="navbar bg-base-100 lg:hidden">
      <label for="my-drawer-3" class="btn btn-square btn-ghost">
        <Menu />
      </label>
    </div>
    <!-- Page content here -->
    {@render children()}
  </div>
  <Sidebar />
</div>
