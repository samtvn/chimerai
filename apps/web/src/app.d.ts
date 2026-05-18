import type { Session, User } from "better-auth/minimal";

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
  // biome-ignore lint/style/noNamespace: SvelteKit requires namespace App
  namespace App {
    interface Locals {
      session?: Session;
      user?: User;
    }

    // interface Error {}
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}
