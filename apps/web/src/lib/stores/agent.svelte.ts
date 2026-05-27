import { api, type AgentEvent } from "$lib/api";

let events = $state<AgentEvent[]>([]);
let connected = $state(false);
let eventSource: EventSource | null = null;

const RUNNING_TYPES = new Set(["thought", "action"]);
const FINAL_TYPES = new Set(["final"]);

let agentRunning = $derived.by(() => {
  const recent = events.slice(-5);
  if (recent.length === 0) return false;
  const last = recent[recent.length - 1];
  if (FINAL_TYPES.has(last.type)) return false;
  return recent.some((e) => RUNNING_TYPES.has(e.type));
});

export function getAgentStore() {
  return {
    get events() { return events; },
    get connected() { return connected; },
    get agentRunning() { return agentRunning; },

    connect() {
      if (eventSource) return;

      eventSource = new EventSource(`http://${window.location.hostname}:8000/api/agent/stream`);

      eventSource.addEventListener("agent", (e) => {
        try {
          const data: AgentEvent = JSON.parse(e.data);
          events = [...events, data];
          if (events.length > 200) {
            events = events.slice(-150);
          }
        } catch { /* ignore parse errors */ }
      });

      eventSource.addEventListener("ping", () => { /* keepalive */ });

      eventSource.onopen = () => {
        connected = true;
      };

      eventSource.onerror = () => {
        connected = false;
        eventSource?.close();
        eventSource = null;
        setTimeout(() => this.connect(), 3000);
      };
    },

    disconnect() {
      eventSource?.close();
      eventSource = null;
      connected = false;
    },

    clear() {
      events = [];
    },

    async trigger(trigger = "manual", data?: Record<string, unknown>) {
      return api.agent.trigger(trigger, data);
    },

    async triggerAnalysis() {
      if (agentRunning) return;
      return api.agent.analyse();
    },
  };
}

const store = getAgentStore();
export default store;
