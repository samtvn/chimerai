<script lang="ts">
  import "./layout.css";
  import favicon from "$lib/assets/favicon.svg";
  import Sidebar from "$lib/components/Sidebar.svelte";
  import { Menu } from "@lucide/svelte";
  import Navbar from "$lib/components/Navbar.svelte";

  let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="bg-base-100 drawer mx-auto max-w-400 lg:drawer-open">
  <input id="drawer" class="drawer-toggle" type="checkbox" autocomplete="off" />
  <div class="drawer-content">
    <Navbar />
    <main class="relative max-w-[100vw] px-6 pb-16 xl:pe-2">
      {@render children()}
    </main>
  </div>
  <Sidebar />
</div>
